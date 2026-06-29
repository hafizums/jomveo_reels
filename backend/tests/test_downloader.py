from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from backend.app.core.config import Settings
from backend.app.core.errors import RemoteDownloadError, UnsafeRemoteURLError
from backend.app.media.downloader import RemoteAssetDownloader


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        generated_root=tmp_path,
        local_storage_root=tmp_path,
        **overrides,
    )


def _resolver(hostname: str, _port: int) -> list[str]:
    if hostname in {"localhost", "127.0.0.1"}:
        return ["127.0.0.1"]
    if hostname == "example.com":
        return ["93.184.216.34"]
    return [hostname]


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/file",
        "http://127.0.0.1/file",
        "http://10.0.0.1/file",
        "http://172.16.0.1/file",
        "http://192.168.1.1/file",
        "http://169.254.169.254/latest/meta-data",
        "http://0.0.0.0/file",
        "http://224.0.0.1/file",
        "http://[::1]/file",
        "file:///etc/passwd",
        "ftp://example.com/file",
        "https://user:pass@example.com/file",
    ],
)
def test_downloader_rejects_unsafe_urls(tmp_path: Path, url: str) -> None:
    downloader = RemoteAssetDownloader(_settings(tmp_path), resolver=_resolver)
    try:
        with pytest.raises(UnsafeRemoteURLError):
            downloader.validate_url(url)
    finally:
        downloader.close()


def test_downloader_allows_public_https_url_with_safe_dns(tmp_path: Path) -> None:
    downloader = RemoteAssetDownloader(
        _settings(tmp_path),
        resolver=lambda _host, _port: ["93.184.216.34"],
    )
    try:
        downloader.validate_url("https://example.com/media/image.png")
    finally:
        downloader.close()


class ChunkedStream(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield b"\x89PNG\r\n\x1a\n"
        yield b"too-large"


def test_downloader_enforces_streamed_byte_limit(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "image/png"},
            stream=ChunkedStream(),
            request=request,
        )
    )
    settings = _settings(tmp_path, max_remote_asset_bytes=10)
    with httpx.Client(transport=transport) as client:
        downloader = RemoteAssetDownloader(
            settings,
            client=client,
            resolver=lambda _host, _port: ["93.184.216.34"],
        )
        with pytest.raises(RemoteDownloadError, match="size limit"):
            downloader.download(
                "https://example.com/image.png",
                tmp_path / "asset",
                "image",
            )

    assert list(tmp_path.glob("*.part")) == []


def test_downloader_saves_valid_media_with_content_type_extension(tmp_path: Path) -> None:
    content = b"\x89PNG\r\n\x1a\nvalid"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "image/png", "content-length": str(len(content))},
            content=content,
            request=request,
        )
    )
    with httpx.Client(transport=transport) as client:
        downloader = RemoteAssetDownloader(
            _settings(tmp_path),
            client=client,
            resolver=lambda _host, _port: ["93.184.216.34"],
        )
        saved = downloader.download(
            "https://example.com/image",
            tmp_path / "asset",
            "image",
        )

    assert saved.name == "asset.png"
    assert saved.read_bytes() == content


def test_downloader_revalidates_redirect_targets(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            302,
            headers={"location": "http://127.0.0.1/private"},
            request=request,
        )
    )
    with httpx.Client(transport=transport) as client:
        downloader = RemoteAssetDownloader(
            _settings(tmp_path),
            client=client,
            resolver=_resolver,
        )
        with pytest.raises(UnsafeRemoteURLError):
            downloader.download(
                "https://example.com/image.png",
                tmp_path / "asset",
                "image",
            )
