from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import require_wavespeed_api_key
from backend.app.scene_animation_generator import (
    SceneAnimationRequest,
    SceneAnimationResponse,
    generate_scene_animations,
)
from backend.app.scene_generator import (
    SceneSequenceRequest,
    SceneSequenceResponse,
    generate_scene_sequence,
)

router = APIRouter()


@router.post("/art-style/scenes/generate", response_model=SceneSequenceResponse)
def create_scene_sequence(
    payload: SceneSequenceRequest,
    api_key: Annotated[str, Depends(require_wavespeed_api_key)],
) -> SceneSequenceResponse:
    return generate_scene_sequence(api_key, payload)


@router.post("/scene-animations/generate", response_model=SceneAnimationResponse)
def create_scene_animations(
    payload: SceneAnimationRequest,
    api_key: Annotated[str, Depends(require_wavespeed_api_key)],
) -> SceneAnimationResponse:
    return generate_scene_animations(api_key, payload)
