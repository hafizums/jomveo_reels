from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.db.models import AuditLog

SAFE_METADATA_KEYS = {
    "job_type",
    "member_user_id",
    "member_role",
    "status",
    "count",
    "amount_credits",
    "estimated_credits",
    "reserved_credits",
    "billing_status",
    "quota_key",
    "asset_type",
    "storage_type",
    "expires_at",
}


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        principal: AuthenticatedPrincipal,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        safe_metadata = (
            {key: value for key, value in metadata.items() if key in SAFE_METADATA_KEYS}
            if metadata
            else None
        )
        entry = AuditLog(
            actor_user_id=principal.user_id,
            actor_subject=principal.subject,
            actor_role=principal.role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            metadata_json=safe_metadata,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_recent(self, project_id: str | None = None, limit: int = 100) -> list[AuditLog]:
        statement = select(AuditLog)
        if project_id is not None:
            statement = statement.where(AuditLog.project_id == project_id)
        return list(
            self.session.scalars(statement.order_by(AuditLog.created_at.desc()).limit(limit))
        )
