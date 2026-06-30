from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from backend.app.application.jobs.schemas import JobListResponse
from backend.app.application.projects.schemas import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemberCreateRequest,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from backend.app.application.projects.service import ProjectService
from backend.app.auth.dependencies import require_principal
from backend.app.auth.models import AuthenticatedPrincipal

router = APIRouter()
Principal = Annotated[AuthenticatedPrincipal, Depends(require_principal)]


def _service(request: Request) -> ProjectService:
    return request.app.state.project_service


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest, request: Request, principal: Principal
) -> ProjectResponse:
    return _service(request).create(principal, payload)


@router.get("", response_model=ProjectListResponse)
def list_projects(request: Request, principal: Principal) -> ProjectListResponse:
    return _service(request).list(principal)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, request: Request, principal: Principal) -> ProjectResponse:
    return _service(request).get(principal, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    request: Request,
    principal: Principal,
) -> ProjectResponse:
    return _service(request).update(principal, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, request: Request, principal: Principal) -> Response:
    _service(request).delete(principal, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
def add_project_member(
    project_id: str,
    payload: ProjectMemberCreateRequest,
    request: Request,
    principal: Principal,
) -> ProjectMemberResponse:
    return _service(request).add_member(principal, project_id, payload)


@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
def list_project_members(
    project_id: str, request: Request, principal: Principal
) -> ProjectMemberListResponse:
    return _service(request).members(principal, project_id)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: str,
    user_id: str,
    request: Request,
    principal: Principal,
) -> Response:
    _service(request).remove_member(principal, project_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/jobs", response_model=JobListResponse)
def list_project_jobs(project_id: str, request: Request, principal: Principal) -> JobListResponse:
    return _service(request).jobs(principal, project_id)
