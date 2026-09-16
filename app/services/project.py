from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Project, User
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectWriteRequest


class ProjectService:
    def __init__(self, session: Session):
        self.session = session
        self.projects = ProjectRepository(session)

    def list_for_user(self, user: User) -> list[Project]:
        return self.projects.list_for_user(user.id)

    def get_owned_or_404(self, project_id: str, user: User) -> Project:
        project = self.projects.get_owned(project_id, user.id)
        if project is None:
            raise NotFoundError("Project not found.")
        return project

    def create(self, user: User, payload: ProjectWriteRequest) -> Project:
        project = self.projects.create(user.id, payload.name, payload.description)
        self.session.commit()
        self.session.refresh(project)
        return project

    def update(self, project_id: str, user: User, payload: ProjectWriteRequest) -> Project:
        project = self.get_owned_or_404(project_id, user)
        project.name = payload.name
        project.description = payload.description
        self.session.commit()
        self.session.refresh(project)
        return project

    def delete(self, project_id: str, user: User) -> None:
        project = self.get_owned_or_404(project_id, user)
        # Deleting a folder must not destroy the conversations inside it; they
        # fall back to the unfiled list.
        self.projects.detach_chats(project.id)
        self.projects.delete(project)
        self.session.commit()
