from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import ProviderRun, utc_now


class ProviderRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        job_id: str,
        provider: str,
        model: str | None,
        request_summary: dict[str, Any] | None = None,
    ) -> ProviderRun:
        provider_run = ProviderRun(
            job_id=job_id,
            provider=provider,
            model=model,
            status="running",
            request_summary_json=request_summary,
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
        provider_run.status = "completed"
        provider_run.response_summary_json = response_summary
        provider_run.updated_at = utc_now()

    def mark_failed(self, provider_run: ProviderRun, code: str, message: str) -> None:
        provider_run.status = "failed"
        provider_run.error_code = code
        provider_run.error_message = message
        provider_run.updated_at = utc_now()

    def mark_cancelled(self, provider_run: ProviderRun) -> None:
        provider_run.status = "cancelled"
        provider_run.updated_at = utc_now()
