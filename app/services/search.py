import logging

import httpx

from app.core.config import settings
from app.schemas.search import SearchResult

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.duckduckgo.com/"


class WebSearchService:
    """DuckDuckGo Instant Answer lookups.

    Uses httpx rather than `requests`: the previous implementation made a
    blocking call inside an async endpoint, which parked the whole event loop
    for the duration of the request and stalled every other user.
    """

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    async def search(self, query: str) -> list[SearchResult]:
        payload = await self._fetch(query)
        if payload is None:
            return []
        return self._parse(payload)

    async def _fetch(self, query: str) -> dict | None:
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        headers = {"User-Agent": "BuddyChat/2.0 (+https://localhost)"}
        try:
            if self._client is not None:
                response = await self._client.get(_ENDPOINT, params=params, headers=headers)
            else:
                async with httpx.AsyncClient(
                    timeout=settings.WEB_SEARCH_TIMEOUT_SECONDS
                ) as client:
                    response = await client.get(_ENDPOINT, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # A failed search degrades to answering from general knowledge; it is
            # never fatal to the conversation.
            logger.warning("Web search failed for %r: %s", query, exc)
            return None

    def _parse(self, payload: dict) -> list[SearchResult]:
        collected: list[SearchResult] = []

        abstract = (payload.get("AbstractText") or "").strip()
        if abstract:
            collected.append(
                SearchResult(
                    title=payload.get("Heading") or "Summary",
                    url=payload.get("AbstractURL") or "",
                    snippet=abstract[:500],
                )
            )

        for result in payload.get("Results") or []:
            if isinstance(result, dict):
                collected.append(self._to_result(result))

        for topic in payload.get("RelatedTopics") or []:
            if not isinstance(topic, dict):
                continue
            if topic.get("FirstURL"):
                collected.append(self._to_result(topic))
            for subtopic in topic.get("Topics") or []:
                if isinstance(subtopic, dict) and subtopic.get("FirstURL"):
                    collected.append(self._to_result(subtopic))

        return self._dedupe(collected)

    @staticmethod
    def _to_result(raw: dict) -> SearchResult:
        text = (raw.get("Text") or "").strip()
        return SearchResult(
            title=text.split(" - ")[0] or "Result",
            url=raw.get("FirstURL") or "",
            snippet=text,
        )

    @staticmethod
    def _dedupe(results: list[SearchResult]) -> list[SearchResult]:
        seen: set[str] = set()
        unique: list[SearchResult] = []
        for result in results:
            if not result.url or result.url in seen:
                continue
            seen.add(result.url)
            unique.append(result)
            if len(unique) >= settings.WEB_SEARCH_MAX_RESULTS:
                break
        return unique
