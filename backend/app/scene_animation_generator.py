from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.app.wavespeed_api import extract_asset_url, poll_prediction, submit_prediction

WAN_I2V_MODEL = "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast"
DEFAULT_NEGATIVE_PROMPT = (
    "blurry, low quality, distorted anatomy, warped face, duplicated subject, extra limbs, "
    "flicker, jitter, sudden cuts, text, logo, watermark"
)


class SceneAnimationInput(BaseModel):
    scene_number: int = Field(..., ge=1, le=10)
    image_url: str = Field(..., min_length=8, max_length=2000)
    motion_prompt: str = Field(..., min_length=10, max_length=1500)


class SceneAnimationRequest(BaseModel):
    scenes: list[SceneAnimationInput] = Field(..., min_length=1, max_length=10)
    duration: Literal[5, 8] = 5
    negative_prompt: str = Field(default=DEFAULT_NEGATIVE_PROMPT, max_length=1000)
    model: str = Field(default=WAN_I2V_MODEL, min_length=1, max_length=120)


class AnimatedScene(BaseModel):
    scene_number: int
    image_url: str
    motion_prompt: str
    video_url: str
    duration: int


class SceneAnimationResponse(BaseModel):
    model: str
    duration: int
    scene_count: int
    scenes: list[AnimatedScene]


def generate_scene_animations(
    api_key: str,
    payload: SceneAnimationRequest,
) -> SceneAnimationResponse:
    ordered_inputs = sorted(payload.scenes, key=lambda scene: scene.scene_number)

    def animate_scene(scene: SceneAnimationInput) -> AnimatedScene:
        with httpx.Client(timeout=30.0) as client:
            submitted = submit_prediction(
                client,
                api_key,
                payload.model,
                {
                    "prompt": scene.motion_prompt,
                    "image": scene.image_url,
                    "negative_prompt": payload.negative_prompt,
                    "duration": payload.duration,
                    "seed": -1,
                },
            )
            output = poll_prediction(
                client,
                api_key,
                submitted["urls"]["get"],
                timeout_detail=f"Timed out animating scene {scene.scene_number}.",
            )

        video_url = extract_asset_url(output.get("outputs"))
        if not video_url:
            raise HTTPException(
                status_code=502,
                detail=f"WaveSpeed did not return a video URL for scene {scene.scene_number}.",
            )
        return AnimatedScene(
            scene_number=scene.scene_number,
            image_url=scene.image_url,
            motion_prompt=scene.motion_prompt,
            video_url=video_url,
            duration=payload.duration,
        )

    with ThreadPoolExecutor(max_workers=min(2, len(ordered_inputs))) as executor:
        animated_scenes = list(executor.map(animate_scene, ordered_inputs))

    return SceneAnimationResponse(
        model=payload.model,
        duration=payload.duration,
        scene_count=len(animated_scenes),
        scenes=animated_scenes,
    )
