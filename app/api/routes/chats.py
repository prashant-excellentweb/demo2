from fastapi import APIRouter, Response, status

from app.api.deps import ChatServiceDep, CurrentUser
from app.api.sse import sse_response
from app.schemas.chat import (
    ChatCreateRequest,
    ChatDetailRead,
    ChatSummaryRead,
    ChatUpdateRequest,
    EphemeralMessageRequest,
    SendMessageRequest,
)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=list[ChatSummaryRead])
def list_chats(user: CurrentUser, service: ChatServiceDep) -> list[ChatSummaryRead]:
    """Sidebar feed: metadata only, so transcripts and image bytes stay out of it."""
    return [
        ChatSummaryRead.model_validate(summary) for summary in service.list_summaries(user)
    ]


@router.post("", response_model=ChatDetailRead, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreateRequest, user: CurrentUser, service: ChatServiceDep
) -> ChatDetailRead:
    return ChatDetailRead.model_validate(service.create(user, payload))


@router.get("/{chat_id}", response_model=ChatDetailRead)
def read_chat(chat_id: str, user: CurrentUser, service: ChatServiceDep) -> ChatDetailRead:
    return ChatDetailRead.model_validate(service.get_detail_or_404(chat_id, user))


@router.patch("/{chat_id}", response_model=ChatDetailRead)
def update_chat(
    chat_id: str,
    payload: ChatUpdateRequest,
    user: CurrentUser,
    service: ChatServiceDep,
) -> ChatDetailRead:
    # `exclude_unset` distinguishes "leave the folder alone" from "unfile it".
    fields_set = payload.model_dump(exclude_unset=True).keys()
    chat = service.update(chat_id, user, payload, set(fields_set))
    return ChatDetailRead.model_validate(service.get_detail_or_404(chat.id, user))


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: str, user: CurrentUser, service: ChatServiceDep) -> None:
    service.delete(chat_id, user)


@router.delete("/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def rewind_chat(
    chat_id: str, message_id: str, user: CurrentUser, service: ChatServiceDep
) -> None:
    """Delete a message and all later ones, so the user can edit and resend."""
    service.rewind_to_message(chat_id, message_id, user)


@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: str,
    payload: SendMessageRequest,
    user: CurrentUser,
    service: ChatServiceDep,
) -> Response:
    """Append one user message and stream the reply as server-sent events.

    Only the new message is accepted; prior turns are read from the database,
    so the transcript cannot be rewritten by the client.
    """
    plan = await service.begin_turn(chat_id, user, payload)
    return sse_response(service.stream_plan(plan, user, payload))


ephemeral_router = APIRouter(prefix="/ephemeral-chat", tags=["chats"])


@ephemeral_router.post("/messages")
async def send_ephemeral_message(
    payload: EphemeralMessageRequest,
    user: CurrentUser,
    service: ChatServiceDep,
) -> Response:
    """Temporary chat. Nothing is stored, but usage is still metered."""
    prompt, sources = await service.begin_ephemeral(user, payload)
    return sse_response(service.stream_ephemeral(prompt, sources, user, payload))
