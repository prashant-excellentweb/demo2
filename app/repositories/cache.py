from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.db.base import utcnow
from app.models import ResponseCache
from app.repositories.base import BaseRepository


class ResponseCacheRepository(BaseRepository):
    def get_fresh(self, cache_key: str) -> ResponseCache | None:
        stmt = select(ResponseCache).where(
            ResponseCache.cache_key == cache_key,
            ResponseCache.expires_at > utcnow(),
        )
        return self.session.scalar(stmt)

    def put(
        self,
        cache_key: str,
        response_text: str,
        total_tokens: int,
        ttl_seconds: int,
    ) -> None:
        """Upsert via merge; the primary key is the cache key."""
        self.session.merge(
            ResponseCache(
                cache_key=cache_key,
                response_text=response_text,
                total_tokens=total_tokens,
                created_at=utcnow(),
                expires_at=utcnow() + timedelta(seconds=ttl_seconds),
            )
        )

    def purge_expired(self, now: datetime | None = None) -> int:
        result = self.session.execute(
            delete(ResponseCache).where(ResponseCache.expires_at <= (now or utcnow()))
        )
        return result.rowcount or 0
