from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from backend.app.art_style_generator import ArtStyleRequest, generate_art_style_image
from backend.app.background_music_generator import (
    BackgroundMusicRequest,
    generate_background_music,
)
from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError
from backend.app.scene_animation_generator import (
    SceneAnimationRequest,
    generate_scene_animations,
)
from backend.app.scene_generator import SceneSequenceRequest, generate_scene_sequence
from backend.app.script_generator import ScriptRequest, generate_video_script
from backend.app.video_generator import VideoGenerationRequest, generate_video
from backend.app.voiceover_generator import VoiceoverRequest, generate_voiceover

JobHandler = Callable[[dict[str, Any], Settings], dict[str, Any]]


@dataclass(frozen=True)
class JobDefinition:
    handler: JobHandler
    provider: str


def _api_key(settings: Settings) -> str:
    api_key = settings.wavespeed_api_key.strip()
    if not api_key:
        raise ConfigurationError(
            "Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment."
        )
    return api_key


def execute_script_generation(input_json: dict[str, Any], settings: Settings) -> dict[str, Any]:
    payload = ScriptRequest.model_validate(input_json)
    return generate_video_script(_api_key(settings), payload).model_dump(mode="json")


def execute_voiceover_generation(input_json: dict[str, Any], settings: Settings) -> dict[str, Any]:
    payload = VoiceoverRequest.model_validate(input_json)
    return generate_voiceover(_api_key(settings), payload).model_dump(mode="json")


def execute_background_music_generation(
    input_json: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    payload = BackgroundMusicRequest.model_validate(input_json)
    return generate_background_music(_api_key(settings), payload).model_dump(mode="json")


def execute_art_style_generation(input_json: dict[str, Any], settings: Settings) -> dict[str, Any]:
    payload = ArtStyleRequest.model_validate(input_json)
    return generate_art_style_image(_api_key(settings), payload).model_dump(mode="json")


def execute_scene_sequence_generation(
    input_json: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    payload = SceneSequenceRequest.model_validate(input_json)
    return generate_scene_sequence(_api_key(settings), payload).model_dump(mode="json")


def execute_scene_animation_generation(
    input_json: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    payload = SceneAnimationRequest.model_validate(input_json)
    return generate_scene_animations(_api_key(settings), payload).model_dump(mode="json")


def execute_video_generation(input_json: dict[str, Any], _settings: Settings) -> dict[str, Any]:
    payload = VideoGenerationRequest.model_validate(input_json)
    return generate_video(payload, settings=_settings).model_dump(mode="json")


JOB_REGISTRY: dict[str, JobDefinition] = {
    "script.generate": JobDefinition(execute_script_generation, "wavespeed"),
    "voiceover.generate": JobDefinition(execute_voiceover_generation, "wavespeed"),
    "background_music.generate": JobDefinition(execute_background_music_generation, "wavespeed"),
    "art_style.generate": JobDefinition(execute_art_style_generation, "wavespeed"),
    "scene_sequence.generate": JobDefinition(execute_scene_sequence_generation, "wavespeed"),
    "scene_animation.generate": JobDefinition(execute_scene_animation_generation, "wavespeed"),
    "video.generate": JobDefinition(execute_video_generation, "local_media"),
}


def get_job_definition(job_type: str) -> JobDefinition:
    try:
        return JOB_REGISTRY[job_type]
    except KeyError as exc:
        raise ConfigurationError(f"No handler is registered for job type {job_type}.") from exc
