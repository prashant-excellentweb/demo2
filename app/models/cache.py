from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class ResponseCache(Base):
    """Deduplicates identical prompts to avoid paying for the same completion twice.

    This is a pragmatic SQL-backed cache. Under real concurrency move it to Redis
    (`SETEX`) — see `app.services.cache` for the seam that makes that a drop-in.
    """

    __tablename__ = "response_cache"
    __table_args__ = (
        # Supports the periodic purge of expired entries.
        Index("ix_response_cache_expires_at", "expires_at"),
    )

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
