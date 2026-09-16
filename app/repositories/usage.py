from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models import UsageCounter
from app.repositories.base import BaseRepository


class UsageRepository(BaseRepository):
    def tokens_used_on(self, user_id: str, usage_date: date) -> int:
        stmt = select(UsageCounter.tokens_used).where(
            UsageCounter.user_id == user_id, UsageCounter.usage_date == usage_date
        )
        return self.session.scalar(stmt) or 0

    def increment(self, user_id: str, usage_date: date, tokens: int) -> None:
        """Atomic upsert-and-add.

        Done as a single `ON CONFLICT DO UPDATE` so two concurrent completions
        cannot read-modify-write over each other and undercount usage.
        """
        if tokens <= 0:
            return

        dialect = self.session.get_bind().dialect.name
        insert = pg_insert if dialect == "postgresql" else sqlite_insert
        stmt = insert(UsageCounter).values(
            user_id=user_id, usage_date=usage_date, tokens_used=tokens
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[UsageCounter.user_id, UsageCounter.usage_date],
            set_={"tokens_used": UsageCounter.tokens_used + tokens},
        )
        self.session.execute(stmt)
