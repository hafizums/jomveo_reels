from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import ProviderRun, utc_now
from backend.app.infrastructure.providers.observability import duration_ms


class ProviderRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        job_id: str,
        provider: str,
        model: str | None,
        provider_mode: str,
        sdk_version: str | None,
        request_summary: dict[str, Any] | None = None,
    ) -> ProviderRun:
        provider_run = ProviderRun(
            job_id=job_id,
            provider=provider,
            model=model,
            status="running",
            request_summary_json=request_summary,
            started_at=utc_now(),
            provider_mode=provider_mode,
            sdk_version=sdk_version,
        )
        self.session.add(provider_run)
        self.session.flush()
        return provider_run

    def get(self, provider_run_id: str) -> ProviderRun | None:
        return self.session.get(ProviderRun, provider_run_id)

    def list_running_for_job(self, job_id: str) -> list[ProviderRun]:
        statement = select(ProviderRun).where(
            ProviderRun.job_id == job_id,
            ProviderRun.status == "running",
        )
        return list(self.session.scalars(statement))

    def mark_completed(
        self,
        provider_run: ProviderRun,
        response_summary: dict[str, Any] | None = None,
    ) -> None:
        completed_at = utc_now()
        provider_run.status = "completed"
        provider_run.response_summary_json = response_summary
        provider_run.completed_at = completed_at
        if provider_run.started_at is not None:
            provider_run.duration_ms = duration_ms(provider_run.started_at, completed_at)
        provider_run.updated_at = completed_at

    def mark_failed(self, provider_run: ProviderRun, code: str, message: str) -> None:
        completed_at = utc_now()
        provider_run.status = "failed"
        provider_run.error_code = code
        provider_run.error_message = message
        provider_run.completed_at = completed_at
        if provider_run.started_at is not None:
            provider_run.duration_ms = duration_ms(provider_run.started_at, completed_at)
        provider_run.updated_at = completed_at

    def mark_cancelled(self, provider_run: ProviderRun) -> None:
        completed_at = utc_now()
        provider_run.status = "cancelled"
        provider_run.completed_at = completed_at
        if provider_run.started_at is not None:
            provider_run.duration_ms = duration_ms(provider_run.started_at, completed_at)
        provider_run.updated_at = completed_at
