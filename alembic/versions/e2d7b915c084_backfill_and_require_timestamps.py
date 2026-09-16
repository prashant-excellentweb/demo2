"""Backfill NULL timestamps and make them NOT NULL

Revision ID: e2d7b915c084
Revises: c8f1a2b34d56
Create Date: 2026-09-16 14:10:00.000000

`created_at` / `updated_at` were nullable on the original tables, so early rows
carry NULLs. The models and response schemas both declare them required, which
means a single NULL row returns a 500 instead of data: one NULL in
`chat_sessions` breaks the whole chat list, and one in `users` breaks
`/api/auth/me` and therefore sign-in for that account.

This fills the gaps (preferring the row's other timestamp) and then tightens the
columns so the schema matches the models.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e2d7b915c084"
down_revision: str | Sequence[str] | None = "c8f1a2b34d56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables carrying both timestamp columns, in dependency order.
_TABLES = ("users", "projects", "chat_sessions")


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _existing_tables()
    now = sa.func.current_timestamp()

    for table in _TABLES:
        if table not in tables:
            continue
        columns = _column_names(table)
        if "created_at" not in columns or "updated_at" not in columns:
            continue

        # Prefer the sibling timestamp so ordering stays meaningful; only fall
        # back to "now" when the row has neither.
        op.execute(
            sa.text(
                f"UPDATE {table} SET created_at = COALESCE(updated_at, CURRENT_TIMESTAMP) "
                "WHERE created_at IS NULL"
            )
        )
        op.execute(
            sa.text(
                f"UPDATE {table} SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP) "
                "WHERE updated_at IS NULL"
            )
        )

        with op.batch_alter_table(table) as batch:
            for column in ("created_at", "updated_at"):
                batch.alter_column(
                    column,
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False,
                    existing_server_default=now,
                )


def downgrade() -> None:
    tables = _existing_tables()

    for table in reversed(_TABLES):
        if table not in tables:
            continue
        columns = _column_names(table)
        if "created_at" not in columns or "updated_at" not in columns:
            continue
        with op.batch_alter_table(table) as batch:
            for column in ("created_at", "updated_at"):
                batch.alter_column(
                    column,
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True,
                )
