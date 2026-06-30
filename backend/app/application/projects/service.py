import re
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.application.jobs.schemas import JobListResponse
from backend.app.application.jobs.service import job_to_detail
from backend.app.application.projects.permissions import require_project_role
from backend.app.application.projects.schemas import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemberCreateRequest,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.core.errors import AuthForbiddenError, ValidationAppError
from backend.app.db.models import Project, ProjectMember, User
from backend.app.db.session import SessionFactory
from backend.app.repositories.audit_logs import AuditLogRepository
from backend.app.repositories.jobs import JobRepository
from backend.app.repositories.projects import ProjectRepository


def _project_response(project: Project, role: str | None) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        status=project.status,
        role=role,
        created_by_user_id=project.created_by_user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _member_response(member: ProjectMember) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        role=member.role,  # type: ignore[arg-type]
        created_at=member.created_at,
    )


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized[:120] or f"project-{uuid.uuid4().hex[:8]}"


class ProjectService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    def create(
        self, principal: AuthenticatedPrincipal, payload: ProjectCreateRequest
    ) -> ProjectResponse:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            slug = _slug(payload.slug or payload.name)
            if session.scalar(select(Project).where(Project.slug == slug)) is not None:
                slug = f"{slug[:111]}-{uuid.uuid4().hex[:8]}"
            project = repository.create(
                payload.name.strip(), slug, payload.description, principal.user_id
            )
            role = None
            if principal.user_id is not None:
                repository.add_member(project.id, principal.user_id, "owner")
                role = "owner"
            AuditLogRepository(session).record(
                principal, "project_created", "project", project.id, project.id
            )
            session.commit()
            return _project_response(project, role)

    def list(self, principal: AuthenticatedPrincipal) -> ProjectListResponse:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            projects = (
                repository.list_all()
                if principal.role == "admin"
                else repository.list_for_user(principal.user_id or "")
            )
            responses = []
            for project in projects:
                membership = repository.membership(project.id, principal.user_id)
                role = (
                    "system_admin"
                    if principal.role == "admin"
                    else membership.role
                    if membership
                    else None
                )
                responses.append(_project_response(project, role))
            return ProjectListResponse(projects=responses, count=len(responses))

    def get(self, principal: AuthenticatedPrincipal, project_id: str) -> ProjectResponse:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            project = repository.get_or_raise(project_id)
            membership = repository.membership(project_id, principal.user_id)
            require_project_role(principal, membership, "viewer")
            return _project_response(
                project, "system_admin" if principal.role == "admin" else membership.role
            )

    def update(
        self,
        principal: AuthenticatedPrincipal,
        project_id: str,
        payload: ProjectUpdateRequest,
    ) -> ProjectResponse:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            project = repository.get_or_raise(project_id)
            membership = repository.membership(project_id, principal.user_id)
            require_project_role(principal, membership, "admin")
            repository.update(project, **payload.model_dump(exclude_unset=True))
            AuditLogRepository(session).record(
                principal, "project_updated", "project", project.id, project.id
            )
            session.commit()
            return _project_response(
                project, "system_admin" if principal.role == "admin" else membership.role
            )

    def delete(self, principal: AuthenticatedPrincipal, project_id: str) -> None:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            project = repository.get_or_raise(project_id)
            membership = repository.membership(project_id, principal.user_id)
            require_project_role(principal, membership, "owner")
            project.status = "deleted"
            AuditLogRepository(session).record(
                principal, "project_deleted", "project", project.id, project.id
            )
            session.commit()

    def members(
        self, principal: AuthenticatedPrincipal, project_id: str
    ) -> ProjectMemberListResponse:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            repository.get_or_raise(project_id)
            require_project_role(
                principal, repository.membership(project_id, principal.user_id), "viewer"
            )
            members = [_member_response(member) for member in repository.members(project_id)]
            return ProjectMemberListResponse(members=members, count=len(members))

    def add_member(
        self,
        principal: AuthenticatedPrincipal,
        project_id: str,
        payload: ProjectMemberCreateRequest,
    ) -> ProjectMemberResponse:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            repository.get_or_raise(project_id)
            actor_membership = repository.membership(project_id, principal.user_id)
            require_project_role(principal, actor_membership, "admin")
            if (
                payload.role == "owner"
                and principal.role != "admin"
                and actor_membership.role != "owner"
            ):
                raise AuthForbiddenError("Only a project owner can add another owner.")
            if session.get(User, payload.user_id) is None:
                raise ValidationAppError("The requested user does not exist.")
            try:
                member = repository.add_member(project_id, payload.user_id, payload.role)
                AuditLogRepository(session).record(
                    principal,
                    "project_member_added",
                    "project_member",
                    member.id,
                    project_id,
                    {"member_user_id": payload.user_id, "member_role": payload.role},
                )
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ValidationAppError("The user is already a project member.") from exc
            return _member_response(member)

    def remove_member(
        self, principal: AuthenticatedPrincipal, project_id: str, user_id: str
    ) -> None:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            repository.get_or_raise(project_id)
            actor_membership = repository.membership(project_id, principal.user_id)
            require_project_role(principal, actor_membership, "admin")
            target = repository.membership(project_id, user_id)
            if target is None:
                raise ValidationAppError("The user is not a project member.")
            if target.role == "owner" and principal.role != "admin":
                raise AuthForbiddenError("Project owners cannot be removed by project admins.")
            target_id = target.id
            repository.remove_member(target)
            AuditLogRepository(session).record(
                principal,
                "project_member_removed",
                "project_member",
                target_id,
                project_id,
                {"member_user_id": user_id},
            )
            session.commit()

    def jobs(self, principal: AuthenticatedPrincipal, project_id: str) -> JobListResponse:
        with self.session_factory() as session:
            repository = ProjectRepository(session)
            repository.get_or_raise(project_id)
            require_project_role(
                principal, repository.membership(project_id, principal.user_id), "viewer"
            )
            jobs = [
                job_to_detail(job) for job in JobRepository(session).list_for_project(project_id)
            ]
            return JobListResponse(jobs=jobs, count=len(jobs))
