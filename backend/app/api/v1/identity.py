from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.application.projects.schemas import MeResponse
from backend.app.auth.dependencies import require_principal
from backend.app.auth.models import AuthenticatedPrincipal

router = APIRouter()
Principal = Annotated[AuthenticatedPrincipal, Depends(require_principal)]


@router.get("/me", response_model=MeResponse)
def me(principal: Principal) -> MeResponse:
    return MeResponse(**principal.model_dump())
