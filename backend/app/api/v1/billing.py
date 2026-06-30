from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from backend.app.application.billing.schemas import (
    BillingAccountResponse,
    CreditTransactionResponse,
    QuotaResponse,
    QuotaUpdateRequest,
    ReconciliationResponse,
    TopUpRequest,
    TransactionListResponse,
    UsageResponse,
)
from backend.app.application.billing.service import BillingService
from backend.app.application.projects.permissions import require_project_role
from backend.app.auth.dependencies import require_admin, require_principal
from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.db.models import CreditTransaction, GenerationJob, utc_now
from backend.app.repositories.audit_logs import AuditLogRepository
from backend.app.repositories.projects import ProjectRepository

router = APIRouter()
Principal = Annotated[AuthenticatedPrincipal, Depends(require_principal)]
AdminPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_admin)]


def _authorize(session, project_id: str, principal: AuthenticatedPrincipal) -> None:
    projects = ProjectRepository(session)
    projects.get_or_raise(project_id)
    require_project_role(principal, projects.membership(project_id, principal.user_id), "viewer")


@router.get("/{project_id}/billing", response_model=BillingAccountResponse)
def get_billing(project_id: str, request: Request, principal: Principal) -> BillingAccountResponse:
    with request.app.state.session_factory() as session:
        _authorize(session, project_id, principal)
        service = BillingService(session, request.app.state.settings)
        account, _quota = service.ensure_project(project_id)
        session.commit()
        return service.account_response(account)


@router.get("/{project_id}/billing/transactions", response_model=TransactionListResponse)
def transactions(
    project_id: str, request: Request, principal: Principal
) -> TransactionListResponse:
    with request.app.state.session_factory() as session:
        _authorize(session, project_id, principal)
        records = list(
            session.scalars(
                select(CreditTransaction)
                .where(CreditTransaction.project_id == project_id)
                .order_by(CreditTransaction.created_at.desc())
                .limit(200)
            )
        )
        values = [
            CreditTransactionResponse(
                id=item.id,
                type=item.type,
                amount_credits=item.amount_credits,
                balance_after_credits=item.balance_after_credits,
                reserved_after_credits=item.reserved_after_credits,
                description=item.description,
                created_at=item.created_at,
            )
            for item in records
        ]
        return TransactionListResponse(transactions=values, count=len(values))


@router.get("/{project_id}/billing/usage", response_model=UsageResponse)
def usage(project_id: str, request: Request, principal: Principal) -> UsageResponse:
    with request.app.state.session_factory() as session:
        _authorize(session, project_id, principal)
        now = datetime.now(UTC)

        def job_count(since):
            return (
                session.scalar(
                    select(func.count())
                    .select_from(GenerationJob)
                    .where(
                        GenerationJob.project_id == project_id, GenerationJob.created_at >= since
                    )
                )
                or 0
            )

        def credits(since):
            return (
                session.scalar(
                    select(func.coalesce(func.sum(CreditTransaction.amount_credits), 0)).where(
                        CreditTransaction.project_id == project_id,
                        CreditTransaction.type == "consume_reserved",
                        CreditTransaction.created_at >= since,
                    )
                )
                or 0
            )

        return UsageResponse(
            project_id=project_id,
            daily_jobs=job_count(now - timedelta(days=1)),
            monthly_jobs=job_count(now - timedelta(days=30)),
            daily_credits=credits(now - timedelta(days=1)),
            monthly_credits=credits(now - timedelta(days=30)),
        )


@router.get("/{project_id}/quotas", response_model=QuotaResponse)
def quotas(project_id: str, request: Request, principal: Principal) -> QuotaResponse:
    with request.app.state.session_factory() as session:
        _authorize(session, project_id, principal)
        service = BillingService(session, request.app.state.settings)
        _account, quota = service.ensure_project(project_id)
        session.commit()
        return service.quota_response(quota)


@router.post("/{project_id}/billing/top-up", response_model=BillingAccountResponse)
def top_up(
    project_id: str, payload: TopUpRequest, request: Request, principal: AdminPrincipal
) -> BillingAccountResponse:
    with request.app.state.session_factory() as session:
        ProjectRepository(session).get_or_raise(project_id)
        service = BillingService(session, request.app.state.settings)
        account, _quota = service.ensure_project(project_id)
        service.top_up(account, payload.amount_credits, principal.user_id, payload.description)
        AuditLogRepository(session).record(
            principal,
            "billing_top_up",
            "credit_account",
            account.id,
            project_id,
            {"amount_credits": payload.amount_credits},
        )
        session.commit()
        return service.account_response(account)


@router.patch("/{project_id}/quotas", response_model=QuotaResponse)
def update_quotas(
    project_id: str, payload: QuotaUpdateRequest, request: Request, principal: AdminPrincipal
) -> QuotaResponse:
    with request.app.state.session_factory() as session:
        ProjectRepository(session).get_or_raise(project_id)
        service = BillingService(session, request.app.state.settings)
        _account, quota = service.ensure_project(project_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(quota, key, value)
        quota.updated_at = utc_now()
        AuditLogRepository(session).record(
            principal, "quota_updated", "project_quota", quota.id, project_id
        )
        session.commit()
        return service.quota_response(quota)


@router.post("/{project_id}/billing/reconcile", response_model=ReconciliationResponse)
def reconcile(
    project_id: str, request: Request, principal: AdminPrincipal
) -> ReconciliationResponse:
    with request.app.state.session_factory() as session:
        ProjectRepository(session).get_or_raise(project_id)
        service = BillingService(session, request.app.state.settings)
        account, _quota = service.ensure_project(project_id)
        expected = (
            session.scalar(
                select(func.coalesce(func.sum(GenerationJob.reserved_credits), 0)).where(
                    GenerationJob.project_id == project_id,
                    GenerationJob.billing_status == "reserved",
                )
            )
            or 0
        )
        corrected = account.reserved_credits != expected
        account.reserved_credits = expected
        account.updated_at = utc_now()
        AuditLogRepository(session).record(
            principal,
            "billing_reconciled",
            "credit_account",
            account.id,
            project_id,
            {"reserved_credits": expected},
        )
        session.commit()
        return ReconciliationResponse(
            account=service.account_response(account),
            corrected=corrected,
            metadata={"expected_reserved_credits": expected},
        )
