from typing import Any

from pydantic import BaseModel, Field

from backend.app.core.config import Settings, get_settings
from backend.app.infrastructure.providers.wavespeed import create_wavespeed_provider_client
from backend.app.infrastructure.providers.wavespeed.client import (
    WaveSpeedProviderClient,
    extract_first_asset_url,
)

DEFAULT_ART_STYLE_MODEL = "google/nano-banana/text-to-image"
Z_IMAGE_TURBO_MODEL = "wavespeed-ai/z-image/turbo"
IMAGE_SAFETY_MODEL = "wavespeed-ai/content-moderator/image"


class ArtStyleRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=2000)
    style_name: str = Field(default="Cinematic Realism", max_length=80)
    art_direction: str = Field(..., min_length=10, max_length=1000)
    model: str = Field(default=DEFAULT_ART_STYLE_MODEL, min_length=1, max_length=120)
    enable_safety_checker: bool = True


class ArtStyleResponse(BaseModel):
    prompt: str
    style_name: str
    art_direction: str
    styled_prompt: str
    model: str
    enable_safety_checker: bool
    safety_output: Any | None
    image_url: str
    raw_output: dict[str, Any]


def _build_styled_prompt(payload: ArtStyleRequest) -> str:
    return (
        f"{payload.prompt}. Visual art direction: {payload.art_direction}. "
        "Create a polished image with strong composition, no text, no logo, no watermark."
    )


def generate_art_style_image(
    api_key: str,
    payload: ArtStyleRequest,
    *,
    provider_client: WaveSpeedProviderClient | None = None,
    settings: Settings | None = None,
) -> ArtStyleResponse:
    settings = settings or get_settings()
    provider_client = provider_client or create_wavespeed_provider_client(settings, api_key=api_key)
    styled_prompt = _build_styled_prompt(payload)
    model_payload: dict[str, Any] = {"prompt": styled_prompt}
    if payload.model == Z_IMAGE_TURBO_MODEL:
        model_payload["size"] = "864*1536"

    output = provider_client.run_model(payload.model, model_payload)

    image_url = extract_first_asset_url(output)

    safety_output: Any | None = None
    if payload.enable_safety_checker:
        safety_result = provider_client.run_model(
            IMAGE_SAFETY_MODEL,
            {
                "image": image_url,
                "text": payload.prompt,
            },
        )
        safety_output = safety_result.get("outputs")

    return ArtStyleResponse(
        prompt=payload.prompt,
        style_name=payload.style_name,
        art_direction=payload.art_direction,
        styled_prompt=styled_prompt,
        model=payload.model,
        enable_safety_checker=payload.enable_safety_checker,
        safety_output=safety_output,
        image_url=image_url,
        raw_output=output,
    )
