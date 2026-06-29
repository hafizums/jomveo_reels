from pathlib import Path
from typing import Any, Protocol

from backend.app.core.errors import ProviderBadResponseError
from backend.app.wavespeed_api import extract_asset_url


class WaveSpeedProviderClient(Protocol):
    provider_mode: str

    def run_model(
        self,
        model: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
        enable_sync_mode: bool = False,
    ) -> dict[str, Any]: ...

    def upload_file(self, path: Path) -> str: ...

    def sdk_version(self) -> str | None: ...


def normalize_wavespeed_response(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        response = response.model_dump(mode="json")
    if not isinstance(response, dict):
        raise ProviderBadResponseError("WaveSpeed SDK returned an invalid response.")

    normalized = dict(response)
    if "outputs" not in normalized:
        data = normalized.get("data")
        if isinstance(data, dict) and "outputs" in data:
            normalized = dict(data)
        else:
            raise ProviderBadResponseError("WaveSpeed SDK response was missing outputs.")
    if normalized.get("outputs") in (None, []):
        raise ProviderBadResponseError("WaveSpeed SDK response contained invalid outputs.")
    return normalized


def extract_outputs(response: dict[str, Any]) -> list[Any]:
    normalized = normalize_wavespeed_response(response)
    outputs = normalized["outputs"]
    return outputs if isinstance(outputs, list) else [outputs]


def extract_first_asset_url(response: dict[str, Any]) -> str:
    url = extract_asset_url(extract_outputs(response))
    if not url:
        raise ProviderBadResponseError("WaveSpeed response did not include an asset URL.")
    return url
