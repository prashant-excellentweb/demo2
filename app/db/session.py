from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _build_engine() -> Engine:
    if settings.DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.SQL_ECHO,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            # SQLite ignores foreign keys unless asked, and the default rollback
            # journal serialises readers against a single writer.
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        return engine

    return create_engine(
        settings.DATABASE_URL,
        echo=settings.SQL_ECHO,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session.

    Rolls back on failure so a half-applied unit of work is never committed by a
    later handler reusing the connection.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
