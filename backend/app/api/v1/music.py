from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import require_wavespeed_api_key
from backend.app.background_music_generator import (
    BackgroundMusicRequest,
    BackgroundMusicResponse,
    generate_background_music,
)

router = APIRouter()


@router.post("/generate", response_model=BackgroundMusicResponse)
def create_background_music(
    payload: BackgroundMusicRequest,
    api_key: Annotated[str, Depends(require_wavespeed_api_key)],
) -> BackgroundMusicResponse:
    return generate_background_music(api_key, payload)
