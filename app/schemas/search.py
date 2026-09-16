from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def _strip_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Search query cannot be blank.")
        return cleaned


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
