"""Add timestamps and indexes for chat sessions and users

Revision ID: d51f217a9573
Revises: adee280e57e2
Create Date: 2026-06-18 17:08:25.292238

Rewritten to use the SQLAlchemy inspector rather than SQLite-only `sqlite_master`
and `PRAGMA` queries, so the chain also applies on PostgreSQL and no-ops cleanly
against a database where these tables do not exist yet.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d51f217a9573"
down_revision: str | Sequence[str] | None = "adee280e57e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    ("ix_chat_sessions_project_id", "chat_sessions", ["project_id"]),
    ("ix_chat_sessions_user_id", "chat_sessions", ["user_id"]),
    ("ix_chat_sessions_user_updated", "chat_sessions", ["user_id", "updated_at"]),
    ("ix_projects_user_id", "projects", ["user_id"]),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    tables = _tables()

    if "chat_sessions" in tables:
        columns = _columns("chat_sessions")
        for column in ("created_at", "updated_at"):
            if column not in columns:
                op.add_column("chat_sessions", sa.Column(column, sa.DateTime(), nullable=True))
        op.execute(
            "UPDATE chat_sessions SET created_at = CURRENT_TIMESTAMP "
            "WHERE created_at IS NULL"
        )
        op.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP "
            "WHERE updated_at IS NULL"
        )

    if "users" in tables and "created_at" not in _columns("users"):
        op.add_column("users", sa.Column("created_at", sa.DateTime(), nullable=True))
        op.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    for name, table, columns in _INDEXES:
        if table in tables and name not in _indexes(table):
            op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    tables = _tables()

    for name, table, _ in reversed(_INDEXES):
        if table in tables and name in _indexes(table):
            op.drop_index(name, table_name=table)

    if "users" in tables and "created_at" in _columns("users"):
        op.drop_column("users", "created_at")

    if "chat_sessions" in tables:
        columns = _columns("chat_sessions")
        for column in ("updated_at", "created_at"):
            if column in columns:
                op.drop_column("chat_sessions", column)
