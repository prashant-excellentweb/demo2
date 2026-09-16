"""`messages.role` must hold the lowercase enum value, not the member name.

SQLAlchemy's Enum type defaults to persisting member *names*, so the column
would hold "USER" while migrations, the API contract and the provider payload
all use "user". The mismatch is invisible through the API — Pydantic serialises
the enum either way — but it makes rows written by one convention unreadable
under the other.
"""

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.session import SessionLocal, engine
from app.models import Message, MessageRole


def test_stored_role_uses_lowercase_values(client: TestClient, account: dict) -> None:
    chat_id = client.post("/api/chats", json={}).json()["id"]
    client.post(f"/api/chats/{chat_id}/messages", json={"content": "Hi"})

    with engine.connect() as connection:
        stored = connection.execute(
            text("SELECT DISTINCT role FROM messages WHERE chat_id = :chat"),
            {"chat": chat_id},
        ).scalars().all()

    assert sorted(stored) == ["assistant", "user"]


def test_rows_written_as_values_load_through_the_orm(
    client: TestClient, account: dict
) -> None:
    """Guards the exact failure mode: a lowercase row raising LookupError."""
    chat_id = client.post("/api/chats", json={}).json()["id"]
    client.post(f"/api/chats/{chat_id}/messages", json={"content": "Hi"})

    # A fresh session cannot reuse an identity map, so this really re-reads.
    with SessionLocal() as session:
        roles = session.scalars(
            select(Message.role).where(Message.chat_id == chat_id)
        ).all()

    assert roles == [MessageRole.USER, MessageRole.ASSISTANT]
