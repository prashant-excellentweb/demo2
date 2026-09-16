from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search import WebSearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def web_search(payload: SearchRequest, user: CurrentUser) -> SearchResponse:
    """Standalone lookup for the composer's manual search action."""
    results = await WebSearchService().search(payload.query)
    return SearchResponse(results=results)
