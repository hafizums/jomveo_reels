from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from backend.app.application.jobs.queue import JobQueue
from backend.app.application.jobs.recovery import recover_stale_jobs, requeue_due_jobs
from backend.app.application.jobs.schemas import (
    JobAcceptedResponse,
    JobCancellationResponse,
    JobDetailResponse,
    JobErrorResponse,
    JobListResponse,
    JobRecoveryResponse,
)
from backend.app.core.config import Settings
from backend.app.core.errors import ValidationAppError
from backend.app.db.models import GenerationJob
from backend.app.db.session import SessionFactory
from backend.app.repositories.jobs import JobRepository
from backend.app.repositories.provider_runs import ProviderRunRepository


def job_to_detail(job: GenerationJob) -> JobDetailResponse:
    error = (
        JobErrorResponse(code=job.error_code, message=job.error_message)
        if job.error_code and job.error_message
        else None
    )
    return JobDetailResponse(
        job_id=job.id,
        type=job.type,
        status=job.status,  # type: ignore[arg-type]
        progress_current=job.progress_current,
        progress_total=job.progress_total,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        next_retry_at=job.next_retry_at,
        result=job.result_json,
        error=error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def job_to_accepted(job: GenerationJob, api_prefix: str) -> JobAcceptedResponse:
    return JobAcceptedResponse(
        job_id=job.id,
        type=job.type,
        status=job.status,  # type: ignore[arg-type]
        created_at=job.created_at,
        status_url=f"{api_prefix}/jobs/{job.id}",
    )


class JobService:
    def __init__(
        self,
        session_factory: SessionFactory,
        queue: JobQueue,
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.queue = queue
        self.settings = settings

    def create_job(
        self,
        job_type: str,
        payload: BaseModel,
        idempotency_key: str | None,
    ) -> JobAcceptedResponse:
        normalized_key = idempotency_key.strip() if idempotency_key else None
        if normalized_key and len(normalized_key) > 255:
            raise ValidationAppError("Idempotency-Key must not exceed 255 characters.")

        with self.session_factory() as session:
            repository = JobRepository(session)
            if normalized_key:
                existing = repository.find_by_idempotency_key(job_type, normalized_key)
                if existing:
                    return job_to_accepted(existing, self.settings.api_v1_prefix)
            try:
                job = repository.create(
                    job_type,
                    payload.model_dump(mode="json"),
                    self.settings.job_max_attempts,
                    normalized_key,
                )
                session.commit()
            except IntegrityError:
                session.rollback()
                if not normalized_key:
                    raise
                existing = repository.find_by_idempotency_key(job_type, normalized_key)
                if existing is None:
                    raise
                return job_to_accepted(existing, self.settings.api_v1_prefix)
            accepted = job_to_accepted(job, self.settings.api_v1_prefix)

        self.queue.enqueue(job.id)
        return accepted

    def get_job(self, job_id: str) -> JobDetailResponse:
        with self.session_factory() as session:
            return job_to_detail(JobRepository(session).get_or_raise(job_id))

    def list_jobs(self, limit: int) -> JobListResponse:
        with self.session_factory() as session:
            jobs = [job_to_detail(job) for job in JobRepository(session).list_recent(limit)]
        return JobListResponse(jobs=jobs, count=len(jobs))

    def cancel_job(self, job_id: str) -> JobCancellationResponse:
        with self.session_factory() as session:
            repository = JobRepository(session)
            job = repository.get_or_raise(job_id)
            if job.status not in {"queued", "retrying", "running"}:
                raise ValidationAppError(f"Job in {job.status} status cannot be cancelled.")
            repository.cancel(job)
            provider_run_repository = ProviderRunRepository(session)
            for provider_run in provider_run_repository.list_running_for_job(job.id):
                provider_run_repository.mark_cancelled(provider_run)
            session.commit()
            return JobCancellationResponse(job_id=job.id, status="cancelled")

    def recover_jobs(self) -> JobRecoveryResponse:
        recovered_stale = recover_stale_jobs(self.session_factory, self.settings)
        due_job_ids = requeue_due_jobs(self.session_factory)
        for job_id in due_job_ids:
            self.queue.enqueue(job_id)
        return JobRecoveryResponse(
            recovered_stale=recovered_stale,
            requeued_due=len(due_job_ids),
        )
