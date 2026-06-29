from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import require_wavespeed_api_key
from backend.app.art_style_generator import (
    ArtStyleRequest,
    ArtStyleResponse,
    generate_art_style_image,
)

router = APIRouter()


@router.post("/generate", response_model=ArtStyleResponse)
def create_art_style_image(
    payload: ArtStyleRequest,
    request: Request,
    api_key: Annotated[str, Depends(require_wavespeed_api_key)],
) -> ArtStyleResponse:
    return generate_art_style_image(api_key, payload, settings=request.app.state.settings)
