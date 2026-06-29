import re
from openai import AsyncOpenAI
import config

if config.AI_PROVIDER == "openai":
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    DEFAULT_MODEL = config.OPENAI_MODEL
else:
    client = AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=config.GROQ_API_KEY,
    )
    DEFAULT_MODEL = config.GROQ_MODEL


SYSTEM_PROMPT = """You are **Buddy**, a capable AI assistant modeled after ChatGPT.

Respond clearly, accurately, and in a natural tone. Adapt structure to the question:
- Simple questions → concise direct answers
- Complex topics → short headings, bullets, or steps when helpful

When images are attached, describe what you see and answer from the visual context.
When web search results are provided, cite sources as Markdown links [Title](URL).
Do not invent facts when sources are given — prefer the provided context.

Safety: decline harmful, illegal, or explicit requests briefly and offer a constructive alternative.
Avoid filler phrases like "Let me know if you need more help."
"""


def build_api_messages(messages: list) -> list:
    """Convert chat messages to OpenAI-compatible format, including vision content."""
    result = []
    image_pattern = re.compile(r"\[IMAGE: ([^\]]+)\]\nData: (data:[^\n]+)")

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "user" and isinstance(content, str) and image_pattern.search(content):
            parts = []
            last_end = 0
            for match in image_pattern.finditer(content):
                before_text = content[last_end : match.start()].strip()
                if before_text:
                    parts.append({"type": "text", "text": before_text})
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": match.group(2)},
                })
                last_end = match.end()
            remaining = content[last_end:].strip()
            if remaining:
                parts.append({"type": "text", "text": remaining})
            result.append({"role": role, "content": parts})
        else:
            result.append({"role": role, "content": content})

    return result


async def generate_chat_response(
    messages: list, max_tokens: int = 4000, temperature: float = 0.7
) -> dict:
    """Call the configured AI provider and return reply + token usage."""
    try:
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + build_api_messages(
            messages
        )

        response = await client.chat.completions.create(
            messages=api_messages,
            model=DEFAULT_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            "reply": response.choices[0].message.content or "",
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
    except Exception as e:
        print(f"API Error: {e}")
        return {
            "reply": "I'm having trouble connecting to the AI service. Please check your API key and try again.",
            "total_tokens": 0,
        }
