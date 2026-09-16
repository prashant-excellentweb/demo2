"""Normalise message.role to lowercase enum values

Revision ID: c8f1a2b34d56
Revises: b7c4e9a10f23
Create Date: 2026-09-16 13:55:00.000000

`Enum(MessageRole)` stored member *names* ("USER"), while the restructure
migration and the API contract both use member *values* ("user"). Rows written
during that window cannot be loaded by the ORM at all, so any chat containing
one raised LookupError on read. The model now pins the column to values; this
rewrites the rows that predate that change.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8f1a2b34d56"
down_revision: str | Sequence[str] | None = "b7c4e9a10f23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "messages" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.execute(
        sa.text(
            "UPDATE messages SET role = LOWER(role) "
            "WHERE role <> LOWER(role)"
        )
    )


def downgrade() -> None:
    # Deliberately not reverting: uppercase names were the bug, and restoring
    # them would break ORM reads again.
    pass
