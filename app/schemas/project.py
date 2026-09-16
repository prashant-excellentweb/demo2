from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectWriteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Project name cannot be blank.")
        return cleaned

    @field_validator("description")
    @classmethod
    def _clean_description(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
