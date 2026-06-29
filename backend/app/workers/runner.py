import logging
from datetime import timedelta
from typing import Any

from fastapi import HTTPException

from backend.app.application.jobs.registry import get_job_definition
from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import AppError
from backend.app.db.models import utc_now
from backend.app.db.session import (
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from backend.app.infrastructure.providers.observability import (
    safe_provider_request_summary,
    safe_provider_response_summary,
)
from backend.app.infrastructure.providers.wavespeed import create_wavespeed_provider_client
from backend.app.repositories.jobs import JobRepository
from backend.app.repositories.provider_runs import ProviderRunRepository

logger = logging.getLogger(__name__)
RETRYABLE_ERROR_CODES = {
    "provider_error",
    "provider_timeout_error",
    "provider_bad_response_error",
    "internal_server_error",
}


def _initial_progress_total(job_type: str, input_json: dict[str, Any]) -> int:
    if job_type == "scene_animation.generate":
        scenes = input_json.get("scenes")
        return len(scenes) if isinstance(scenes, list) and scenes else 1
    if job_type == "video.generate":
        return 5
    return 1


def _record_failure(
    session_factory: SessionFactory,
    settings: Settings,
    job_id: str,
    provider_run_id: str | None,
    code: str,
    message: str,
) -> None:
    with session_factory() as session:
        job_repository = JobRepository(session)
        job = job_repository.get(job_id)
        if job is not None and job.status != "cancelled":
            if code in RETRYABLE_ERROR_CODES and job.attempt_count < job.max_attempts:
                next_retry_at = utc_now() + timedelta(seconds=settings.job_retry_backoff_seconds)
                job_repository.mark_retrying(job, code, message, next_retry_at)
            else:
                job_repository.mark_failed(job, code, message)
        if provider_run_id:
            provider_run_repository = ProviderRunRepository(session)
            provider_run = provider_run_repository.get(provider_run_id)
            if provider_run is not None:
                provider_run_repository.mark_failed(provider_run, code, message)
        session.commit()


def _http_error(exc: HTTPException) -> tuple[str, str]:
    message = exc.detail if isinstance(exc.detail, str) else "Job provider request failed."
    message_lower = message.casefold()
    if exc.status_code < 500:
        return "validation_error", message
    if exc.status_code == 504:
        return "provider_timeout_error", message
    if "401" in message_lower or "unauthorized" in message_lower:
        return "provider_auth_error", message
    if "403" in message_lower or "forbidden" in message_lower or "denied" in message_lower:
        return "provider_forbidden_error", message
    return "provider_error", message


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
            job = job_repository.claim_for_execution(job_id, settings.job_worker_id)
            if job is None:
                existing = job_repository.get(job_id)
                if existing is None:
                    logger.warning("job_not_found", extra={"job_id": job_id})
                    return
                logger.info(
                    "job_execution_skipped",
                    extra={"job_id": job_id, "job_status": existing.status},
                )
                return

            definition = get_job_definition(job.type)
            progress_total = _initial_progress_total(job.type, job.input_json)
            job_repository.set_progress_total(job, progress_total)
            if definition.provider == "wavespeed":
                metadata_client = create_wavespeed_provider_client(settings)
                provider_mode = metadata_client.provider_mode
                sdk_version = metadata_client.sdk_version()
            else:
                provider_mode = "local"
                sdk_version = None
            model = str(job.input_json.get("model") or "") or None
            provider_run = ProviderRunRepository(session).create(
                job_id=job.id,
                provider=definition.provider,
                model=model,
                provider_mode=provider_mode,
                sdk_version=sdk_version,
                request_summary=safe_provider_request_summary(
                    job.type,
                    model,
                    provider_mode,
                ),
            )
            provider_run_id = provider_run.id
            input_json = dict(job.input_json)
            session.commit()

        result = definition.handler(input_json, settings)

        with session_factory() as session:
            job_repository = JobRepository(session)
            job = job_repository.get_or_raise(job_id)
            provider_run_repository = ProviderRunRepository(session)
            provider_run = provider_run_repository.get(provider_run_id)
            if job.status == "cancelled":
                if provider_run is not None:
                    provider_run_repository.mark_cancelled(provider_run)
                session.commit()
                return
            if job.type == "scene_sequence.generate":
                scene_count = result.get("scene_count")
                if isinstance(scene_count, int) and scene_count > 0:
                    job_repository.set_progress_total(job, scene_count + 1)
            job_repository.mark_completed(job, result)
            if provider_run is not None:
                provider_run_repository.mark_completed(
                    provider_run,
                    safe_provider_response_summary(result),
                )
            session.commit()
    except AppError as exc:
        _record_failure(session_factory, settings, job_id, provider_run_id, exc.code, exc.message)
    except HTTPException as exc:
        code, message = _http_error(exc)
        _record_failure(session_factory, settings, job_id, provider_run_id, code, message)
    except Exception:
        logger.exception("job_execution_failed", extra={"job_id": job_id})
        _record_failure(
            session_factory,
            settings,
            job_id,
            provider_run_id,
            "internal_server_error",
            "Job execution failed unexpectedly.",
        )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()
