from datetime import datetime

from sqlalchemy import delete, select, update

from app.models import Attachment
from app.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository):
    def get_owned(self, attachment_id: str, user_id: str) -> Attachment | None:
        stmt = select(Attachment).where(
            Attachment.id == attachment_id, Attachment.user_id == user_id
        )
        return self.session.scalar(stmt)

    def list_pending_owned(self, attachment_ids: list[str], user_id: str) -> list[Attachment]:
        """Fetch the composer's staged uploads in one query.

        `message_id IS NULL` prevents replaying an attachment that already
        belongs to an earlier message.
        """
        if not attachment_ids:
            return []
        stmt = select(Attachment).where(
            Attachment.id.in_(attachment_ids),
            Attachment.user_id == user_id,
            Attachment.message_id.is_(None),
        )
        return list(self.session.scalars(stmt))

    def create(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        is_image: bool,
        storage_path: str | None,
        text_content: str | None,
    ) -> Attachment:
        attachment = Attachment(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            is_image=is_image,
            storage_path=storage_path,
            text_content=text_content,
        )
        self.add(attachment)
        self.flush()
        return attachment

    def bind_to_message(self, attachment_ids: list[str], message_id: str) -> None:
        if not attachment_ids:
            return
        self.session.execute(
            update(Attachment)
            .where(Attachment.id.in_(attachment_ids))
            .values(message_id=message_id)
        )

    def list_orphans_before(self, cutoff: datetime) -> list[Attachment]:
        """Uploads staged but never sent; their files are reclaimable."""
        stmt = select(Attachment).where(
            Attachment.message_id.is_(None), Attachment.created_at < cutoff
        )
        return list(self.session.scalars(stmt))

    def delete_by_ids(self, attachment_ids: list[str]) -> None:
        if not attachment_ids:
            return
        self.session.execute(delete(Attachment).where(Attachment.id.in_(attachment_ids)))
