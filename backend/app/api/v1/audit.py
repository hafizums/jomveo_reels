from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from backend.app.auth.dependencies import require_admin
from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.repositories.audit_logs import AuditLogRepository

router = APIRouter()
AdminPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_admin)]


@router.get("")
def list_audit_logs(
    request: Request,
    _principal: AdminPrincipal,
    project_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> dict[str, Any]:
    with request.app.state.session_factory() as session:
        entries = AuditLogRepository(session).list_recent(project_id, limit)
        logs = [
            {
                "id": entry.id,
                "actor_user_id": entry.actor_user_id,
                "actor_subject": entry.actor_subject,
                "actor_role": entry.actor_role,
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "project_id": entry.project_id,
                "metadata": entry.metadata_json,
                "created_at": entry.created_at,
            }
            for entry in entries
        ]
        return {"logs": logs, "count": len(logs)}
