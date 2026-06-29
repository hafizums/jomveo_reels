import logging
from pathlib import Path
from typing import Any

import requests
import wavespeed
from wavespeed import Client

from backend.app.core.config import Settings
from backend.app.core.errors import (
    ProviderAuthError,
    ProviderBadResponseError,
    ProviderError,
    ProviderForbiddenError,
    ProviderTimeoutError,
)
from backend.app.infrastructure.providers.wavespeed.client import normalize_wavespeed_response

logger = logging.getLogger(__name__)


class WaveSpeedSDKClient:
    provider_mode = "sdk"

    def __init__(
        self,
        settings: Settings,
        *,
        sdk_client: Any | None = None,
        api_key: str | None = None,
    ) -> None:
        self.settings = settings
        self.client = sdk_client or Client(api_key=api_key or settings.wavespeed_api_key)

    def run_model(
        self,
        model: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
        enable_sync_mode: bool = False,
    ) -> dict[str, Any]:
        try:
            response = self.client.run(
                model,
                payload,
                timeout=(
                    self.settings.wavespeed_sdk_timeout_seconds
                    if timeout_seconds is None
                    else timeout_seconds
                ),
                poll_interval=(
                    self.settings.wavespeed_sdk_poll_interval_seconds
                    if poll_interval_seconds is None
                    else poll_interval_seconds
                ),
                enable_sync_mode=(enable_sync_mode or self.settings.wavespeed_sdk_enable_sync_mode),
            )
            return normalize_wavespeed_response(response)
        except ProviderBadResponseError:
            raise
        except Exception as exc:
            raise self._map_exception(exc) from exc

    def upload_file(self, path: Path) -> str:
        if not path.is_file():
            raise ProviderBadResponseError("WaveSpeed upload source file does not exist.")
        try:
            url = self.client.upload(
                str(path),
                timeout=self.settings.wavespeed_sdk_timeout_seconds,
            )
        except Exception as exc:
            raise self._map_exception(exc) from exc
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ProviderBadResponseError("WaveSpeed SDK upload returned an invalid URL.")
        return url

    def sdk_version(self) -> str | None:
        version = getattr(wavespeed, "__version__", None)
        return str(version) if version else None

    def _map_exception(self, exc: Exception) -> ProviderError:
        logger.warning(
            "wavespeed_sdk_failure",
            extra={"sdk_exception_type": type(exc).__name__},
        )
        message = str(exc).casefold()
        cause = exc.__cause__
        if (
            isinstance(
                exc,
                (TimeoutError, requests.exceptions.Timeout),
            )
            or isinstance(cause, (TimeoutError, requests.exceptions.Timeout))
            or any(marker in message for marker in ("timed out", "timeout"))
        ):
            return ProviderTimeoutError("WaveSpeed SDK request timed out.")
        if any(marker in message for marker in ("http 401", "unauthorized")):
            return ProviderAuthError("WaveSpeed rejected the configured API key.")
        if any(marker in message for marker in ("http 403", "forbidden", "denied")):
            return ProviderForbiddenError("WaveSpeed denied access to the requested model.")
        if isinstance(exc, ValueError) and "api key" in message:
            return ProviderAuthError("WaveSpeed rejected the configured API key.")
        if any(
            marker in message
            for marker in (
                "no request id",
                "missing outputs",
                "invalid response",
                "no download_url",
                "invalid json",
            )
        ):
            return ProviderBadResponseError("WaveSpeed SDK returned an invalid response.")
        return ProviderError("WaveSpeed SDK request failed.")
