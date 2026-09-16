from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.chat import MessageRole
from app.schemas.attachment import AttachmentRead
from app.schemas.search import SearchResult

MAX_MESSAGE_CHARS = 32_000
MAX_ATTACHMENTS_PER_MESSAGE = 10


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: MessageRole
    content: str
    created_at: datetime
    sources: list[SearchResult] | None = None
    attachments: list[AttachmentRead] = Field(default_factory=list)


class ChatSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    project_id: str | None
    total_tokens: int
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    project_id: str | None
    total_tokens: int
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead]


class ChatCreateRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=200)
    project_id: str | None = None


class ChatUpdateRequest(BaseModel):
    """Both fields are optional; only keys present in the request are applied,
    so `project_id: null` genuinely moves a chat out of its folder."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    project_id: str | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class GenerationOptions(BaseModel):
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, ge=256, le=16_000)


class SendMessageRequest(GenerationOptions):
    content: str = Field(default="", max_length=MAX_MESSAGE_CHARS)
    attachment_ids: list[str] = Field(
        default_factory=list, max_length=MAX_ATTACHMENTS_PER_MESSAGE
    )
    web_search: bool = False

    @model_validator(mode="after")
    def _require_content_or_attachment(self) -> "SendMessageRequest":
        if not self.content.strip() and not self.attachment_ids:
            raise ValueError("Provide a message or at least one attachment.")
        return self


class EphemeralTurn(BaseModel):
    """A turn in a temporary chat.

    Temporary conversations are never persisted, so the transcript necessarily
    round-trips through the client. The role is constrained to a closed set and
    the server still supplies the system prompt, so a client cannot impersonate
    a system instruction.
    """

    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_MESSAGE_CHARS)


class EphemeralMessageRequest(GenerationOptions):
    messages: list[EphemeralTurn] = Field(min_length=1, max_length=40)
    web_search: bool = False

    @model_validator(mode="after")
    def _require_trailing_user_turn(self) -> "EphemeralMessageRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The final message must come from the user.")
        return self
