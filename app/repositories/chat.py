from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.models import ChatSession, Message
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class ChatSummary:
    """Sidebar projection: metadata only, never message bodies."""

    id: str
    title: str
    project_id: str | None
    total_tokens: int
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatRepository(BaseRepository):
    def list_summaries_for_user(self, user_id: str) -> list[ChatSummary]:
        """One query for the whole sidebar.

        The message count comes from a grouped LEFT JOIN rather than touching
        `chat.messages` per row, which would be an N+1 across every chat, and
        the transcript (including attachment bytes) is never loaded here.
        """
        stmt = (
            select(
                ChatSession.id,
                ChatSession.title,
                ChatSession.project_id,
                ChatSession.total_tokens,
                func.count(Message.id).label("message_count"),
                ChatSession.created_at,
                ChatSession.updated_at,
            )
            .outerjoin(Message, Message.chat_id == ChatSession.id)
            .where(ChatSession.user_id == user_id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.updated_at.desc())
        )
        return [ChatSummary(*row) for row in self.session.execute(stmt)]

    def get_owned(self, chat_id: str, user_id: str) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.id == chat_id, ChatSession.user_id == user_id
        )
        return self.session.scalar(stmt)

    def get_owned_with_messages(self, chat_id: str, user_id: str) -> ChatSession | None:
        """Load a transcript and its attachments in three queries, not one per message."""
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == chat_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages).selectinload(Message.attachments))
        )
        return self.session.scalar(stmt)

    def create(
        self, user_id: str, title: str, project_id: str | None, chat_id: str | None = None
    ) -> ChatSession:
        chat = ChatSession(user_id=user_id, title=title, project_id=project_id)
        if chat_id:
            chat.id = chat_id
        self.add(chat)
        self.flush()
        return chat

    def recent_context(self, chat_id: str, limit: int) -> list[Message]:
        """Newest `limit` messages, oldest-first, with attachments eagerly loaded.

        Context is capped in SQL so prompt size stays bounded no matter how long
        the conversation grows.
        """
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .options(selectinload(Message.attachments))
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        return list(reversed(list(self.session.scalars(stmt))))

    def get_message(self, message_id: str, chat_id: str) -> Message | None:
        stmt = select(Message).where(Message.id == message_id, Message.chat_id == chat_id)
        return self.session.scalar(stmt)

    def delete_from_message_onward(self, chat_id: str, pivot: Message) -> int:
        """Drop `pivot` and every later message, used by edit-and-resend."""
        result = self.session.execute(
            delete(Message).where(
                Message.chat_id == chat_id,
                Message.created_at >= pivot.created_at,
            )
        )
        return result.rowcount or 0

    def add_message(
        self,
        chat_id: str,
        role,
        content: str,
        token_count: int = 0,
        sources: list | None = None,
    ) -> Message:
        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            token_count=token_count,
            sources=sources,
        )
        self.add(message)
        self.flush()
        return message
