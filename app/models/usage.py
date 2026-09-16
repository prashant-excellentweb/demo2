from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageCounter(Base):
    """Per-user, per-day token spend.

    The old schema kept `token_limit`/`locked_until` on the chat row and let the
    browser POST them, so any client could raise its own ceiling. Usage is now
    accumulated server-side and checked before each completion.
    """

    __tablename__ = "usage_counters"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
