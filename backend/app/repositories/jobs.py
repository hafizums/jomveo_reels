from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.app.core.errors import JobNotFoundError
from backend.app.db.models import GenerationJob, utc_now


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        job_type: str,
        input_json: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> GenerationJob:
        job = GenerationJob(
            type=job_type,
            status="queued",
            input_json=input_json,
            idempotency_key=idempotency_key,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: str) -> GenerationJob | None:
        return self.session.get(GenerationJob, job_id)

    def get_or_raise(self, job_id: str) -> GenerationJob:
        job = self.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} was not found.")
        return job

    def find_by_idempotency_key(
        self,
        job_type: str,
        idempotency_key: str,
    ) -> GenerationJob | None:
        statement = select(GenerationJob).where(
            GenerationJob.type == job_type,
            GenerationJob.idempotency_key == idempotency_key,
        )
        return self.session.scalar(statement)

    def list_recent(self, limit: int) -> list[GenerationJob]:
        statement: Select[tuple[GenerationJob]] = (
            select(GenerationJob).order_by(GenerationJob.created_at.desc()).limit(limit)
        )
        return list(self.session.scalars(statement))

    def mark_running(self, job: GenerationJob) -> None:
        job.status = "running"
        job.started_at = utc_now()
        job.updated_at = utc_now()

    def mark_completed(self, job: GenerationJob, result: dict[str, Any]) -> None:
        now = utc_now()
        job.status = "completed"
        job.result_json = result
        job.error_code = None
        job.error_message = None
        job.progress_current = job.progress_total
        job.completed_at = now
        job.updated_at = now

    def mark_failed(self, job: GenerationJob, code: str, message: str) -> None:
        now = utc_now()
        job.status = "failed"
        job.error_code = code
        job.error_message = message
        job.completed_at = now
        job.updated_at = now
