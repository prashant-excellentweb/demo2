from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.project import Project


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    projects: Mapped[list["Project"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    chats: Mapped[list["ChatSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def label(self) -> str:
        return self.display_name or self.username
