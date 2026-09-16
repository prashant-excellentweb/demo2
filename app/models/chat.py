import enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.project import Project
    from app.models.user import User


class MessageRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        # Sidebar query: newest chats for one user.
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
        # Chats filtered to a single project folder.
        Index("ix_chat_sessions_user_project", "user_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), default="New Chat", nullable=False)
    # Cumulative tokens billed to this chat. Written only by the server.
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="chats")
    project: Mapped["Project | None"] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (
        # Every transcript read walks one chat in chronological order.
        Index("ix_messages_chat_created", "chat_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    chat_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    # values_callable keeps the lowercase member values in the column. Without
    # it SQLAlchemy stores member *names* ("USER"), which would not match the
    # role strings the API returns and the provider expects.
    role: Mapped[MessageRole] = mapped_column(
        Enum(
            MessageRole,
            native_enum=False,
            length=16,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Web-search results that grounded this turn: [{title, url, snippet}, ...].
    sources: Mapped[list | None] = mapped_column(JSON)

    chat: Mapped["ChatSession"] = relationship(back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="Attachment.created_at",
    )
