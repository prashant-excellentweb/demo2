from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import MIN_PASSWORD_LENGTH


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str | None
    created_at: datetime


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    current_password: str | None = Field(default=None, max_length=256)
    new_password: str | None = Field(default=None, max_length=256)

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )
        return value

    @field_validator("display_name")
    @classmethod
    def _clean_display_name(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class DailyUsageRead(BaseModel):
    tokens_used: int
    daily_budget: int
