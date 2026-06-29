from pathlib import Path
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.core.errors import ProviderBadResponseError, ProviderError
from backend.app.wavespeed_api import poll_prediction, submit_prediction


class WaveSpeedLegacyHTTPClient:
    provider_mode = "legacy_http"

    def __init__(self, settings: Settings, *, api_key: str | None = None) -> None:
        self.settings = settings
        self.api_key = api_key or settings.wavespeed_api_key

    def run_model(
        self,
        model: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
        enable_sync_mode: bool = False,
    ) -> dict[str, Any]:
        del timeout_seconds, poll_interval_seconds, enable_sync_mode
        with httpx.Client(timeout=30.0) as client:
            submitted = submit_prediction(
                client,
                self.api_key,
                model,
                payload,
                api_base_url=self.settings.wavespeed_api_base_url,
            )
            urls = submitted.get("urls")
            status_url = urls.get("get") if isinstance(urls, dict) else None
            if not isinstance(status_url, str) or not status_url:
                raise ProviderBadResponseError(
                    "WaveSpeed submit response was missing the result URL."
                )
            return poll_prediction(
                client,
                self.api_key,
                status_url,
                "Timed out waiting for WaveSpeed prediction results.",
            )

    def upload_file(self, path: Path) -> str:
        raise ProviderError("Legacy WaveSpeed file upload is not supported.")

    def sdk_version(self) -> str | None:
        return None
