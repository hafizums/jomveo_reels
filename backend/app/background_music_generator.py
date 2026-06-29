from typing import Any

from pydantic import BaseModel, Field

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import ProviderBadResponseError
from backend.app.infrastructure.providers.wavespeed import create_wavespeed_provider_client
from backend.app.infrastructure.providers.wavespeed.client import WaveSpeedProviderClient
from backend.app.wavespeed_api import extract_asset_url

DEFAULT_BACKGROUND_MUSIC_MODEL = "mureka-ai/mureka-v9/generate-bgm"
DEFAULT_OUTPUT_FORMAT = "mp3"
DEFAULT_NUMBER_OF_SONGS = 1
DEFAULT_BACKGROUND_MUSIC_PROMPT = (
    "Dark cinematic documentary background music, slow pulse, low strings, distant "
    "percussion, restrained tension, modern trailer-style production, instrumental only"
)


class BackgroundMusicRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=1024)
    style_name: str = Field(default="Dark Documentary", max_length=80)
    number_of_songs: int = Field(default=DEFAULT_NUMBER_OF_SONGS, ge=1, le=3)
    output_format: str = Field(default=DEFAULT_OUTPUT_FORMAT, min_length=3, max_length=10)
    model: str = Field(default=DEFAULT_BACKGROUND_MUSIC_MODEL, min_length=1, max_length=120)


class BackgroundMusicResponse(BaseModel):
    prompt: str
    style_name: str
    number_of_songs: int
    output_format: str
    model: str
    audio_urls: list[str]
    raw_output: dict[str, Any]


def _extract_audio_urls(value: Any) -> list[str]:
    if isinstance(value, list):
        urls = [
            item
            for item in value
            if isinstance(item, str) and item.startswith(("http://", "https://"))
        ]
        return urls

    single_url = extract_asset_url(value)
    return [single_url] if single_url else []


def generate_background_music(
    api_key: str,
    payload: BackgroundMusicRequest,
    *,
    provider_client: WaveSpeedProviderClient | None = None,
    settings: Settings | None = None,
) -> BackgroundMusicResponse:
    settings = settings or get_settings()
    provider_client = provider_client or create_wavespeed_provider_client(settings, api_key=api_key)
    output = provider_client.run_model(
        payload.model,
        {
            "prompt": payload.prompt,
            "number_of_songs": payload.number_of_songs,
            "output_format": payload.output_format,
        },
    )

    audio_urls = _extract_audio_urls(output.get("outputs"))
    if not audio_urls:
        raise ProviderBadResponseError(
            "WaveSpeed response did not include any background music URLs."
        )

    return BackgroundMusicResponse(
        prompt=payload.prompt,
        style_name=payload.style_name,
        number_of_songs=payload.number_of_songs,
        output_format=payload.output_format,
        model=payload.model,
        audio_urls=audio_urls,
        raw_output=output,
    )
