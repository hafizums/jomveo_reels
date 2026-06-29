from collections.abc import Callable
from typing import Any

from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError
from backend.app.script_generator import ScriptRequest, generate_video_script

JobHandler = Callable[[dict[str, Any], Settings], dict[str, Any]]


def execute_script_generation(input_json: dict[str, Any], settings: Settings) -> dict[str, Any]:
    api_key = settings.wavespeed_api_key.strip()
    if not api_key:
        raise ConfigurationError(
            "Missing WAVESPEED_API_KEY. Add it to backend/.env or your environment."
        )
    payload = ScriptRequest.model_validate(input_json)
    return generate_video_script(api_key, payload).model_dump(mode="json")


JOB_REGISTRY: dict[str, JobHandler] = {
    "script.generate": execute_script_generation,
}


def get_job_handler(job_type: str) -> JobHandler:
    try:
        return JOB_REGISTRY[job_type]
    except KeyError as exc:
        raise ConfigurationError(f"No handler is registered for job type {job_type}.") from exc
