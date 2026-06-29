"""Add timestamps and indexes for chat sessions and users

Revision ID: d51f217a9573
Revises: adee280e57e2
Create Date: 2026-06-18 17:08:25.292238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d51f217a9573"
down_revision: Union[str, Sequence[str], None] = "adee280e57e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(conn, name: str) -> bool:
    row = conn.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='index' AND name=:name"),
        {"name": name},
    ).fetchone()
    return row is not None


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def upgrade() -> None:
    """Upgrade schema (SQLite-safe)."""
    conn = op.get_bind()

    if not _column_exists(conn, "chat_sessions", "created_at"):
        op.add_column("chat_sessions", sa.Column("created_at", sa.DateTime(), nullable=True))
    if not _column_exists(conn, "chat_sessions", "updated_at"):
        op.add_column("chat_sessions", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.execute(
        "UPDATE chat_sessions SET created_at = datetime('now'), updated_at = datetime('now') "
        "WHERE created_at IS NULL OR updated_at IS NULL"
    )

    if not _column_exists(conn, "users", "created_at"):
        op.add_column("users", sa.Column("created_at", sa.DateTime(), nullable=True))

    op.execute(
        "UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL"
    )

    if not _index_exists(conn, "ix_chat_sessions_project_id"):
        op.create_index(
            op.f("ix_chat_sessions_project_id"),
            "chat_sessions",
            ["project_id"],
            unique=False,
        )
    if not _index_exists(conn, "ix_chat_sessions_user_id"):
        op.create_index(
            op.f("ix_chat_sessions_user_id"),
            "chat_sessions",
            ["user_id"],
            unique=False,
        )
    if not _index_exists(conn, "ix_chat_sessions_user_updated"):
        op.create_index(
            "ix_chat_sessions_user_updated",
            "chat_sessions",
            ["user_id", "updated_at"],
            unique=False,
        )
    if not _index_exists(conn, "ix_projects_user_id"):
        op.create_index(
            op.f("ix_projects_user_id"),
            "projects",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    for index_name in (
        "ix_projects_user_id",
        "ix_chat_sessions_user_updated",
        "ix_chat_sessions_user_id",
        "ix_chat_sessions_project_id",
    ):
        if _index_exists(conn, index_name):
            op.drop_index(index_name, table_name=(
                "projects" if index_name == "ix_projects_user_id" else "chat_sessions"
            ))

    if _column_exists(conn, "users", "created_at"):
        op.drop_column("users", "created_at")
    if _column_exists(conn, "chat_sessions", "updated_at"):
        op.drop_column("chat_sessions", "updated_at")
    if _column_exists(conn, "chat_sessions", "created_at"):
        op.drop_column("chat_sessions", "created_at")
