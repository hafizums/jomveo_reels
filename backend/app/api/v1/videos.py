from fastapi import APIRouter

from backend.app.video_generator import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    generate_video,
)

router = APIRouter()


@router.post("/generate", response_model=VideoGenerationResponse)
def create_video(payload: VideoGenerationRequest) -> VideoGenerationResponse:
    return generate_video(payload)
