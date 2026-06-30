import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request

from backend.app.application.jobs.schemas import (
    JobAcceptedResponse,
    JobCancellationResponse,
    JobDetailResponse,
    JobListResponse,
    JobRecoveryResponse,
)
from backend.app.application.jobs.service import JobService
from backend.app.art_style_generator import ArtStyleRequest
from backend.app.auth.dependencies import require_admin, require_principal
from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.background_music_generator import BackgroundMusicRequest
from backend.app.scene_animation_generator import SceneAnimationRequest
from backend.app.scene_generator import SceneSequenceRequest
from backend.app.script_generator import ScriptRequest
from backend.app.video_generator import VideoGenerationRequest
from backend.app.voiceover_generator import VoiceoverRequest

router = APIRouter()
logger = logging.getLogger(__name__)
IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key")]
AdminPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_admin)]
Principal = Annotated[AuthenticatedPrincipal, Depends(require_principal)]
ProjectId = Annotated[str | None, Header(alias="X-Project-ID")]


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


@router.post("/scripts/generate", response_model=JobAcceptedResponse)
def create_script_job(
    payload: ScriptRequest,
    request: Request,
    principal: Principal,
    idempotency_key: IdempotencyKey = None,
    project_id: ProjectId = None,
) -> JobAcceptedResponse:
    return get_job_service(request).create_job(
        "script.generate", payload, idempotency_key, principal, project_id
    )


@router.post("/voiceovers/generate", response_model=JobAcceptedResponse)
def create_voiceover_job(
    payload: VoiceoverRequest,
    request: Request,
    principal: Principal,
    idempotency_key: IdempotencyKey = None,
    project_id: ProjectId = None,
) -> JobAcceptedResponse:
    return get_job_service(request).create_job(
        "voiceover.generate", payload, idempotency_key, principal, project_id
    )


@router.post("/background-music/generate", response_model=JobAcceptedResponse)
def create_background_music_job(
    payload: BackgroundMusicRequest,
    request: Request,
    principal: Principal,
    idempotency_key: IdempotencyKey = None,
    project_id: ProjectId = None,
) -> JobAcceptedResponse:
    return get_job_service(request).create_job(
        "background_music.generate", payload, idempotency_key, principal, project_id
    )


@router.post("/art-style/generate", response_model=JobAcceptedResponse)
def create_art_style_job(
    payload: ArtStyleRequest,
    request: Request,
    principal: Principal,
    idempotency_key: IdempotencyKey = None,
    project_id: ProjectId = None,
) -> JobAcceptedResponse:
    return get_job_service(request).create_job(
        "art_style.generate", payload, idempotency_key, principal, project_id
    )


@router.post("/art-style/scenes/generate", response_model=JobAcceptedResponse)
def create_scene_sequence_job(
    payload: SceneSequenceRequest,
    request: Request,
    principal: Principal,
    idempotency_key: IdempotencyKey = None,
    project_id: ProjectId = None,
) -> JobAcceptedResponse:
    return get_job_service(request).create_job(
        "scene_sequence.generate", payload, idempotency_key, principal, project_id
    )


@router.post("/scene-animations/generate", response_model=JobAcceptedResponse)
def create_scene_animation_job(
    payload: SceneAnimationRequest,
    request: Request,
    principal: Principal,
    idempotency_key: IdempotencyKey = None,
    project_id: ProjectId = None,
) -> JobAcceptedResponse:
    return get_job_service(request).create_job(
        "scene_animation.generate", payload, idempotency_key, principal, project_id
    )


@router.post("/videos/generate", response_model=JobAcceptedResponse)
def create_video_job(
    payload: VideoGenerationRequest,
    request: Request,
    principal: Principal,
    idempotency_key: IdempotencyKey = None,
    project_id: ProjectId = None,
) -> JobAcceptedResponse:
    return get_job_service(request).create_job(
        "video.generate", payload, idempotency_key, principal, project_id
    )


@router.post("/recover-stale", response_model=JobRecoveryResponse)
def recover_stale(request: Request, principal: AdminPrincipal) -> JobRecoveryResponse:
    logger.info(
        "admin_action",
        extra={
            "admin_action": "job_recover_stale",
            "principal_subject": principal.subject,
        },
    )
    return get_job_service(request).recover_jobs(principal)


@router.get("", response_model=JobListResponse)
def list_jobs(
    request: Request,
    principal: Principal,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobListResponse:
    return get_job_service(request).list_jobs(limit, principal)


@router.post("/{job_id}/cancel", response_model=JobCancellationResponse)
def cancel_job(
    job_id: str,
    request: Request,
    principal: AdminPrincipal,
) -> JobCancellationResponse:
    logger.info(
        "admin_action",
        extra={
            "admin_action": "job_cancel",
            "principal_subject": principal.subject,
            "target_job_id": job_id,
        },
    )
    return get_job_service(request).cancel_job(job_id, principal)


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, request: Request, principal: Principal) -> JobDetailResponse:
    return get_job_service(request).get_job(job_id, principal)
