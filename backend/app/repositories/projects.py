from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import ProjectNotFoundError
from backend.app.db.models import Project, ProjectMember, utc_now


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, project_id: str) -> Project | None:
        return self.session.get(Project, project_id)

    def get_or_raise(self, project_id: str) -> Project:
        project = self.get(project_id)
        if project is None or project.status == "deleted":
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        return project

    def create(self, name: str, slug: str, description: str | None, user_id: str | None) -> Project:
        project = Project(name=name, slug=slug, description=description, created_by_user_id=user_id)
        self.session.add(project)
        self.session.flush()
        return project

    def list_for_user(self, user_id: str) -> list[Project]:
        statement = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id, Project.status == "active")
            .order_by(Project.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_all(self) -> list[Project]:
        return list(
            self.session.scalars(
                select(Project)
                .where(Project.status == "active")
                .order_by(Project.created_at.desc())
            )
        )

    def membership(self, project_id: str, user_id: str | None) -> ProjectMember | None:
        if user_id is None:
            return None
        return self.session.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )

    def members(self, project_id: str) -> list[ProjectMember]:
        return list(
            self.session.scalars(
                select(ProjectMember)
                .where(ProjectMember.project_id == project_id)
                .order_by(ProjectMember.created_at)
            )
        )

    def add_member(self, project_id: str, user_id: str, role: str) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        self.session.flush()
        return member

    def remove_member(self, member: ProjectMember) -> None:
        self.session.delete(member)

    def update(self, project: Project, **values: str | None) -> None:
        for key, value in values.items():
            if value is not None:
                setattr(project, key, value)
        project.updated_at = utc_now()
