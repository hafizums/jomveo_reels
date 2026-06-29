from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.core.config import Settings, get_settings
from backend.app.infrastructure.providers.wavespeed import create_wavespeed_provider_client
from backend.app.infrastructure.providers.wavespeed.client import (
    WaveSpeedProviderClient,
    extract_first_asset_url,
)

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
    *,
    provider_client: WaveSpeedProviderClient | None = None,
    settings: Settings | None = None,
) -> SceneAnimationResponse:
    settings = settings or get_settings()
    provider_client = provider_client or create_wavespeed_provider_client(settings, api_key=api_key)
    ordered_inputs = sorted(payload.scenes, key=lambda scene: scene.scene_number)

    def animate_scene(scene: SceneAnimationInput) -> AnimatedScene:
        output = provider_client.run_model(
            payload.model,
            {
                "prompt": scene.motion_prompt,
                "image": scene.image_url,
                "negative_prompt": payload.negative_prompt,
                "duration": payload.duration,
                "seed": -1,
            },
        )

        video_url = extract_first_asset_url(output)
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
