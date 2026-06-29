from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.app.wavespeed_api import extract_asset_url, poll_prediction, submit_prediction

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


def generate_art_style_image(api_key: str, payload: ArtStyleRequest) -> ArtStyleResponse:
    styled_prompt = _build_styled_prompt(payload)
    model_payload: dict[str, Any] = {"prompt": styled_prompt}
    if payload.model == Z_IMAGE_TURBO_MODEL:
        model_payload["size"] = "864*1536"

    with httpx.Client(timeout=30.0) as client:
        submitted = submit_prediction(
            client,
            api_key,
            payload.model,
            model_payload,
        )
        output = poll_prediction(
            client,
            api_key,
            submitted["urls"]["get"],
            timeout_detail="Timed out waiting for WaveSpeed to finish generating the art-style image.",
        )

    image_url = extract_asset_url(output.get("outputs"))
    if not image_url:
        raise HTTPException(
            status_code=502,
            detail="WaveSpeed response did not include an art-style image URL.",
        )

    safety_output: Any | None = None
    if payload.enable_safety_checker:
        with httpx.Client(timeout=30.0) as client:
            safety_submitted = submit_prediction(
                client,
                api_key,
                IMAGE_SAFETY_MODEL,
                {
                    "image": image_url,
                    "text": payload.prompt,
                },
            )
            safety_result = poll_prediction(
                client,
                api_key,
                safety_submitted["urls"]["get"],
                timeout_detail="Timed out waiting for the image safety check.",
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
