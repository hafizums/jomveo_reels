from fastapi import Request

from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.auth.security import credential_from_request, is_valid_admin_key
from backend.app.core.errors import AuthForbiddenError, AuthRequiredError
from backend.app.repositories.api_keys import APIKeyRepository
from backend.app.repositories.audit_logs import AuditLogRepository
from backend.app.repositories.users import UserRepository

DEV_ADMIN_PRINCIPAL = AuthenticatedPrincipal(subject="development-admin")
ADMIN_PRINCIPAL = AuthenticatedPrincipal(subject="admin-api-key")


def _audit_auth(request: Request, principal: AuthenticatedPrincipal, action: str) -> None:
    with request.app.state.session_factory() as session:
        AuditLogRepository(session).record(principal, action, "api_key")
        session.commit()


def _authenticate_credential(request: Request) -> AuthenticatedPrincipal | None:
    credential = credential_from_request(request)
    if credential is None:
        return None
    token, source = credential
    settings = request.app.state.settings
    if source != "user" and is_valid_admin_key(token, settings.admin_api_keys):
        _audit_auth(request, ADMIN_PRINCIPAL, "api_key_authenticated")
        return ADMIN_PRINCIPAL

    if settings.user_auth_enabled and source != "admin":
        with request.app.state.session_factory() as session:
            authenticated = APIKeyRepository(session).authenticate(token)
            if authenticated is not None:
                record, user = authenticated
                principal = AuthenticatedPrincipal(
                    subject=f"api-key:{record.id}",
                    role=record.role,  # type: ignore[arg-type]
                    user_id=user.id if user else None,
                    email=user.email if user else None,
                )
                AuditLogRepository(session).record(
                    principal, "api_key_authenticated", "api_key", record.id
                )
                session.commit()
                return principal

    rejected = AuthenticatedPrincipal(subject="anonymous", role="user")
    _audit_auth(request, rejected, "api_key_rejected")
    raise AuthForbiddenError("Authentication failed.")


def _demo_principal(request: Request) -> AuthenticatedPrincipal | None:
    settings = request.app.state.settings
    if not settings.demo_user_enabled:
        return None
    with request.app.state.session_factory() as session:
        user, _project = UserRepository(session).ensure_demo(settings.demo_user_email)
        session.commit()
        return AuthenticatedPrincipal(
            subject=f"user:{user.id}", role="user", user_id=user.id, email=user.email
        )


def optional_admin(request: Request) -> AuthenticatedPrincipal | None:
    settings = request.app.state.settings
    if not settings.admin_auth_enabled:
        return DEV_ADMIN_PRINCIPAL

    principal = _authenticate_credential(request)
    if principal is None:
        return None
    if principal.role != "admin":
        raise AuthForbiddenError("Admin authentication failed.")
    return principal


def require_admin(request: Request) -> AuthenticatedPrincipal:
    principal = optional_admin(request)
    if principal is None:
        raise AuthRequiredError("Admin authentication is required.")
    return principal


def optional_principal(request: Request) -> AuthenticatedPrincipal | None:
    principal = _authenticate_credential(request)
    return principal or _demo_principal(request)


def require_principal(request: Request) -> AuthenticatedPrincipal:
    principal = optional_principal(request)
    if principal is None:
        raise AuthRequiredError("Authentication is required.")
    return principal
