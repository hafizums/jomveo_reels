import json
from concurrent.futures import ThreadPoolExecutor
from textwrap import dedent
from threading import Lock
from typing import Any, Callable

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.app.art_style_generator import (
    DEFAULT_ART_STYLE_MODEL,
    Z_IMAGE_TURBO_MODEL,
    ArtStyleRequest,
    generate_art_style_image,
)
from backend.app.core.config import Settings, get_settings
from backend.app.infrastructure.providers.wavespeed import create_wavespeed_provider_client
from backend.app.infrastructure.providers.wavespeed.client import WaveSpeedProviderClient

LLM_BASE_URL = get_settings().wavespeed_llm_base_url
DEFAULT_SCENE_PLANNER_MODEL = "openai/gpt-5.4-mini"


class SceneSequenceRequest(BaseModel):
    script: str = Field(..., min_length=20, max_length=12000)
    title: str = Field(default="Untitled story", max_length=200)
    event_name: str = Field(default="", max_length=200)
    duration_seconds: int = Field(default=60, ge=30, le=90)
    planner_model: str = Field(default=DEFAULT_SCENE_PLANNER_MODEL, min_length=1, max_length=120)
    style_name: str = Field(default="Cinematic Realism", max_length=80)
    art_direction: str = Field(..., min_length=10, max_length=1000)
    model: str = Field(default=DEFAULT_ART_STYLE_MODEL, min_length=1, max_length=120)
    enable_safety_checker: bool = True


class PlannedScene(BaseModel):
    narration: str
    image_prompt: str
    motion_prompt: str


class GeneratedScene(BaseModel):
    scene_number: int
    narration: str
    image_prompt: str
    motion_prompt: str
    image_url: str
    safety_output: object | None = None


class SceneSequenceResponse(BaseModel):
    title: str
    event_name: str
    duration_seconds: int
    scene_count: int
    planner_model: str
    style_name: str
    art_direction: str
    model: str
    enable_safety_checker: bool
    scenes: list[GeneratedScene]


def _scene_count_range(duration_seconds: int) -> tuple[int, int]:
    minimum = max(3, min(9, round(duration_seconds / 10)))
    maximum = max(minimum, min(10, round(duration_seconds / 7.5)))
    return minimum, maximum


def _build_planner_prompt(payload: SceneSequenceRequest) -> str:
    minimum_scenes, maximum_scenes = _scene_count_range(payload.duration_seconds)
    subject = payload.event_name.strip() or payload.title.strip() or "the story's central subject"
    return dedent(
        f"""
        Create a visual storyboard for a {payload.duration_seconds}-second short-form video.

        Story title: {payload.title}
        Central subject or event: {subject}
        Selected visual direction: {payload.art_direction}

        Full narration:
        {payload.script}

        Decide the best number of scenes yourself. Use between {minimum_scenes} and
        {maximum_scenes} scenes, choosing scene changes only where the narration introduces
        a genuinely new visual beat, location, time, action, or emotional turn.

        Return one JSON object with exactly one key named "scenes". Its value must be an
        ordered array. Every scene object must contain exactly these keys:
        - narration: the exact contiguous portion of narration covered by the scene
        - image_prompt: a standalone production-ready text-to-image prompt
        - motion_prompt: concise natural subject and camera movement for animating that image

        Image prompt requirements:
        - Translate the narration into a concrete visual; never merely paste or summarize it.
        - Specify subject appearance, action, environment, historical period, camera framing,
          lighting, atmosphere, foreground, and background when relevant.
        - Repeat stable identifying details for the central subject across scenes so independently
          generated images retain visual continuity.
        - Use a cinematic vertical 9:16 composition suitable for a short-form video.
        - Show one decisive visual moment per image, not a collage or split screen.
        - Do not include captions, written words, logos, watermarks, UI, or prompt commentary.
        - Do not repeat the selected visual direction; the image generator adds it separately.

        Motion prompt requirements:
        - Describe only believable movement visible from the scene's start frame.
        - Include subtle environmental motion and one restrained camera movement.
        - Preserve identity, composition, anatomy, lighting, and background continuity.
        - Do not introduce new people, objects, locations, cuts, text, or scene changes.

        Preserve the narration order and cover the complete script once without inventing new facts.
        """
    ).strip()


def _parse_scene_plan(content: str) -> list[PlannedScene]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Scene planner returned invalid JSON.") from exc

    raw_scenes = parsed.get("scenes") if isinstance(parsed, dict) else None
    if not isinstance(raw_scenes, list) or not 2 <= len(raw_scenes) <= 10:
        raise HTTPException(
            status_code=502, detail="Scene planner must return between 2 and 10 scenes."
        )

    scenes: list[PlannedScene] = []
    for index, value in enumerate(raw_scenes, start=1):
        if not isinstance(value, dict):
            raise HTTPException(
                status_code=502,
                detail=f"Scene planner returned an invalid scene at position {index}.",
            )
        narration = value.get("narration")
        image_prompt = value.get("image_prompt")
        motion_prompt = value.get("motion_prompt")
        if not isinstance(narration, str) or not narration.strip():
            raise HTTPException(status_code=502, detail=f"Scene {index} is missing narration.")
        if not isinstance(image_prompt, str) or len(image_prompt.strip()) < 20:
            raise HTTPException(
                status_code=502, detail=f"Scene {index} is missing a detailed image prompt."
            )
        if not isinstance(motion_prompt, str) or len(motion_prompt.strip()) < 10:
            raise HTTPException(
                status_code=502, detail=f"Scene {index} is missing a motion prompt."
            )
        scenes.append(
            PlannedScene(
                narration=narration.strip(),
                image_prompt=image_prompt.strip()[:2000],
                motion_prompt=motion_prompt.strip()[:1000],
            )
        )
    return scenes


def _generate_scene_plan(api_key: str, payload: SceneSequenceRequest) -> list[PlannedScene]:
    with httpx.Client(timeout=90.0) as client:
        response = client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": payload.planner_model,
                "temperature": 0.6,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a storyboard director and expert text-to-image prompt writer. "
                            "Return valid JSON only and preserve factual accuracy."
                        ),
                    },
                    {"role": "user", "content": _build_planner_prompt(payload)},
                ],
            },
        )

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=502,
            detail="WaveSpeed denied the scene-planner request. Verify the API key and planner model access.",
        )
    try:
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Scene-planner request failed: {exc}") from exc

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise HTTPException(status_code=502, detail="Scene planner returned no choices.")
    first_choice = choices[0]
    message = first_choice.get("message") if isinstance(first_choice, dict) else None
    content: Any = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=502, detail="Scene planner returned no content.")
    return _parse_scene_plan(content)


def generate_scene_sequence(
    api_key: str,
    payload: SceneSequenceRequest,
    *,
    provider_client: WaveSpeedProviderClient | None = None,
    provider_client_factory: Callable[[], WaveSpeedProviderClient] | None = None,
    settings: Settings | None = None,
) -> SceneSequenceResponse:
    settings = settings or get_settings()
    planned_scenes = _generate_scene_plan(api_key, payload)
    scene_count = len(planned_scenes)
    shared_client_lock = Lock()

    def create_render_client() -> WaveSpeedProviderClient:
        if provider_client is not None:
            return provider_client
        factory = provider_client_factory or (
            lambda: create_wavespeed_provider_client(settings, api_key=api_key)
        )
        return factory()

    def render_scene(scene_input: tuple[int, PlannedScene]) -> GeneratedScene:
        scene_number, planned_scene = scene_input
        render_client = create_render_client()

        def generate_image():
            return generate_art_style_image(
                api_key,
                ArtStyleRequest(
                    prompt=planned_scene.image_prompt,
                    style_name=payload.style_name,
                    art_direction=payload.art_direction,
                    model=payload.model,
                    enable_safety_checker=payload.enable_safety_checker,
                ),
                provider_client=render_client,
                settings=settings,
            )

        if provider_client is None:
            image = generate_image()
        else:
            with shared_client_lock:
                image = generate_image()
        return GeneratedScene(
            scene_number=scene_number,
            narration=planned_scene.narration,
            image_prompt=image.styled_prompt,
            motion_prompt=planned_scene.motion_prompt,
            image_url=image.image_url,
            safety_output=image.safety_output,
        )

    scene_inputs = list(enumerate(planned_scenes, start=1))
    max_workers = 1 if payload.model == Z_IMAGE_TURBO_MODEL else min(3, scene_count)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        scenes = list(executor.map(render_scene, scene_inputs))

    return SceneSequenceResponse(
        title=payload.title,
        event_name=payload.event_name,
        duration_seconds=payload.duration_seconds,
        scene_count=scene_count,
        planner_model=payload.planner_model,
        style_name=payload.style_name,
        art_direction=payload.art_direction,
        model=payload.model,
        enable_safety_checker=payload.enable_safety_checker,
        scenes=scenes,
    )
