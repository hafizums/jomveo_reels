from fastapi import APIRouter, Request

from backend.app.video_generator import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    generate_video,
)

router = APIRouter()


@router.post("/generate", response_model=VideoGenerationResponse)
def create_video(payload: VideoGenerationRequest, request: Request) -> VideoGenerationResponse:
    return generate_video(payload, settings=request.app.state.settings)
