import re

from pydantic import BaseModel, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
MIN_PASSWORD_LENGTH = 8


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)
    display_name: str | None = Field(default=None, max_length=128)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.match(value):
            raise ValueError(
                "Username may only contain letters, numbers, dots, dashes and underscores."
            )
        return value

    @field_validator("display_name")
    @classmethod
    def _clean_display_name(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None
