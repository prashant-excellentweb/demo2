from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

INSECURE_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "production"] = "development"

    SECRET_KEY: str = INSECURE_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)

    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'chatgpt.db'}"
    SQL_ECHO: bool = False

    AI_PROVIDER: Literal["openai", "groq"] = "groq"
    OPENAI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"
    # Groq rotates its catalogue and returns 404 for retired names, so this
    # default goes stale; `GET /openai/v1/models` lists what a key can use.
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    AI_REQUEST_TIMEOUT_SECONDS: float = 120.0

    # Number of most recent messages replayed to the model as context.
    CHAT_CONTEXT_WINDOW: int = Field(default=20, ge=2, le=200)
    # Server-enforced daily token budget per user. 0 disables the limit.
    DAILY_TOKEN_BUDGET: int = Field(default=200_000, ge=0)
    RESPONSE_CACHE_TTL_SECONDS: int = Field(default=86_400, ge=0)

    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    UPLOAD_DIR: Path = BASE_DIR / "var" / "uploads"
    # Text extracted from an uploaded document is truncated to this many chars
    # before it is handed to the model, to bound prompt cost.
    MAX_DOCUMENT_CONTEXT_CHARS: int = 8_000

    WEB_SEARCH_TIMEOUT_SECONDS: float = 10.0
    WEB_SEARCH_MAX_RESULTS: int = Field(default=5, ge=1, le=20)

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Directory containing the built React bundle; served in production.
    FRONTEND_DIST_DIR: Path = BASE_DIR / "frontend" / "dist"

    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _validate_runtime_safety(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == INSECURE_SECRET or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a random value of at least 32 "
                    "characters when ENVIRONMENT=production."
                )
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "SQLite is not supported in production. Point DATABASE_URL at "
                    "PostgreSQL so concurrent writes and connection pooling work."
                )

        if self.AI_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai.")
        if self.AI_PROVIDER == "groq" and not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required when AI_PROVIDER=groq.")

        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def ai_model(self) -> str:
        return self.OPENAI_MODEL if self.AI_PROVIDER == "openai" else self.GROQ_MODEL

    @property
    def ai_api_key(self) -> str | None:
        return self.OPENAI_API_KEY if self.AI_PROVIDER == "openai" else self.GROQ_API_KEY

    @property
    def ai_base_url(self) -> str | None:
        return None if self.AI_PROVIDER == "openai" else "https://api.groq.com/openai/v1"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
