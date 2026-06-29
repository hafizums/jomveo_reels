from typing import Annotated

from fastapi import Depends

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import ConfigurationError


def require_wavespeed_api_key(settings: Annotated[Settings, Depends(get_settings)]) -> str:
    api_key = settings.wavespeed_api_key.strip()
    if not api_key:
        raise ConfigurationError(
            "Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment."
        )
    return api_key
