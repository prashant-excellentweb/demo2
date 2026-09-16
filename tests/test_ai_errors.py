"""Provider 429s must be told apart: throttling is retryable, no credits is not."""

import httpx
import pytest
from openai import AuthenticationError, RateLimitError

from app.core.exceptions import UpstreamServiceError
from app.services.ai import AIService


def _rate_limit_error(body: dict) -> RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request, json=body)
    return RateLimitError("429", response=response, body=body.get("error"))


class _FailingClient:
    """Stands in for AsyncOpenAI so no network call is attempted."""

    def __init__(self, error: Exception):
        self._error = error
        completions = type("C", (), {"create": self._create})()
        self.chat = type("Chat", (), {"completions": completions})()

    async def _create(self, **_kwargs):
        raise self._error


async def _drain(service: AIService) -> None:
    async for _ in service.stream_completion([{"role": "user", "content": "hi"}], 0.7, 64):
        pass


@pytest.mark.asyncio
async def test_exhausted_credits_says_so_instead_of_suggesting_retry() -> None:
    error = _rate_limit_error(
        {
            "error": {
                "message": "You have no credits remaining.",
                "type": "insufficient_quota",
                "code": "credit_balance_exhausted",
            }
        }
    )
    service = AIService(client=_FailingClient(error), model="gpt-test")

    with pytest.raises(UpstreamServiceError) as caught:
        await _drain(service)

    assert "no credits left" in str(caught.value)


@pytest.mark.asyncio
async def test_plain_throttling_still_asks_for_a_retry() -> None:
    error = _rate_limit_error(
        {"error": {"message": "Rate limit reached", "type": "requests", "code": None}}
    )
    service = AIService(client=_FailingClient(error), model="gpt-test")

    with pytest.raises(UpstreamServiceError) as caught:
        await _drain(service)

    assert "retry shortly" in str(caught.value)


@pytest.mark.asyncio
async def test_rejected_key_points_at_the_configuration() -> None:
    """A 401 is an operator problem, so the message must not read as transient."""
    body = {"error": {"message": "Invalid API Key", "code": "invalid_api_key"}}
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    error = AuthenticationError(
        "401", response=httpx.Response(401, request=request, json=body), body=body["error"]
    )
    service = AIService(client=_FailingClient(error), model="gpt-test")

    with pytest.raises(UpstreamServiceError) as caught:
        await _drain(service)

    message = str(caught.value)
    assert "API key was rejected" in message
    assert ".env" in message
