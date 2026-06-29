from importlib import metadata, util
from typing import Any

from fastapi import APIRouter, Query, Request

from backend.app.infrastructure.providers.wavespeed import create_wavespeed_provider_client

router = APIRouter()


def _sdk_version() -> str | None:
    if util.find_spec("wavespeed") is None:
        return None
    try:
        return metadata.version("wavespeed")
    except metadata.PackageNotFoundError:
        return None


@router.get("/wavespeed/status")
def wavespeed_status(request: Request, live: bool = Query(default=False)) -> dict[str, Any]:
    settings = request.app.state.settings
    sdk_version = _sdk_version()
    response: dict[str, Any] = {
        "provider": "wavespeed",
        "mode": settings.wavespeed_provider_mode,
        "sdk_available": sdk_version is not None,
        "sdk_version": sdk_version,
        "api_key_configured": bool(settings.wavespeed_api_key),
        "chat_completions_mode": "legacy_http",
        "live_check_enabled": settings.allow_provider_live_checks,
        "live_check_status": "not_requested",
    }
    if not live:
        return response
    if not settings.allow_provider_live_checks:
        response["live_check_status"] = "disabled"
        return response
    if not settings.wavespeed_api_key:
        response["live_check_status"] = "not_configured"
        return response

    client = create_wavespeed_provider_client(settings)
    response["live_check_status"] = "client_initialized"
    response["provider_mode"] = client.provider_mode
    response["provider_sdk_version"] = client.sdk_version()
    return response
