from typing import Annotated

from fastapi import APIRouter, Header, Query, Request

from backend.app.application.jobs.schemas import (
    JobAcceptedResponse,
    JobDetailResponse,
    JobListResponse,
)
from backend.app.application.jobs.service import JobService
from backend.app.script_generator import ScriptRequest

router = APIRouter()


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


@router.post("/scripts/generate", response_model=JobAcceptedResponse)
def create_script_job(
    payload: ScriptRequest,
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JobAcceptedResponse:
    return get_job_service(request).create_script_job(payload, idempotency_key)


@router.get("", response_model=JobListResponse)
def list_jobs(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobListResponse:
    return get_job_service(request).list_jobs(limit)


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, request: Request) -> JobDetailResponse:
    return get_job_service(request).get_job(job_id)
