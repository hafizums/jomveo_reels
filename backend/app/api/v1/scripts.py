from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import require_wavespeed_api_key
from backend.app.script_generator import ScriptRequest, ScriptResponse, generate_video_script

router = APIRouter()


@router.post("/generate", response_model=ScriptResponse)
def generate_script(
    payload: ScriptRequest,
    api_key: Annotated[str, Depends(require_wavespeed_api_key)],
) -> ScriptResponse:
    return generate_video_script(api_key, payload)
