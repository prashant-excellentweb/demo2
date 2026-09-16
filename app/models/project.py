from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.user import User


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        # Sidebar loads a user's projects ordered by name.
        Index("ix_projects_user_name", "user_id", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="projects")
    chats: Mapped[list["ChatSession"]] = relationship(back_populates="project")
