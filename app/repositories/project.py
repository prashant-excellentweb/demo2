from sqlalchemy import select, update

from app.models import ChatSession, Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository):
    def list_for_user(self, user_id: str) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.name.asc())
        )
        return list(self.session.scalars(stmt))

    def get_owned(self, project_id: str, user_id: str) -> Project | None:
        """Ownership is part of the predicate so a wrong id cannot leak another
        user's project."""
        stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
        return self.session.scalar(stmt)

    def create(self, user_id: str, name: str, description: str | None) -> Project:
        project = Project(user_id=user_id, name=name, description=description)
        self.add(project)
        self.flush()
        return project

    def detach_chats(self, project_id: str) -> None:
        """Move a deleted project's chats back to the unfiled list in one statement."""
        self.session.execute(
            update(ChatSession)
            .where(ChatSession.project_id == project_id)
            .values(project_id=None)
        )
