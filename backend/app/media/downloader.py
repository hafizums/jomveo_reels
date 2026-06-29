import ipaddress
import logging
import os
import socket
import uuid
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from backend.app.core.config import Settings
from backend.app.core.errors import (
    MediaValidationError,
    RemoteDownloadError,
    UnsafeRemoteURLError,
)
from backend.app.media.validation import (
    CONTENT_TYPES_BY_KIND,
    content_type_for_extension,
    normalized_content_type,
    validate_content_type,
    validate_magic_bytes,
)

logger = logging.getLogger(__name__)
Resolver = Callable[[str, int], list[str]]


CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}

DEFAULT_EXTENSIONS = {
    "image": ".jpg",
    "audio": ".mp3",
    "video": ".mp4",
}


def resolve_addresses(hostname: str, port: int) -> list[str]:
    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeRemoteURLError("Remote asset hostname could not be resolved.") from exc
    return sorted({record[4][0] for record in records})


class RemoteAssetDownloader:
    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        resolver: Resolver = resolve_addresses,
    ) -> None:
        self.settings = settings
        self.resolver = resolver
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=settings.remote_download_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> "RemoteAssetDownloader":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def validate_url(self, url: str) -> None:
        if "\\" in url or any(ord(character) < 32 for character in url):
            raise UnsafeRemoteURLError("Remote asset URL contains unsafe characters.")
        try:
            parsed = urlsplit(url)
            port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        except ValueError as exc:
            raise UnsafeRemoteURLError("Remote asset URL is invalid.") from exc
        allowed_schemes = {scheme.lower() for scheme in self.settings.allowed_remote_asset_schemes}
        if parsed.scheme.lower() not in {"http", "https"} or parsed.scheme.lower() not in (
            allowed_schemes
        ):
            raise UnsafeRemoteURLError("Remote asset URL scheme is not allowed.")
        if not parsed.hostname:
            raise UnsafeRemoteURLError("Remote asset URL must include a hostname.")
        if parsed.username is not None or parsed.password is not None:
            raise UnsafeRemoteURLError("Remote asset URL must not include user information.")

        addresses = self.resolver(parsed.hostname, port)
        if not addresses:
            raise UnsafeRemoteURLError("Remote asset hostname did not resolve to an address.")
        if self.settings.allow_private_network_downloads:
            return
        for address in addresses:
            try:
                ip = ipaddress.ip_address(address.split("%", 1)[0])
            except ValueError as exc:
                raise UnsafeRemoteURLError("Remote asset hostname resolved unsafely.") from exc
            if (
                not ip.is_global
                or ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise UnsafeRemoteURLError("Remote asset URL resolves to a blocked network.")

    def download(self, url: str, destination: Path, expected_kind: str) -> Path:
        if expected_kind not in DEFAULT_EXTENSIONS:
            raise RemoteDownloadError("Remote asset media type is unsupported.")
        current_url = url
        for _redirect_count in range(6):
            self.validate_url(current_url)
            try:
                with self.client.stream(
                    "GET",
                    current_url,
                    follow_redirects=False,
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise RemoteDownloadError(
                                "Remote asset redirect was missing a location."
                            )
                        current_url = urljoin(current_url, location)
                        continue
                    response.raise_for_status()
                    return self._write_response(response, destination, expected_kind)
            except (UnsafeRemoteURLError, RemoteDownloadError):
                raise
            except httpx.TimeoutException as exc:
                raise RemoteDownloadError("Remote asset download timed out.") from exc
            except httpx.HTTPError as exc:
                logger.warning("remote_asset_download_failed", exc_info=exc)
                raise RemoteDownloadError("Remote asset download failed.") from exc
        raise UnsafeRemoteURLError("Remote asset exceeded the redirect limit.")

    def _write_response(
        self,
        response: httpx.Response,
        destination: Path,
        expected_kind: str,
    ) -> Path:
        content_type = normalized_content_type(response.headers.get("content-type"))
        if content_type:
            try:
                validate_content_type(content_type, CONTENT_TYPES_BY_KIND[expected_kind])
            except MediaValidationError as exc:
                raise RemoteDownloadError(
                    "Remote asset returned an unsupported media type."
                ) from exc
        extension = CONTENT_TYPE_EXTENSIONS.get(
            content_type or "",
            DEFAULT_EXTENSIONS[expected_kind],
        )
        final_path = destination.with_suffix(extension)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = final_path.with_name(f".{final_path.name}.{uuid.uuid4().hex}.part")

        content_length = response.headers.get("content-length")
        try:
            if content_length and int(content_length) > self.settings.max_remote_asset_bytes:
                raise RemoteDownloadError("Remote asset exceeds the configured size limit.")
        except ValueError as exc:
            raise RemoteDownloadError("Remote asset returned an invalid content length.") from exc

        downloaded = 0
        try:
            with temporary.open("wb") as output:
                for chunk in response.iter_bytes():
                    downloaded += len(chunk)
                    if downloaded > self.settings.max_remote_asset_bytes:
                        raise RemoteDownloadError("Remote asset exceeds the configured size limit.")
                    output.write(chunk)
            if downloaded == 0:
                raise RemoteDownloadError("Remote asset was empty.")
            media_type = content_type or content_type_for_extension(extension, expected_kind)
            with temporary.open("rb") as downloaded_file:
                validate_magic_bytes(downloaded_file.read(4096), media_type)
            os.replace(temporary, final_path)
            return final_path
        except RemoteDownloadError:
            temporary.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise
        except (OSError, MediaValidationError) as exc:
            temporary.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise RemoteDownloadError("Remote asset failed media validation.") from exc
