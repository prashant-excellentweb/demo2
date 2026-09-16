import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)

from app.core.config import settings
from app.core.exceptions import UpstreamServiceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompletionChunk:
    """One streamed fragment. `usage_tokens` is set only on the final chunk."""

    delta: str = ""
    usage_tokens: int | None = None


# A provider returns 429 both for "slow down" and for "this account is out of
# credits". Only the first is worth retrying, and telling someone to retry an
# exhausted balance sends them into a loop.
_QUOTA_MARKERS = frozenset(
    {"insufficient_quota", "credit_balance_exhausted", "billing_hard_limit_reached"}
)


def _is_quota_exhausted(exc: RateLimitError) -> bool:
    body = exc.body if isinstance(getattr(exc, "body", None), dict) else {}
    error = body.get("error") if isinstance(body.get("error"), dict) else {}
    candidates = {getattr(exc, "code", None), error.get("code"), error.get("type")}
    return bool(candidates & _QUOTA_MARKERS)


class AIService:
    """Thin async wrapper over the OpenAI-compatible provider."""

    def __init__(self, client: AsyncOpenAI | None = None, model: str | None = None):
        self._client = client or AsyncOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
        self.model = model or settings.ai_model

    async def _open_stream(self, prompt: list[dict], temperature: float, max_tokens: int):
        kwargs = {
            "model": self.model,
            "messages": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            # Ask the provider to report usage on the terminal chunk so token
            # accounting does not rely on estimation.
            "stream_options": {"include_usage": True},
        }
        try:
            return await self._client.chat.completions.create(**kwargs)
        except TypeError:
            # Providers/SDK versions that reject stream_options fall back to
            # estimated usage.
            kwargs.pop("stream_options")
            return await self._client.chat.completions.create(**kwargs)

    async def stream_completion(
        self, prompt: list[dict], temperature: float, max_tokens: int
    ) -> AsyncIterator[CompletionChunk]:
        try:
            stream = await self._open_stream(prompt, temperature, max_tokens)
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning("AI provider unreachable: %s", exc)
            raise UpstreamServiceError(
                "The AI service is not responding. Please try again."
            ) from exc
        except RateLimitError as exc:
            if _is_quota_exhausted(exc):
                logger.error("AI provider quota exhausted: %s", exc)
                raise UpstreamServiceError(
                    "The AI provider account has no credits left. "
                    "Add credits or switch providers to continue."
                ) from exc
            logger.warning("AI provider rate limited: %s", exc)
            raise UpstreamServiceError(
                "The AI service is rate limited right now. Please retry shortly."
            ) from exc
        except (AuthenticationError, PermissionDeniedError) as exc:
            # A bad or missing key is a deployment problem, not something the
            # person chatting can resolve by retrying, so name the cause.
            logger.error("AI provider rejected the credentials: %s", exc)
            raise UpstreamServiceError(
                f"The {settings.AI_PROVIDER} API key was rejected. "
                "Check the key in your .env file."
            ) from exc
        except APIError as exc:
            logger.error("AI provider rejected the request: %s", exc)
            raise UpstreamServiceError("The AI service rejected the request.") from exc

        try:
            async for event in stream:
                usage = getattr(event, "usage", None)
                if usage is not None and getattr(usage, "total_tokens", None):
                    yield CompletionChunk(usage_tokens=usage.total_tokens)

                for choice in event.choices or []:
                    delta = getattr(choice.delta, "content", None)
                    if delta:
                        yield CompletionChunk(delta=delta)
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning("AI stream interrupted: %s", exc)
            raise UpstreamServiceError("The AI response was interrupted.") from exc
        except APIError as exc:
            logger.error("AI stream failed: %s", exc)
            raise UpstreamServiceError("The AI service failed mid-response.") from exc
