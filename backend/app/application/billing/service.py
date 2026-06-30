from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.application.billing.pricing import CostEstimate
from backend.app.application.billing.schemas import BillingAccountResponse, QuotaResponse
from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.core.config import Settings
from backend.app.core.errors import BillingInsufficientCreditsError, QuotaExceededError
from backend.app.db.models import (
    CreditAccount,
    CreditTransaction,
    GenerationJob,
    JobCostEstimate,
    ProjectQuota,
    ProviderCostRecord,
    ProviderRun,
    utc_now,
)
from backend.app.repositories.audit_logs import AuditLogRepository


class BillingService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def ensure_project(self, project_id: str) -> tuple[CreditAccount, ProjectQuota]:
        account = self.session.scalar(
            select(CreditAccount).where(CreditAccount.project_id == project_id).with_for_update()
        )
        if account is None:
            account = CreditAccount(project_id=project_id)
            self.session.add(account)
            self.session.flush()
            if self.settings.default_project_starting_credits > 0:
                self.top_up(
                    account,
                    self.settings.default_project_starting_credits,
                    None,
                    "Starting credits",
                )
        quota = self.session.scalar(
            select(ProjectQuota).where(ProjectQuota.project_id == project_id)
        )
        if quota is None:
            quota = ProjectQuota(
                project_id=project_id,
                daily_job_limit=self.settings.default_daily_job_limit,
                monthly_job_limit=self.settings.default_monthly_job_limit,
                daily_credit_limit=self.settings.default_daily_credit_limit,
                monthly_credit_limit=self.settings.default_monthly_credit_limit,
                max_concurrent_jobs=self.settings.default_max_concurrent_jobs,
            )
            self.session.add(quota)
            self.session.flush()
        return account, quota

    def account_response(self, account: CreditAccount) -> BillingAccountResponse:
        return BillingAccountResponse(
            project_id=account.project_id,
            currency=account.currency,
            balance_credits=account.balance_credits,
            reserved_credits=account.reserved_credits,
            available_credits=account.balance_credits - account.reserved_credits,
            lifetime_purchased_credits=account.lifetime_purchased_credits,
            lifetime_used_credits=account.lifetime_used_credits,
        )

    def quota_response(self, quota: ProjectQuota) -> QuotaResponse:
        return QuotaResponse(**{key: getattr(quota, key) for key in QuotaResponse.model_fields})

    def top_up(
        self, account: CreditAccount, amount: int, user_id: str | None, description: str | None
    ) -> None:
        account.balance_credits += amount
        account.lifetime_purchased_credits += amount
        account.updated_at = utc_now()
        self._transaction(account, "top_up", amount, None, user_id, description)

    def check_quotas(self, project_id: str, estimate: int) -> None:
        _account, quota = self.ensure_project(project_id)
        now = datetime.now(UTC)
        day = now - timedelta(days=1)
        month = now - timedelta(days=30)
        daily_jobs = self._job_count(project_id, day)
        monthly_jobs = self._job_count(project_id, month)
        concurrent = (
            self.session.scalar(
                select(func.count())
                .select_from(GenerationJob)
                .where(
                    GenerationJob.project_id == project_id,
                    GenerationJob.status.in_(("queued", "running", "retrying")),
                )
            )
            or 0
        )
        daily_credits = self._credit_usage(project_id, day)
        monthly_credits = self._credit_usage(project_id, month)
        exceeded = (
            (quota.daily_job_limit is not None and daily_jobs >= quota.daily_job_limit)
            or (quota.monthly_job_limit is not None and monthly_jobs >= quota.monthly_job_limit)
            or (quota.max_concurrent_jobs is not None and concurrent >= quota.max_concurrent_jobs)
            or (
                quota.daily_credit_limit is not None
                and daily_credits + estimate > quota.daily_credit_limit
            )
            or (
                quota.monthly_credit_limit is not None
                and monthly_credits + estimate > quota.monthly_credit_limit
            )
        )
        if exceeded:
            raise QuotaExceededError("Project job quota has been exceeded.")

    def reserve(
        self, job: GenerationJob, estimate: CostEstimate, principal: AuthenticatedPrincipal
    ) -> None:
        account, _quota = self.ensure_project(job.project_id or "")
        if account.balance_credits - account.reserved_credits < estimate.estimated_credits:
            raise BillingInsufficientCreditsError("Project has insufficient credits.")
        account.reserved_credits += estimate.estimated_credits
        job.estimated_credits = estimate.estimated_credits
        job.reserved_credits = estimate.estimated_credits
        job.billing_status = "reserved"
        self.session.add(
            JobCostEstimate(
                job_id=job.id,
                project_id=job.project_id,
                estimated_credits=estimate.estimated_credits,
                reserved_credits=estimate.estimated_credits,
                pricing_version=estimate.pricing_version,
                estimate_json=estimate.details,
            )
        )
        self._transaction(
            account,
            "reserve",
            estimate.estimated_credits,
            job.id,
            principal.user_id,
            "Job credit reservation",
        )
        AuditLogRepository(self.session).record(
            principal,
            "billing_reserved",
            "generation_job",
            job.id,
            job.project_id,
            {
                "estimated_credits": estimate.estimated_credits,
                "reserved_credits": estimate.estimated_credits,
            },
        )

    def consume(self, job: GenerationJob, provider_run: ProviderRun | None = None) -> None:
        if job.billing_status != "reserved" or not job.project_id:
            return
        account, _quota = self.ensure_project(job.project_id)
        amount = job.reserved_credits or 0
        account.reserved_credits = max(0, account.reserved_credits - amount)
        account.balance_credits -= amount
        account.lifetime_used_credits += amount
        job.billing_status = "consumed"
        self._transaction(
            account, "consume_reserved", amount, job.id, job.created_by_user_id, "Completed job"
        )
        self.session.add(
            ProviderCostRecord(
                provider_run_id=provider_run.id if provider_run else None,
                job_id=job.id,
                project_id=job.project_id,
                provider=provider_run.provider if provider_run else "local_media",
                model=provider_run.model if provider_run else None,
                estimated_credits=amount,
                actual_credits=amount,
                pricing_version=self.settings.pricing_version,
            )
        )
        principal = AuthenticatedPrincipal(
            subject=f"user:{job.created_by_user_id}" if job.created_by_user_id else "system",
            role="user",
            user_id=job.created_by_user_id,
        )
        AuditLogRepository(self.session).record(
            principal,
            "billing_consumed",
            "generation_job",
            job.id,
            job.project_id,
            {"amount_credits": amount, "billing_status": "consumed"},
        )

    def release(self, job: GenerationJob) -> None:
        if job.billing_status != "reserved" or not job.project_id:
            return
        account, _quota = self.ensure_project(job.project_id)
        amount = job.reserved_credits or 0
        account.reserved_credits = max(0, account.reserved_credits - amount)
        job.billing_status = "released"
        self._transaction(
            account,
            "release_reserved",
            amount,
            job.id,
            job.created_by_user_id,
            "Job reservation released",
        )
        principal = AuthenticatedPrincipal(
            subject=f"user:{job.created_by_user_id}" if job.created_by_user_id else "system",
            role="user",
            user_id=job.created_by_user_id,
        )
        AuditLogRepository(self.session).record(
            principal,
            "billing_released",
            "generation_job",
            job.id,
            job.project_id,
            {"amount_credits": amount, "billing_status": "released"},
        )

    def _transaction(
        self,
        account: CreditAccount,
        transaction_type: str,
        amount: int,
        job_id: str | None,
        user_id: str | None,
        description: str | None,
    ) -> None:
        self.session.add(
            CreditTransaction(
                account_id=account.id,
                project_id=account.project_id,
                job_id=job_id,
                type=transaction_type,
                amount_credits=amount,
                balance_after_credits=account.balance_credits,
                reserved_after_credits=account.reserved_credits,
                description=description,
                created_by_user_id=user_id,
            )
        )

    def _job_count(self, project_id: str, since: datetime) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(GenerationJob)
                .where(GenerationJob.project_id == project_id, GenerationJob.created_at >= since)
            )
            or 0
        )

    def _credit_usage(self, project_id: str, since: datetime) -> int:
        return (
            self.session.scalar(
                select(func.coalesce(func.sum(CreditTransaction.amount_credits), 0)).where(
                    CreditTransaction.project_id == project_id,
                    CreditTransaction.type == "consume_reserved",
                    CreditTransaction.created_at >= since,
                )
            )
            or 0
        )
