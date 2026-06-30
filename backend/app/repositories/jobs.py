from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.orm import Session

from backend.app.core.errors import JobNotFoundError
from backend.app.db.models import GenerationJob, ProjectMember, utc_now


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        job_type: str,
        input_json: dict[str, Any],
        max_attempts: int,
        idempotency_key: str | None = None,
        project_id: str | None = None,
        created_by_user_id: str | None = None,
    ) -> GenerationJob:
        job = GenerationJob(
            type=job_type,
            status="queued",
            input_json=input_json,
            max_attempts=max_attempts,
            idempotency_key=idempotency_key,
            project_id=project_id,
            created_by_user_id=created_by_user_id,
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

    def list_for_project(self, project_id: str, limit: int = 100) -> list[GenerationJob]:
        statement = (
            select(GenerationJob)
            .where(GenerationJob.project_id == project_id)
            .order_by(GenerationJob.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_for_user(
        self, user_id: str, limit: int, include_unowned: bool = False
    ) -> list[GenerationJob]:
        project_ids = select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        ownership = or_(
            GenerationJob.created_by_user_id == user_id,
            GenerationJob.project_id.in_(project_ids),
        )
        if include_unowned:
            ownership = or_(ownership, GenerationJob.created_by_user_id.is_(None))
        statement = (
            select(GenerationJob)
            .where(ownership)
            .order_by(GenerationJob.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def find_stale_running(self, cutoff: datetime) -> list[GenerationJob]:
        statement = select(GenerationJob).where(
            GenerationJob.status == "running",
            or_(
                GenerationJob.last_heartbeat_at < cutoff,
                and_(
                    GenerationJob.last_heartbeat_at.is_(None),
                    GenerationJob.updated_at < cutoff,
                ),
            ),
        )
        return list(self.session.scalars(statement))

    def find_due_retries(self, now: datetime) -> list[GenerationJob]:
        statement = select(GenerationJob).where(
            GenerationJob.status == "retrying",
            GenerationJob.next_retry_at.is_not(None),
            GenerationJob.next_retry_at <= now,
        )
        return list(self.session.scalars(statement))

    def mark_running(self, job: GenerationJob, worker_id: str) -> None:
        now = utc_now()
        job.status = "running"
        job.attempt_count += 1
        job.started_at = job.started_at or now
        job.locked_at = now
        job.lock_owner = worker_id
        job.last_heartbeat_at = now
        job.next_retry_at = None
        job.error_code = None
        job.error_message = None
        job.updated_at = now

    def claim_for_execution(self, job_id: str, worker_id: str) -> GenerationJob | None:
        now = utc_now()
        statement = (
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == "queued")
            .values(
                status="running",
                attempt_count=GenerationJob.attempt_count + 1,
                started_at=func.coalesce(GenerationJob.started_at, now),
                locked_at=now,
                lock_owner=worker_id,
                last_heartbeat_at=now,
                next_retry_at=None,
                error_code=None,
                error_message=None,
                updated_at=now,
            )
        )
        result = self.session.execute(statement)
        if result.rowcount != 1:  # type: ignore[attr-defined]
            return None
        return self.get(job_id)

    def set_progress_total(self, job: GenerationJob, total: int) -> None:
        job.progress_total = max(1, total)
        job.progress_current = min(job.progress_current, job.progress_total)
        job.updated_at = utc_now()

    def mark_progress(self, job: GenerationJob, current: int, total: int) -> None:
        job.progress_total = max(1, total)
        job.progress_current = max(0, min(current, job.progress_total))
        job.updated_at = utc_now()

    def heartbeat(self, job: GenerationJob) -> None:
        now = utc_now()
        job.last_heartbeat_at = now
        job.updated_at = now

    def mark_completed(self, job: GenerationJob, result: dict[str, Any]) -> None:
        now = utc_now()
        job.status = "completed"
        job.result_json = result
        job.error_code = None
        job.error_message = None
        job.progress_current = job.progress_total
        job.completed_at = now
        job.next_retry_at = None
        job.locked_at = None
        job.lock_owner = None
        job.updated_at = now

    def mark_failed(self, job: GenerationJob, code: str, message: str) -> None:
        now = utc_now()
        job.status = "failed"
        job.error_code = code
        job.error_message = message
        job.completed_at = now
        job.next_retry_at = None
        job.locked_at = None
        job.lock_owner = None
        job.updated_at = now

    def mark_retrying(
        self,
        job: GenerationJob,
        code: str,
        message: str,
        next_retry_at: datetime,
    ) -> None:
        job.status = "retrying"
        job.error_code = code
        job.error_message = message
        job.next_retry_at = next_retry_at
        job.completed_at = None
        job.locked_at = None
        job.lock_owner = None
        job.updated_at = utc_now()

    def mark_queued(self, job: GenerationJob) -> None:
        job.status = "queued"
        job.next_retry_at = None
        job.locked_at = None
        job.lock_owner = None
        job.updated_at = utc_now()

    def cancel(self, job: GenerationJob) -> None:
        if job.status not in {"queued", "retrying", "running"}:
            return
        now = utc_now()
        job.status = "cancelled"
        job.completed_at = now
        job.next_retry_at = None
        job.locked_at = None
        job.lock_owner = None
        job.updated_at = now
