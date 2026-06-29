from datetime import timedelta

from backend.app.core.config import Settings
from backend.app.db.models import utc_now
from backend.app.db.session import SessionFactory
from backend.app.repositories.jobs import JobRepository
from backend.app.repositories.provider_runs import ProviderRunRepository


def recover_stale_jobs(session_factory: SessionFactory, settings: Settings) -> int:
    now = utc_now()
    cutoff = now - timedelta(seconds=settings.job_stale_after_seconds)
    with session_factory() as session:
        repository = JobRepository(session)
        provider_run_repository = ProviderRunRepository(session)
        jobs = repository.find_stale_running(cutoff)
        for job in jobs:
            message = "Job execution became stale and was queued for recovery."
            if job.attempt_count < job.max_attempts:
                repository.mark_retrying(
                    job,
                    "internal_server_error",
                    message,
                    now,
                )
            else:
                message = "Job execution became stale after all attempts were exhausted."
                repository.mark_failed(
                    job,
                    "internal_server_error",
                    message,
                )
            for provider_run in provider_run_repository.list_running_for_job(job.id):
                provider_run_repository.mark_failed(
                    provider_run,
                    "internal_server_error",
                    message,
                )
        session.commit()
        return len(jobs)


def requeue_due_jobs(session_factory: SessionFactory) -> list[str]:
    now = utc_now()
    with session_factory() as session:
        repository = JobRepository(session)
        jobs = repository.find_due_retries(now)
        job_ids = [job.id for job in jobs]
        for job in jobs:
            repository.mark_queued(job)
        session.commit()
        return job_ids
