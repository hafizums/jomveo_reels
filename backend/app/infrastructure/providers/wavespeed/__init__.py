"""WaveSpeed provider integration."""

from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError
from backend.app.infrastructure.providers.wavespeed.client import WaveSpeedProviderClient
from backend.app.infrastructure.providers.wavespeed.legacy_http_client import (
    WaveSpeedLegacyHTTPClient,
)
from backend.app.infrastructure.providers.wavespeed.sdk_client import WaveSpeedSDKClient


def create_wavespeed_provider_client(
    settings: Settings,
    *,
    api_key: str | None = None,
) -> WaveSpeedProviderClient:
    mode = settings.wavespeed_provider_mode.casefold()
    if mode == "sdk":
        return WaveSpeedSDKClient(settings, api_key=api_key)
    if mode == "legacy_http":
        return WaveSpeedLegacyHTTPClient(settings, api_key=api_key)
    raise ConfigurationError(f"Unsupported WAVESPEED_PROVIDER_MODE: {mode}")


__all__ = [
    "WaveSpeedLegacyHTTPClient",
    "WaveSpeedProviderClient",
    "WaveSpeedSDKClient",
    "create_wavespeed_provider_client",
]
