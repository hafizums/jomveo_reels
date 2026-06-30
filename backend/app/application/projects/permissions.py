from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.core.errors import AuthForbiddenError
from backend.app.db.models import ProjectMember

ROLE_LEVEL = {"viewer": 1, "editor": 2, "admin": 3, "owner": 4}


def require_project_role(
    principal: AuthenticatedPrincipal,
    membership: ProjectMember | None,
    minimum_role: str,
) -> None:
    if principal.role == "admin":
        return
    if membership is None or ROLE_LEVEL.get(membership.role, 0) < ROLE_LEVEL[minimum_role]:
        raise AuthForbiddenError("You do not have permission to access this project.")
