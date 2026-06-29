from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import require_wavespeed_api_key
from backend.app.voiceover_generator import VoiceoverRequest, VoiceoverResponse, generate_voiceover

router = APIRouter()


@router.post("/generate", response_model=VoiceoverResponse)
def create_voiceover(
    payload: VoiceoverRequest,
    request: Request,
    api_key: Annotated[str, Depends(require_wavespeed_api_key)],
) -> VoiceoverResponse:
    return generate_voiceover(api_key, payload, settings=request.app.state.settings)
