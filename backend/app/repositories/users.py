from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Project, ProjectMember, User

DEMO_PROJECT_SLUG = "demo"


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: str) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.casefold()))

    def create(self, email: str, display_name: str | None = None) -> User:
        user = User(email=email.casefold(), display_name=display_name)
        self.session.add(user)
        self.session.flush()
        return user

    def ensure_demo(self, email: str) -> tuple[User, Project]:
        user = self.get_by_email(email)
        if user is None:
            user = self.create(email, "Demo User")
        project = self.session.scalar(select(Project).where(Project.slug == DEMO_PROJECT_SLUG))
        if project is None:
            project = Project(
                name="Demo Project",
                slug=DEMO_PROJECT_SLUG,
                description="Backward-compatible demo workspace.",
                created_by_user_id=user.id,
            )
            self.session.add(project)
            self.session.flush()
        member = self.session.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
        )
        if member is None:
            self.session.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
            self.session.flush()
        return user, project
