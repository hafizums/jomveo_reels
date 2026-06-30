from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from backend.app.application.billing.pricing import estimate_job_cost
from backend.app.application.billing.service import BillingService
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
from backend.app.application.projects.permissions import require_project_role
from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.core.config import Settings
from backend.app.core.errors import (
    AuthForbiddenError,
    BillingInsufficientCreditsError,
    QuotaExceededError,
    ValidationAppError,
)
from backend.app.db.models import GenerationJob
from backend.app.db.session import SessionFactory
from backend.app.repositories.audit_logs import AuditLogRepository
from backend.app.repositories.jobs import JobRepository
from backend.app.repositories.projects import ProjectRepository
from backend.app.repositories.provider_runs import ProviderRunRepository
from backend.app.repositories.users import UserRepository


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
        input_payload=job.input_json,
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
        principal: AuthenticatedPrincipal,
        project_id: str | None = None,
    ) -> JobAcceptedResponse:
        normalized_key = idempotency_key.strip() if idempotency_key else None
        if normalized_key and len(normalized_key) > 255:
            raise ValidationAppError("Idempotency-Key must not exceed 255 characters.")

        with self.session_factory() as session:
            repository = JobRepository(session)
            resolved_project_id = project_id
            if resolved_project_id is not None:
                projects = ProjectRepository(session)
                projects.get_or_raise(resolved_project_id)
                require_project_role(
                    principal,
                    projects.membership(resolved_project_id, principal.user_id),
                    "editor",
                )
            elif (
                self.settings.demo_user_enabled
                and principal.email == self.settings.demo_user_email.casefold()
            ):
                _user, demo_project = UserRepository(session).ensure_demo(
                    self.settings.demo_user_email
                )
                resolved_project_id = demo_project.id
            if normalized_key:
                existing = repository.find_by_idempotency_key(job_type, normalized_key)
                if existing:
                    self._require_job_access(session, existing, principal)
                    return job_to_accepted(existing, self.settings.api_v1_prefix)
            input_json = payload.model_dump(mode="json")
            estimate = estimate_job_cost(job_type, input_json, self.settings)
            billing = BillingService(session, self.settings)
            if resolved_project_id is not None:
                try:
                    billing.check_quotas(resolved_project_id, estimate.estimated_credits)
                except QuotaExceededError:
                    session.rollback()
                    self._audit_billing_rejection(
                        principal,
                        resolved_project_id,
                        "job_quota_rejected",
                        estimate.estimated_credits,
                    )
                    raise
            try:
                job = repository.create(
                    job_type,
                    input_json,
                    self.settings.job_max_attempts,
                    normalized_key,
                    resolved_project_id,
                    principal.user_id,
                )
                billing_required = (
                    self.settings.billing_enabled
                    and resolved_project_id is not None
                    and not (
                        principal.email == self.settings.demo_user_email.casefold()
                        and not self.settings.demo_billing_enabled
                    )
                )
                if billing_required:
                    billing.reserve(job, estimate, principal)
                else:
                    job.estimated_credits = estimate.estimated_credits
                    job.reserved_credits = 0
                    job.billing_status = "not_required"
                AuditLogRepository(session).record(
                    principal,
                    "job_created",
                    "generation_job",
                    job.id,
                    resolved_project_id,
                    {"job_type": job_type},
                )
                session.commit()
            except BillingInsufficientCreditsError:
                session.rollback()
                self._audit_billing_rejection(
                    principal,
                    resolved_project_id,
                    "job_credit_rejected",
                    estimate.estimated_credits,
                )
                raise
            except IntegrityError:
                session.rollback()
                if not normalized_key:
                    raise
                existing = repository.find_by_idempotency_key(job_type, normalized_key)
                if existing is None:
                    raise
                self._require_job_access(session, existing, principal)
                return job_to_accepted(existing, self.settings.api_v1_prefix)
            accepted = job_to_accepted(job, self.settings.api_v1_prefix)

        self.queue.enqueue(job.id)
        return accepted

    def get_job(self, job_id: str, principal: AuthenticatedPrincipal) -> JobDetailResponse:
        with self.session_factory() as session:
            job = JobRepository(session).get_or_raise(job_id)
            self._require_job_access(session, job, principal)
            return job_to_detail(job)

    def list_jobs(self, limit: int, principal: AuthenticatedPrincipal) -> JobListResponse:
        with self.session_factory() as session:
            repository = JobRepository(session)
            if principal.role == "admin":
                records = repository.list_recent(limit)
            else:
                records = repository.list_for_user(
                    principal.user_id or "",
                    limit,
                    include_unowned=(
                        self.settings.demo_user_enabled
                        and principal.email == self.settings.demo_user_email.casefold()
                    ),
                )
            jobs = [job_to_detail(job) for job in records]
        return JobListResponse(jobs=jobs, count=len(jobs))

    def cancel_job(self, job_id: str, principal: AuthenticatedPrincipal) -> JobCancellationResponse:
        with self.session_factory() as session:
            repository = JobRepository(session)
            job = repository.get_or_raise(job_id)
            if job.status not in {"queued", "retrying", "running"}:
                raise ValidationAppError(f"Job in {job.status} status cannot be cancelled.")
            repository.cancel(job)
            provider_run_repository = ProviderRunRepository(session)
            for provider_run in provider_run_repository.list_running_for_job(job.id):
                provider_run_repository.mark_cancelled(provider_run)
            BillingService(session, self.settings).release(job)
            AuditLogRepository(session).record(
                principal, "job_cancelled", "generation_job", job.id, job.project_id
            )
            session.commit()
            return JobCancellationResponse(job_id=job.id, status="cancelled")

    def recover_jobs(self, principal: AuthenticatedPrincipal) -> JobRecoveryResponse:
        recovered_stale = recover_stale_jobs(self.session_factory, self.settings)
        due_job_ids = requeue_due_jobs(self.session_factory)
        for job_id in due_job_ids:
            self.queue.enqueue(job_id)
        with self.session_factory() as session:
            AuditLogRepository(session).record(
                principal,
                "job_recovered_stale",
                "generation_job",
                metadata={"count": recovered_stale + len(due_job_ids)},
            )
            session.commit()
        return JobRecoveryResponse(
            recovered_stale=recovered_stale,
            requeued_due=len(due_job_ids),
        )

    def _require_job_access(
        self,
        session,
        job: GenerationJob,
        principal: AuthenticatedPrincipal,
    ) -> None:
        if principal.role == "admin" or job.created_by_user_id == principal.user_id:
            return
        if job.project_id is not None:
            membership = ProjectRepository(session).membership(job.project_id, principal.user_id)
            require_project_role(principal, membership, "viewer")
            return
        if (
            self.settings.demo_user_enabled
            and principal.email == self.settings.demo_user_email.casefold()
        ):
            return
        raise AuthForbiddenError("You do not have permission to access this job.")

    def _audit_billing_rejection(
        self,
        principal: AuthenticatedPrincipal,
        project_id: str | None,
        action: str,
        estimated_credits: int,
    ) -> None:
        with self.session_factory() as audit_session:
            AuditLogRepository(audit_session).record(
                principal,
                action,
                "generation_job",
                project_id=project_id,
                metadata={"estimated_credits": estimated_credits},
            )
            audit_session.commit()
