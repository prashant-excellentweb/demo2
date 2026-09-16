"""Restructure chat storage: messages table, attachments on disk, server-side quota

Revision ID: b7c4e9a10f23
Revises: d51f217a9573
Create Date: 2026-09-16 10:40:00.000000

Replaces the single `chat_sessions.messages` JSON blob with a real `messages`
table and moves uploads into an `attachments` table backed by files on disk.

Existing conversations are migrated in place. Base64 images that were embedded
in the old JSON are decoded and written under the upload directory so no
attachment is lost. The client-writable `token_limit` / `locked_until` columns
are dropped in favour of the server-side `usage_counters` table.
"""

import base64
import binascii
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "b7c4e9a10f23"
down_revision: str | Sequence[str] | None = "d51f217a9573"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table)}


# --------------------------------------------------------------------- tables


def _create_baseline_tables(tables: set[str]) -> None:
    """Create `users` / `chat_sessions` when starting from an empty database.

    The first migration in this chain predates Alembic managing these tables, so
    a fresh install would otherwise have nothing to migrate against.
    """
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("username", sa.String(64), nullable=False),
            sa.Column("display_name", sa.String(128), nullable=True),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_users_username", "users", ["username"], unique=True)

    if "chat_sessions" not in tables:
        op.create_table(
            "chat_sessions",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("project_id", sa.String(36), nullable=True),
            sa.Column("title", sa.String(200), nullable=False, server_default="New Chat"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
        op.create_index("ix_chat_sessions_project_id", "chat_sessions", ["project_id"])
        op.create_index(
            "ix_chat_sessions_user_updated", "chat_sessions", ["user_id", "updated_at"]
        )


def _create_new_tables() -> None:
    # Guarded individually so a partially applied run can be retried: SQLite
    # commits DDL outside the migration transaction.
    existing = _tables()

    if "messages" not in existing:
        _create_messages_table()
    if "attachments" not in existing:
        _create_attachments_table()
    if "usage_counters" not in existing:
        _create_usage_table()
    if "response_cache" not in existing:
        _create_cache_table()


def _create_messages_table() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("chat_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["chat_id"], ["chat_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_chat_created", "messages", ["chat_id", "created_at"])


def _create_attachments_table() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("message_id", sa.String(36), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("is_image", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("storage_path", sa.String(512), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_attachments_user_id", "attachments", ["user_id"])
    op.create_index("ix_attachments_message_id", "attachments", ["message_id"])
    op.create_index(
        "ix_attachments_user_message", "attachments", ["user_id", "message_id"]
    )


def _create_usage_table() -> None:
    op.create_table(
        "usage_counters",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("user_id", "usage_date"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def _create_cache_table() -> None:
    op.create_table(
        "response_cache",
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cache_key"),
    )
    op.create_index("ix_response_cache_expires_at", "response_cache", ["expires_at"])


# ------------------------------------------------------------------ data move


def _as_datetime(value: object) -> datetime | None:
    """Timestamps predating this schema may still be stored as text."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _upload_root() -> Path:
    try:
        from app.core.config import settings

        return Path(settings.UPLOAD_DIR)
    except Exception:
        return Path(__file__).resolve().parents[2] / "var" / "uploads"


def _persist_legacy_image(user_id: str, data_url: str) -> tuple[str, str, int] | None:
    """Decode a base64 data URL onto disk, returning (path, content_type, size)."""
    try:
        header, _, encoded = data_url.partition(",")
        if not encoded or "base64" not in header:
            return None
        content_type = header.split(";")[0].removeprefix("data:") or "image/png"
        raw = base64.b64decode(encoded, validate=False)
    except (binascii.Error, ValueError):
        return None
    if not raw:
        return None

    suffix = _IMAGE_EXTENSIONS.get(content_type, ".png")
    relative = Path(user_id) / f"{uuid.uuid4().hex}{suffix}"
    destination = _upload_root() / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return relative.as_posix(), content_type, len(raw)


def _legacy_rows(connection) -> list[sa.Row]:
    """Read the old transcripts through typed columns.

    Declaring the types matters: a raw textual SELECT hands back SQLite's stored
    strings, whereas this lets the dialect decode the JSON blob and build real
    datetime objects.
    """
    legacy = sa.table(
        "chat_sessions",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("messages", sa.JSON),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    return list(
        connection.execute(
            sa.select(
                legacy.c.id,
                legacy.c.user_id,
                legacy.c.messages,
                legacy.c.created_at,
                legacy.c.updated_at,
            ).order_by(legacy.c.created_at)
        )
    )


def _migrate_transcripts() -> None:
    connection = op.get_bind()
    messages_table = sa.table(
        "messages",
        sa.column("id", sa.String),
        sa.column("chat_id", sa.String),
        sa.column("role", sa.String),
        sa.column("content", sa.Text),
        sa.column("token_count", sa.Integer),
        sa.column("sources", sa.JSON),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    attachments_table = sa.table(
        "attachments",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("message_id", sa.String),
        sa.column("filename", sa.String),
        sa.column("content_type", sa.String),
        sa.column("size_bytes", sa.Integer),
        sa.column("is_image", sa.Boolean),
        sa.column("storage_path", sa.String),
        sa.column("text_content", sa.Text),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    message_rows: list[dict] = []
    attachment_rows: list[dict] = []

    for chat in _legacy_rows(connection):
        raw = chat.messages
        if not raw:
            continue
        try:
            transcript = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            continue
        if not isinstance(transcript, list):
            continue

        # The legacy columns were nullable, and `messages.created_at` is not,
        # so fall back rather than inserting a row that violates the constraint.
        base_time = (
            _as_datetime(chat.created_at)
            or _as_datetime(chat.updated_at)
            or datetime.now(UTC)
        )

        for index, entry in enumerate(transcript):
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            if role not in ("user", "assistant"):
                continue

            # The old client stored the model-facing blob in `content` and the
            # human-readable text in `display_text`; the latter is what should
            # survive as the transcript.
            content = entry.get("display_text") or entry.get("content") or ""
            if not isinstance(content, str):
                content = str(content)

            sources = entry.get("web_search_results")
            if not isinstance(sources, list) or not sources:
                sources = None

            message_id = str(uuid.uuid4())
            # Offset by position so the original ordering survives, since the
            # legacy rows carried no per-message timestamp.
            timestamp = base_time + timedelta(seconds=index)

            message_rows.append(
                {
                    "id": message_id,
                    "chat_id": chat.id,
                    "role": role,
                    "content": content,
                    "token_count": 0,
                    "sources": sources,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )

            for legacy in entry.get("attachments") or []:
                if not isinstance(legacy, dict):
                    continue
                filename = legacy.get("filename") or legacy.get("name") or "attachment"
                content_type = legacy.get("file_type") or legacy.get("type") or "text/plain"
                payload = legacy.get("content")
                if not isinstance(payload, str) or not payload:
                    continue

                if legacy.get("is_image") and payload.startswith("data:"):
                    stored = _persist_legacy_image(chat.user_id, payload)
                    if stored is None:
                        continue
                    storage_path, content_type, size_bytes = stored
                    text_content = None
                    is_image = True
                else:
                    storage_path = None
                    text_content = payload
                    size_bytes = len(payload.encode("utf-8"))
                    is_image = False

                attachment_rows.append(
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": chat.user_id,
                        "message_id": message_id,
                        "filename": filename,
                        "content_type": content_type,
                        "size_bytes": size_bytes,
                        "is_image": is_image,
                        "storage_path": storage_path,
                        "text_content": text_content,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    }
                )

    if message_rows:
        op.bulk_insert(messages_table, message_rows)
    if attachment_rows:
        op.bulk_insert(attachments_table, attachment_rows)


# ------------------------------------------------------------------- upgrade


def upgrade() -> None:
    tables = _tables()
    _create_baseline_tables(tables)
    _create_new_tables()

    tables = _tables()

    if "users" in tables:
        user_columns = _columns("users")
        if "is_active" not in user_columns:
            op.add_column(
                "users",
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            )
        if "updated_at" not in user_columns:
            op.add_column(
                "users",
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            )
            op.execute("UPDATE users SET updated_at = created_at WHERE updated_at IS NULL")

    chat_columns = _columns("chat_sessions")

    if "total_tokens" not in chat_columns:
        op.add_column(
            "chat_sessions",
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        )

    if "messages" in chat_columns:
        _migrate_transcripts()

    # Drop the legacy blob and the quota columns the browser used to supply.
    legacy_chat_columns = [
        column
        for column in ("messages", "token_limit", "locked_until")
        if column in chat_columns
    ]
    if legacy_chat_columns:
        with op.batch_alter_table("chat_sessions") as batch:
            for column in legacy_chat_columns:
                batch.drop_column(column)

    if "ix_chat_sessions_user_project" not in _indexes("chat_sessions"):
        op.create_index(
            "ix_chat_sessions_user_project", "chat_sessions", ["user_id", "project_id"]
        )

    if "projects" in tables and "ix_projects_user_name" not in _indexes("projects"):
        op.create_index("ix_projects_user_name", "projects", ["user_id", "name"])

    # The old cache table is disposable; entries are regenerated on demand.
    if "global_cache" in tables:
        op.drop_table("global_cache")


def downgrade() -> None:
    tables = _tables()

    if "ix_projects_user_name" in (_indexes("projects") if "projects" in tables else set()):
        op.drop_index("ix_projects_user_name", table_name="projects")
    if "ix_chat_sessions_user_project" in _indexes("chat_sessions"):
        op.drop_index("ix_chat_sessions_user_project", table_name="chat_sessions")

    with op.batch_alter_table("chat_sessions") as batch:
        batch.add_column(sa.Column("messages", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column("token_limit", sa.Integer(), nullable=True, server_default="1000")
        )
        batch.add_column(
            sa.Column("locked_until", sa.BigInteger(), nullable=True, server_default="0")
        )

    op.drop_index("ix_response_cache_expires_at", table_name="response_cache")
    op.drop_table("response_cache")
    op.drop_table("usage_counters")
    op.drop_index("ix_attachments_user_message", table_name="attachments")
    op.drop_index("ix_attachments_message_id", table_name="attachments")
    op.drop_index("ix_attachments_user_id", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("ix_messages_chat_created", table_name="messages")
    op.drop_table("messages")
