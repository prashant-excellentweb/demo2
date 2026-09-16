import json
import logging
from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


def _encode(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


async def _wrap(events: AsyncIterator[dict]) -> AsyncIterator[str]:
    try:
        async for event in events:
            yield _encode(event)
    except Exception:
        # Headers are already on the wire, so a late failure can only be
        # reported inside the stream.
        logger.exception("Streaming response failed")
        yield _encode({"type": "error", "message": "The response failed unexpectedly."})


def sse_response(events: AsyncIterator[dict]) -> StreamingResponse:
    return StreamingResponse(
        _wrap(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # Tells nginx not to buffer the response, which would otherwise
            # defeat streaming entirely behind a reverse proxy.
            "X-Accel-Buffering": "no",
        },
    )
