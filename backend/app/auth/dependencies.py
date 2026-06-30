from fastapi import Request

from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.auth.security import admin_token_from_request, is_valid_admin_key
from backend.app.core.errors import AuthForbiddenError, AuthRequiredError

DEV_ADMIN_PRINCIPAL = AuthenticatedPrincipal(subject="development-admin")
ADMIN_PRINCIPAL = AuthenticatedPrincipal(subject="admin-api-key")


def optional_admin(request: Request) -> AuthenticatedPrincipal | None:
    settings = request.app.state.settings
    if not settings.admin_auth_enabled:
        return DEV_ADMIN_PRINCIPAL

    token = admin_token_from_request(request)
    if token is None:
        return None
    if not is_valid_admin_key(token, settings.admin_api_keys):
        raise AuthForbiddenError("Admin authentication failed.")
    return ADMIN_PRINCIPAL


def require_admin(request: Request) -> AuthenticatedPrincipal:
    principal = optional_admin(request)
    if principal is None:
        raise AuthRequiredError("Admin authentication is required.")
    return principal
