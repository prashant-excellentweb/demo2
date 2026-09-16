"""Test configuration.

The environment is prepared before `app` is imported because `Settings` is
instantiated at import time; real environment variables take precedence over
the project's `.env`, so a developer's local credentials never leak into a run.
"""

import os
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="buddy-tests-"))

os.environ.update(
    {
        "ENVIRONMENT": "development",
        "SECRET_KEY": "test-secret-key-long-enough-for-validation-0000",
        "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
        "AI_PROVIDER": "groq",
        "GROQ_API_KEY": "test-key",
        "UPLOAD_DIR": str(_TMP / "uploads"),
        "DAILY_TOKEN_BUDGET": "100000",
        "LOG_LEVEL": "WARNING",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import DbSession, get_chat_service  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.ai import CompletionChunk  # noqa: E402
from app.services.chat import ChatService  # noqa: E402

FAKE_REPLY = "Hello from the stubbed model."


class FakeAIService:
    """Streams a canned reply so tests never touch a real provider."""

    model = "fake-model"

    async def stream_completion(
        self, prompt: list[dict], temperature: float, max_tokens: int
    ) -> AsyncIterator[CompletionChunk]:
        self.last_prompt = prompt
        for word in FAKE_REPLY.split(" "):
            yield CompletionChunk(delta=word + " ")
        yield CompletionChunk(usage_tokens=42)


class FakeSearchService:
    async def search(self, query: str) -> list:
        from app.schemas.search import SearchResult

        return [
            SearchResult(
                title=f"Result for {query}",
                url="https://example.com/a",
                snippet="A snippet.",
            )
        ]


def _chat_service_override(session: DbSession) -> ChatService:
    return ChatService(
        session, ai_service=FakeAIService(), search_service=FakeSearchService()
    )


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _stub_ai() -> Iterator[None]:
    app.dependency_overrides[get_chat_service] = _chat_service_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


_counter = {"value": 0}


@pytest.fixture
def account(client: TestClient) -> dict:
    """Register a fresh user and leave the session cookie on the client."""
    _counter["value"] += 1
    username = f"tester{_counter['value']}"
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "sup3r-secret", "display_name": "Tester"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def read_sse(response) -> list[dict]:
    """Parse an SSE body into its decoded event payloads."""
    import json

    events = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line.removeprefix("data: ")))
    return events
