from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

JobStatus = Literal["queued", "running", "completed", "failed", "cancelled", "retrying"]


class JobAcceptedResponse(BaseModel):
    job_id: str
    type: str
    status: JobStatus
    created_at: datetime
    status_url: str


class JobErrorResponse(BaseModel):
    code: str
    message: str


class JobDetailResponse(BaseModel):
    job_id: str
    type: str
    status: JobStatus
    progress_current: int
    progress_total: int
    attempt_count: int
    max_attempts: int
    next_retry_at: datetime | None
    result: dict[str, Any] | None
    error: JobErrorResponse | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobListResponse(BaseModel):
    jobs: list[JobDetailResponse]
    count: int


class JobRecoveryResponse(BaseModel):
    recovered_stale: int
    requeued_due: int


class JobCancellationResponse(BaseModel):
    job_id: str
    status: JobStatus
