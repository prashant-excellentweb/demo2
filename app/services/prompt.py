"""Translation from stored domain objects into provider prompt payloads."""

import base64
import hashlib
import json
from pathlib import Path

from app.core.config import settings
from app.models import Attachment, Message

SYSTEM_PROMPT = """You are **Buddy**, a capable AI assistant.

Respond clearly, accurately, and in a natural tone. Adapt structure to the question:
- Simple questions -> concise direct answers
- Complex topics -> short headings, bullets, or steps when helpful

When images are attached, describe what you see and answer from the visual context.
When web search results are provided, cite sources as Markdown links [Title](URL).
Do not invent facts when sources are given - prefer the provided context.
Format code in fenced blocks with a language tag.

Safety: decline harmful, illegal, or explicit requests briefly and offer a
constructive alternative. Avoid filler phrases like "Let me know if you need
more help."
"""


def _image_data_url(attachment: Attachment) -> str | None:
    """Read an image off disk and inline it for the vision API.

    Images are kept as files and encoded only at prompt time, so the bytes never
    sit inside a database row or a chat-list response.
    """
    if not attachment.storage_path:
        return None
    path = Path(settings.UPLOAD_DIR) / attachment.storage_path
    if not path.is_file():
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{attachment.content_type};base64,{encoded}"


def _document_block(attachment: Attachment) -> str | None:
    if not attachment.text_content:
        return None
    text = attachment.text_content[: settings.MAX_DOCUMENT_CONTEXT_CHARS]
    if len(attachment.text_content) > settings.MAX_DOCUMENT_CONTEXT_CHARS:
        text += "\n... [truncated]"
    return f"Attached file `{attachment.filename}`:\n```\n{text}\n```"


def _sources_block(sources: list | None) -> str | None:
    if not sources:
        return None
    lines = []
    for source in sources:
        title = source.get("title") if isinstance(source, dict) else None
        url = source.get("url") if isinstance(source, dict) else None
        snippet = source.get("snippet") if isinstance(source, dict) else None
        lines.append(f"- [{title or 'Result'}]({url or ''}): {snippet or ''}")
    return "Web search results:\n" + "\n".join(lines)


def build_prompt(messages: list[Message]) -> list[dict]:
    """Render a transcript into OpenAI chat-completions format.

    Multimodal parts are only emitted when a turn actually carries images, since
    text-only providers reject the parts array.
    """
    payload: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    for message in messages:
        text_segments: list[str] = []
        if message.content.strip():
            text_segments.append(message.content)

        images: list[str] = []
        for attachment in message.attachments:
            if attachment.is_image:
                data_url = _image_data_url(attachment)
                if data_url:
                    images.append(data_url)
            else:
                block = _document_block(attachment)
                if block:
                    text_segments.append(block)

        sources = _sources_block(message.sources)
        if sources:
            text_segments.append(sources)

        combined_text = "\n\n".join(text_segments)

        if images:
            parts: list[dict] = []
            if combined_text:
                parts.append({"type": "text", "text": combined_text})
            parts.extend(
                {"type": "image_url", "image_url": {"url": url}} for url in images
            )
            payload.append({"role": message.role.value, "content": parts})
        else:
            payload.append({"role": message.role.value, "content": combined_text})

    return payload


def build_ephemeral_prompt(
    turns: list[tuple[str, str]], sources: list[dict] | None = None
) -> list[dict]:
    """Prompt for a temporary chat, whose transcript is not persisted.

    Roles are already constrained to user/assistant by the request schema, and
    the system instruction is prepended here, so the client cannot inject one.
    """
    payload: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for index, (role, content) in enumerate(turns):
        text = content
        if sources and index == len(turns) - 1:
            block = _sources_block(sources)
            if block:
                text = f"{text}\n\n{block}" if text else block
        payload.append({"role": role, "content": text})
    return payload


def build_cache_key(
    user_id: str, model: str, temperature: float, max_tokens: int, prompt: list[dict]
) -> str:
    """Scoped to the user so one account's answer is never served to another."""
    material = json.dumps(
        {
            "user_id": user_id,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "prompt": prompt,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def is_cacheable(prompt: list[dict]) -> bool:
    """Skip caching multimodal turns: the key would embed whole base64 images."""
    return all(isinstance(entry.get("content"), str) for entry in prompt)


def estimate_tokens(text: str) -> int:
    """Rough fallback for providers that omit usage on streamed responses."""
    return max(1, len(text) // 4)


def derive_title(content: str) -> str:
    cleaned = " ".join(content.split())
    if not cleaned:
        return "New Chat"
    return cleaned[:60] + ("..." if len(cleaned) > 60 else "")
