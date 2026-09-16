import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import NotFoundError, QuotaExceededError, UpstreamServiceError
from app.db.base import utcnow
from app.models import Attachment, ChatSession, MessageRole, User
from app.repositories.attachment import AttachmentRepository
from app.repositories.cache import ResponseCacheRepository
from app.repositories.chat import ChatRepository, ChatSummary
from app.repositories.project import ProjectRepository
from app.repositories.usage import UsageRepository
from app.schemas.chat import (
    ChatCreateRequest,
    ChatUpdateRequest,
    EphemeralMessageRequest,
    SendMessageRequest,
)
from app.services import prompt as prompt_builder
from app.services.ai import AIService
from app.services.search import WebSearchService

logger = logging.getLogger(__name__)

# Cached replays are emitted in slices so the UI animates identically to a live
# stream instead of snapping the whole answer into place.
_CACHE_REPLAY_CHUNK = 24


@dataclass
class TurnPlan:
    """Everything decided before the first token arrives.

    Built while the request can still fail with a real status code, so a 404 or
    a quota rejection never has to be smuggled inside an already-open stream.
    """

    chat_id: str
    prompt: list[dict]
    user_message_id: str
    chat_title: str
    cache_key: str | None
    cached_text: str | None
    cached_tokens: int
    sources: list[dict] = field(default_factory=list)


class ChatService:
    """Owns a conversational turn end to end.

    The transcript lives on the server: a request contributes a single new
    message, and context is rebuilt from the database. The client can no longer
    forge prior assistant turns, drop the system prompt, or set its own token
    ceiling the way the previous `POST /api/chat` contract allowed.
    """

    def __init__(
        self,
        session: Session,
        ai_service: AIService | None = None,
        search_service: WebSearchService | None = None,
    ):
        self.session = session
        self.chats = ChatRepository(session)
        self.projects = ProjectRepository(session)
        self.attachments = AttachmentRepository(session)
        self.cache = ResponseCacheRepository(session)
        self.usage = UsageRepository(session)
        self.ai = ai_service or AIService()
        self.search = search_service or WebSearchService()

    # ------------------------------------------------------------------ CRUD

    def list_summaries(self, user: User) -> list[ChatSummary]:
        return self.chats.list_summaries_for_user(user.id)

    def get_owned_or_404(self, chat_id: str, user: User) -> ChatSession:
        chat = self.chats.get_owned(chat_id, user.id)
        if chat is None:
            raise NotFoundError("Chat not found.")
        return chat

    def get_detail_or_404(self, chat_id: str, user: User) -> ChatSession:
        chat = self.chats.get_owned_with_messages(chat_id, user.id)
        if chat is None:
            raise NotFoundError("Chat not found.")
        return chat

    def create(self, user: User, payload: ChatCreateRequest) -> ChatSession:
        project_id: str | None = None
        if payload.project_id:
            # Validated so a chat cannot be filed into someone else's project.
            if self.projects.get_owned(payload.project_id, user.id) is None:
                raise NotFoundError("Project not found.")
            project_id = payload.project_id

        chat = self.chats.create(user.id, payload.title or "New Chat", project_id)
        self.session.commit()
        self.session.refresh(chat)
        return chat

    def update(
        self, chat_id: str, user: User, payload: ChatUpdateRequest, fields_set: set[str]
    ) -> ChatSession:
        chat = self.get_owned_or_404(chat_id, user)

        if "title" in fields_set and payload.title:
            chat.title = payload.title

        if "project_id" in fields_set:
            if payload.project_id is None:
                chat.project_id = None
            else:
                if self.projects.get_owned(payload.project_id, user.id) is None:
                    raise NotFoundError("Project not found.")
                chat.project_id = payload.project_id

        chat.updated_at = utcnow()
        self.session.commit()
        self.session.refresh(chat)
        return chat

    def delete(self, chat_id: str, user: User) -> None:
        chat = self.get_detail_or_404(chat_id, user)
        self._delete_attachment_files(chat)
        self.chats.delete(chat)
        self.session.commit()

    def rewind_to_message(self, chat_id: str, message_id: str, user: User) -> int:
        """Drop a message and everything after it, backing the edit-and-resend flow."""
        chat = self.get_owned_or_404(chat_id, user)
        pivot = self.chats.get_message(message_id, chat.id)
        if pivot is None:
            raise NotFoundError("Message not found.")

        removed = self.chats.delete_from_message_onward(chat.id, pivot)
        chat.updated_at = utcnow()
        self.session.commit()
        return removed

    def _delete_attachment_files(self, chat: ChatSession) -> None:
        """Unlink uploaded files before the rows cascade away, so deleting a
        chat does not leave orphaned bytes on disk forever."""
        root = Path(settings.UPLOAD_DIR)
        for message in chat.messages:
            for attachment in message.attachments:
                if attachment.storage_path:
                    (root / attachment.storage_path).unlink(missing_ok=True)

    # --------------------------------------------------------------- Quota

    def _assert_within_budget(self, user_id: str) -> None:
        if settings.DAILY_TOKEN_BUDGET <= 0:
            return
        today = utcnow().astimezone(UTC).date()
        used = self.usage.tokens_used_on(user_id, today)
        if used >= settings.DAILY_TOKEN_BUDGET:
            raise QuotaExceededError(
                "You have reached today's usage limit. It resets at midnight UTC."
            )

    def _record_usage(self, user_id: str, tokens: int) -> None:
        today = utcnow().astimezone(UTC).date()
        self.usage.increment(user_id, today, tokens)

    # ------------------------------------------------------- Turn pipeline

    def _authorize_turn(
        self, chat_id: str, user: User, attachment_ids: list[str]
    ) -> tuple[ChatSession, list[Attachment]]:
        chat = self.get_owned_or_404(chat_id, user)
        self._assert_within_budget(user.id)

        attachments = self.attachments.list_pending_owned(attachment_ids, user.id)
        if len(attachments) != len(set(attachment_ids)):
            raise NotFoundError("One or more attachments are unavailable.")
        return chat, attachments

    def _persist_user_turn(
        self,
        chat: ChatSession,
        user: User,
        content: str,
        attachments: list[Attachment],
        sources: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> TurnPlan:
        is_first_turn = not self.chats.recent_context(chat.id, 1)

        message = self.chats.add_message(
            chat_id=chat.id,
            role=MessageRole.USER,
            content=content,
            sources=sources or None,
        )
        self.attachments.bind_to_message([a.id for a in attachments], message.id)

        if is_first_turn and chat.title in ("", "New Chat"):
            chat.title = prompt_builder.derive_title(content or attachments[0].filename)
        chat.updated_at = utcnow()

        # Committed before the model is called so a dropped connection or a
        # provider outage still leaves the user's message in their history.
        self.session.commit()

        context = self.chats.recent_context(chat.id, settings.CHAT_CONTEXT_WINDOW)
        prompt = prompt_builder.build_prompt(context)

        cache_key = None
        cached_text = None
        cached_tokens = 0
        if prompt_builder.is_cacheable(prompt):
            cache_key = prompt_builder.build_cache_key(
                user.id, self.ai.model, temperature, max_tokens, prompt
            )
            hit = self.cache.get_fresh(cache_key)
            if hit is not None:
                cached_text = hit.response_text
                cached_tokens = hit.total_tokens

        return TurnPlan(
            chat_id=chat.id,
            prompt=prompt,
            user_message_id=message.id,
            chat_title=chat.title,
            cache_key=cache_key,
            cached_text=cached_text,
            cached_tokens=cached_tokens,
            sources=sources,
        )

    def _persist_assistant_turn(
        self,
        chat_id: str,
        user_id: str,
        text: str,
        tokens: int,
        cache_key: str | None,
        store_in_cache: bool,
    ) -> dict:
        chat = self.session.get(ChatSession, chat_id)
        if chat is None:
            return {}

        message = self.chats.add_message(
            chat_id=chat_id,
            role=MessageRole.ASSISTANT,
            content=text,
            token_count=tokens,
        )
        chat.total_tokens += tokens
        chat.updated_at = utcnow()
        self._record_usage(user_id, tokens)

        if store_in_cache and cache_key and text:
            self.cache.put(cache_key, text, tokens, settings.RESPONSE_CACHE_TTL_SECONDS)

        self.session.commit()
        return {
            "message_id": message.id,
            "tokens": tokens,
            "chat_total_tokens": chat.total_tokens,
        }

    async def _resolve_sources(self, query: str, enabled: bool) -> list[dict]:
        if not enabled or not query.strip():
            return []
        results = await self.search.search(query)
        return [result.model_dump() for result in results]

    async def begin_turn(
        self, chat_id: str, user: User, payload: SendMessageRequest
    ) -> TurnPlan:
        """Authorize, optionally search, and persist the user's message.

        Runs before the response starts so ownership, quota and attachment
        failures surface as ordinary HTTP errors. Database work is pushed to the
        threadpool because this coroutine shares the event loop with every other
        in-flight request.
        """
        chat, attachments = await run_in_threadpool(
            self._authorize_turn, chat_id, user, payload.attachment_ids
        )
        sources = await self._resolve_sources(payload.content, payload.web_search)
        return await run_in_threadpool(
            self._persist_user_turn,
            chat,
            user,
            payload.content.strip(),
            attachments,
            sources,
            payload.temperature,
            payload.max_tokens,
        )

    async def stream_plan(
        self, plan: TurnPlan, user: User, payload: SendMessageRequest
    ) -> AsyncIterator[dict]:
        """Emit transport-neutral events for a prepared turn."""
        yield {
            "type": "start",
            "chat_id": plan.chat_id,
            "user_message_id": plan.user_message_id,
            "title": plan.chat_title,
            "sources": plan.sources,
        }

        accumulated: list[str] = []
        reported_tokens: int | None = None

        try:
            if plan.cached_text is not None:
                for index in range(0, len(plan.cached_text), _CACHE_REPLAY_CHUNK):
                    piece = plan.cached_text[index : index + _CACHE_REPLAY_CHUNK]
                    accumulated.append(piece)
                    yield {"type": "delta", "text": piece}
                reported_tokens = plan.cached_tokens
            else:
                async for chunk in self.ai.stream_completion(
                    plan.prompt, payload.temperature, payload.max_tokens
                ):
                    if chunk.usage_tokens is not None:
                        reported_tokens = chunk.usage_tokens
                    if chunk.delta:
                        accumulated.append(chunk.delta)
                        yield {"type": "delta", "text": chunk.delta}
        except UpstreamServiceError as exc:
            # Keep whatever was generated so the user does not lose a long,
            # partially streamed answer to a transient provider failure.
            partial = "".join(accumulated)
            if partial:
                await run_in_threadpool(
                    self._persist_assistant_turn,
                    plan.chat_id,
                    user.id,
                    partial,
                    prompt_builder.estimate_tokens(partial),
                    plan.cache_key,
                    False,
                )
            yield {"type": "error", "message": exc.message}
            return

        text = "".join(accumulated)
        tokens = (
            reported_tokens
            if reported_tokens is not None
            else prompt_builder.estimate_tokens(text)
        )
        result = await run_in_threadpool(
            self._persist_assistant_turn,
            plan.chat_id,
            user.id,
            text,
            tokens,
            plan.cache_key,
            plan.cached_text is None,
        )
        yield {"type": "done", **result}

    async def begin_ephemeral(
        self, user: User, payload: EphemeralMessageRequest
    ) -> tuple[list[dict], list[dict]]:
        """Temporary chat: nothing is written to the transcript, but the daily
        budget still applies so temp mode is not a free bypass."""
        await run_in_threadpool(self._assert_within_budget, user.id)
        sources = await self._resolve_sources(
            payload.messages[-1].content, payload.web_search
        )
        prompt = prompt_builder.build_ephemeral_prompt(
            [(turn.role, turn.content) for turn in payload.messages], sources
        )
        return prompt, sources

    async def stream_ephemeral(
        self,
        prompt: list[dict],
        sources: list[dict],
        user: User,
        payload: EphemeralMessageRequest,
    ) -> AsyncIterator[dict]:
        yield {"type": "start", "chat_id": None, "sources": sources}

        accumulated: list[str] = []
        reported_tokens: int | None = None
        try:
            async for chunk in self.ai.stream_completion(
                prompt, payload.temperature, payload.max_tokens
            ):
                if chunk.usage_tokens is not None:
                    reported_tokens = chunk.usage_tokens
                if chunk.delta:
                    accumulated.append(chunk.delta)
                    yield {"type": "delta", "text": chunk.delta}
        except UpstreamServiceError as exc:
            yield {"type": "error", "message": exc.message}
            return

        text = "".join(accumulated)
        tokens = reported_tokens if reported_tokens is not None else (
            prompt_builder.estimate_tokens(text)
        )
        await run_in_threadpool(self._record_usage_committed, user.id, tokens)
        yield {"type": "done", "tokens": tokens}

    def _record_usage_committed(self, user_id: str, tokens: int) -> None:
        self._record_usage(user_id, tokens)
        self.session.commit()
