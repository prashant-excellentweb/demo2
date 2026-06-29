from sqlalchemy import Column, String, Integer, BigInteger, JSON, ForeignKey, DateTime, func, Index
from database import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class GlobalCache(Base):
    __tablename__ = "global_cache"

    query_hash = Column(String, primary_key=True, index=True)
    response_text = Column(String, nullable=False)
    total_tokens = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String, default="New Chat")
    messages = Column(JSON, default=list)
    total_tokens = Column(Integer, default=0)
    token_limit = Column(Integer, default=1000)
    locked_until = Column(BigInteger, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
