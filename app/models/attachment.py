from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.chat import Message
    from app.models.user import User


class Attachment(Base, TimestampMixin):
    """An uploaded file.

    Binary payloads live on disk (`storage_path`) rather than base64-encoded
    inside a chat's JSON, so listing chats never transfers image bytes. Text
    documents keep their extracted text in `text_content` because that is what
    actually gets fed to the model.
    """

    __tablename__ = "attachments"
    __table_args__ = (
        # Reclaiming uploads a user never sent: message_id IS NULL, old created_at.
        Index("ix_attachments_user_message", "user_id", "message_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # NULL while the upload is still pending in the composer.
    message_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Path relative to settings.UPLOAD_DIR. Set for images/binary files only.
    storage_path: Mapped[str | None] = mapped_column(String(512))
    # Extracted text for document uploads.
    text_content: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship()
    message: Mapped["Message | None"] = relationship(back_populates="attachments")
