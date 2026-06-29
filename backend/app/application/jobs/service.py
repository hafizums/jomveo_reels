from sqlalchemy.exc import IntegrityError

from backend.app.application.jobs.queue import JobQueue
from backend.app.application.jobs.schemas import (
    JobAcceptedResponse,
    JobDetailResponse,
    JobErrorResponse,
    JobListResponse,
)
from backend.app.core.errors import ValidationAppError
from backend.app.db.models import GenerationJob
from backend.app.db.session import SessionFactory
from backend.app.repositories.jobs import JobRepository
from backend.app.script_generator import ScriptRequest

SCRIPT_JOB_TYPE = "script.generate"


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
        api_prefix: str,
    ) -> None:
        self.session_factory = session_factory
        self.queue = queue
        self.api_prefix = api_prefix

    def create_script_job(
        self,
        payload: ScriptRequest,
        idempotency_key: str | None,
    ) -> JobAcceptedResponse:
        normalized_key = idempotency_key.strip() if idempotency_key else None
        if normalized_key and len(normalized_key) > 255:
            raise ValidationAppError("Idempotency-Key must not exceed 255 characters.")

        with self.session_factory() as session:
            repository = JobRepository(session)
            if normalized_key:
                existing = repository.find_by_idempotency_key(SCRIPT_JOB_TYPE, normalized_key)
                if existing:
                    return job_to_accepted(existing, self.api_prefix)
            try:
                job = repository.create(
                    SCRIPT_JOB_TYPE,
                    payload.model_dump(mode="json"),
                    normalized_key,
                )
                session.commit()
            except IntegrityError:
                session.rollback()
                if not normalized_key:
                    raise
                existing = repository.find_by_idempotency_key(SCRIPT_JOB_TYPE, normalized_key)
                if existing is None:
                    raise
                return job_to_accepted(existing, self.api_prefix)
            accepted = job_to_accepted(job, self.api_prefix)

        self.queue.enqueue(job.id)
        return accepted

    def get_job(self, job_id: str) -> JobDetailResponse:
        with self.session_factory() as session:
            return job_to_detail(JobRepository(session).get_or_raise(job_id))

    def list_jobs(self, limit: int) -> JobListResponse:
        with self.session_factory() as session:
            jobs = [job_to_detail(job) for job in JobRepository(session).list_recent(limit)]
        return JobListResponse(jobs=jobs, count=len(jobs))
