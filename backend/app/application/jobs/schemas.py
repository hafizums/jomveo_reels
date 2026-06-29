from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


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
    result: dict[str, Any] | None
    error: JobErrorResponse | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobListResponse(BaseModel):
    jobs: list[JobDetailResponse]
    count: int
