"""Add projects table and project_id to chat_sessions

Revision ID: adee280e57e2
Revises:
Create Date: 2026-04-16 13:23:24.024345

This migration originally assumed `users` and `chat_sessions` had already been
created by `Base.metadata.create_all`. The guards below let the same script run
against a brand-new database, where the later restructure migration creates
those tables instead.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "adee280e57e2"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()

    if "projects" not in tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)

    if "chat_sessions" in tables and "project_id" not in _columns("chat_sessions"):
        op.add_column("chat_sessions", sa.Column("project_id", sa.String(), nullable=True))


def downgrade() -> None:
    tables = _tables()

    if "chat_sessions" in tables and "project_id" in _columns("chat_sessions"):
        op.drop_column("chat_sessions", "project_id")

    if "projects" in tables:
        op.drop_index(op.f("ix_projects_id"), table_name="projects")
        op.drop_table("projects")
