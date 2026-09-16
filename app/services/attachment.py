import io
import logging
import uuid
from datetime import timedelta
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from app.db.base import utcnow
from app.models import Attachment, User
from app.repositories.attachment import AttachmentRepository

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 64 * 1024

# An explicit allowlist rather than `mimetypes.guess_type`, which consults the
# Windows registry and therefore resolves the same extension differently on a
# developer machine than on the Linux host.
EXTENSION_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".pdf": "application/pdf",
}

IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# Leading bytes that must be present for a file to be treated as an image, so a
# script renamed to .png is rejected rather than stored and later served back.
_IMAGE_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def _sniff_image_type(data: bytes) -> str | None:
    for signature, content_type in _IMAGE_SIGNATURES:
        if data.startswith(signature):
            return content_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class AttachmentService:
    def __init__(self, session: Session):
        self.session = session
        self.attachments = AttachmentRepository(session)

    @property
    def _root(self) -> Path:
        return Path(settings.UPLOAD_DIR)

    async def _read_limited(self, upload: UploadFile) -> bytes:
        """Stream the upload, aborting as soon as the size cap is passed.

        Reading in chunks means a hostile 2 GB upload is refused after 10 MB
        instead of being buffered in full first.
        """
        buffer = io.BytesIO()
        total = 0
        while chunk := await upload.read(_CHUNK_SIZE):
            total += len(chunk)
            if total > settings.MAX_UPLOAD_BYTES:
                limit_mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
                raise PayloadTooLargeError(f"Files must be {limit_mb} MB or smaller.")
            buffer.write(chunk)
        if total == 0:
            raise ValidationError("The uploaded file is empty.")
        return buffer.getvalue()

    def _resolve_content_type(self, filename: str) -> str:
        """Derive the type from the extension, not the browser-supplied header."""
        resolved = EXTENSION_TYPES.get(Path(filename).suffix.lower())
        if resolved is None:
            raise UnsupportedMediaTypeError(
                "Supported uploads: images (JPEG, PNG, GIF, WebP), PDF, and text "
                "files (TXT, CSV, Markdown, JSON)."
            )
        return resolved

    @staticmethod
    def _extract_pdf_text(data: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise ValidationError(
                "PDF support is unavailable because pypdf is not installed."
            ) from exc

        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            logger.warning("Unreadable PDF upload: %s", exc)
            raise ValidationError("That PDF could not be read.") from exc

        text = "\n\n".join(page.strip() for page in pages if page.strip())
        if not text:
            raise ValidationError(
                "That PDF contains no extractable text. Scanned documents need OCR."
            )
        return text

    def _write_to_disk(self, user_id: str, data: bytes, suffix: str) -> str:
        """Persist under a generated name; the client filename never touches the path."""
        relative = Path(user_id) / f"{uuid.uuid4().hex}{suffix}"
        destination = self._root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return relative.as_posix()

    async def store(self, user: User, upload: UploadFile) -> Attachment:
        filename = Path(upload.filename or "upload").name
        content_type = self._resolve_content_type(filename)
        data = await self._read_limited(upload)

        is_image = content_type in IMAGE_TYPES
        storage_path: str | None = None
        text_content: str | None = None

        if is_image:
            sniffed = _sniff_image_type(data)
            if sniffed is None:
                raise UnsupportedMediaTypeError(
                    "That file is not a valid image despite its extension."
                )
            content_type = sniffed
            storage_path = self._write_to_disk(user.id, data, IMAGE_TYPES[content_type])
        elif content_type == "application/pdf":
            text_content = self._extract_pdf_text(data)
            storage_path = self._write_to_disk(user.id, data, ".pdf")
        else:
            try:
                text_content = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValidationError(
                    "Text uploads must be UTF-8 encoded."
                ) from exc

        attachment = self.attachments.create(
            user_id=user.id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            is_image=is_image,
            storage_path=storage_path,
            text_content=text_content,
        )
        self.session.commit()
        self.session.refresh(attachment)
        return attachment

    def resolve_file(self, attachment_id: str, user: User) -> tuple[Attachment, Path]:
        attachment = self.attachments.get_owned(attachment_id, user.id)
        if attachment is None or not attachment.storage_path:
            raise NotFoundError("Attachment not found.")

        root = self._root.resolve()
        path = (root / attachment.storage_path).resolve()
        # Defence in depth: refuse anything that escapes the upload root even if
        # a stored path were ever tampered with.
        if not path.is_file() or root not in path.parents:
            raise NotFoundError("Attachment file is missing.")
        return attachment, path

    def purge_orphans(self, older_than_hours: int = 24) -> int:
        """Delete uploads that were staged in the composer but never sent."""
        cutoff = utcnow() - timedelta(hours=older_than_hours)
        orphans = self.attachments.list_orphans_before(cutoff)
        for orphan in orphans:
            if orphan.storage_path:
                (self._root / orphan.storage_path).unlink(missing_ok=True)
        self.attachments.delete_by_ids([orphan.id for orphan in orphans])
        self.session.commit()
        return len(orphans)
