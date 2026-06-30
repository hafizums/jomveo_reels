from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.app.application.assets.schemas import AssetListResponse, AssetResponse
from backend.app.application.assets.service import AssetService
from backend.app.application.projects.permissions import require_project_role
from backend.app.auth.dependencies import require_principal
from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.core.errors import AuthForbiddenError
from backend.app.repositories.assets import AssetRepository
from backend.app.repositories.projects import ProjectRepository

router = APIRouter()
Principal = Annotated[AuthenticatedPrincipal, Depends(require_principal)]


def authorize_project(session, project_id: str, principal: AuthenticatedPrincipal):
    projects = ProjectRepository(session)
    projects.get_or_raise(project_id)
    require_project_role(principal, projects.membership(project_id, principal.user_id), "viewer")


@router.get("/projects/{project_id}/assets", response_model=AssetListResponse)
def project_assets(project_id: str, request: Request, principal: Principal):
    with request.app.state.session_factory() as session:
        authorize_project(session, project_id, principal)
        return AssetService(session, request.app.state.settings).list_response(
            AssetRepository(session).for_project(project_id)
        )


@router.get("/projects/{project_id}/assets/{asset_id}", response_model=AssetResponse)
def project_asset(project_id: str, asset_id: str, request: Request, principal: Principal):
    with request.app.state.session_factory() as session:
        authorize_project(session, project_id, principal)
        asset = AssetRepository(session).get(asset_id)
        if asset is None or asset.project_id != project_id:
            raise AuthForbiddenError("Asset is not accessible.")
        return AssetService(session, request.app.state.settings).response(asset)


@router.get("/jobs/{job_id}/assets", response_model=AssetListResponse)
def job_assets(job_id: str, request: Request, principal: Principal):
    request.app.state.job_service.get_job(job_id, principal)
    with request.app.state.session_factory() as session:
        return AssetService(session, request.app.state.settings).list_response(
            AssetRepository(session).for_job(job_id)
        )
