import logging

from fastapi import HTTPException

from backend.app.application.jobs.registry import get_job_handler
from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import AppError
from backend.app.db.session import (
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from backend.app.repositories.jobs import JobRepository
from backend.app.repositories.provider_runs import ProviderRunRepository

logger = logging.getLogger(__name__)


def _mark_failed(
    session_factory: SessionFactory,
    job_id: str,
    provider_run_id: str | None,
    code: str,
    message: str,
) -> None:
    with session_factory() as session:
        job = JobRepository(session).get(job_id)
        if job is not None:
            JobRepository(session).mark_failed(job, code, message)
        if provider_run_id:
            provider_run_repository = ProviderRunRepository(session)
            provider_run = provider_run_repository.get(provider_run_id)
            if provider_run is not None:
                provider_run_repository.mark_failed(provider_run, code, message)
        session.commit()


def execute_job(
    job_id: str,
    *,
    session_factory: SessionFactory | None = None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    owned_engine = None
    if session_factory is None:
        owned_engine = create_database_engine(settings)
        session_factory = create_session_factory(owned_engine)

    provider_run_id: str | None = None
    try:
        with session_factory() as session:
            job_repository = JobRepository(session)
            job = job_repository.get(job_id)
            if job is None:
                logger.warning("job_not_found", extra={"job_id": job_id})
                return
            if job.status != "queued":
                logger.info(
                    "job_execution_skipped",
                    extra={"job_id": job_id, "job_status": job.status},
                )
                return

            job_repository.mark_running(job)
            provider_run = ProviderRunRepository(session).create(
                job_id=job.id,
                provider="wavespeed",
                model=str(job.input_json.get("model") or "") or None,
                request_summary={"job_type": job.type},
            )
            provider_run_id = provider_run.id
            job_type = job.type
            input_json = dict(job.input_json)
            session.commit()

        handler = get_job_handler(job_type)
        result = handler(input_json, settings)

        with session_factory() as session:
            job_repository = JobRepository(session)
            job = job_repository.get_or_raise(job_id)
            job_repository.mark_completed(job, result)
            provider_run_repository = ProviderRunRepository(session)
            provider_run = provider_run_repository.get(provider_run_id)
            if provider_run is not None:
                provider_run_repository.mark_completed(
                    provider_run,
                    {"result_available": True},
                )
            session.commit()
    except AppError as exc:
        _mark_failed(session_factory, job_id, provider_run_id, exc.code, exc.message)
    except HTTPException as exc:
        message = exc.detail if isinstance(exc.detail, str) else "Job provider request failed."
        code = "provider_error" if exc.status_code >= 500 else "validation_error"
        _mark_failed(session_factory, job_id, provider_run_id, code, message)
    except Exception:
        logger.exception("job_execution_failed", extra={"job_id": job_id})
        _mark_failed(
            session_factory,
            job_id,
            provider_run_id,
            "internal_server_error",
            "Job execution failed unexpectedly.",
        )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()
