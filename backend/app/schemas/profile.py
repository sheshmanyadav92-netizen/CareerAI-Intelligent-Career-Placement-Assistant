from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    education: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=200)
    branch: str | None = Field(default=None, max_length=100)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    skills: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    experience_level: Literal["entry", "mid", "senior", "lead"] | None = None

    @field_validator("skills", "preferred_roles")
    @classmethod
    def validate_string_lists(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            cleaned.append(text)
        return cleaned


class ProfileUpdate(ProfileBase):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    education: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=200)
    branch: str | None = Field(default=None, max_length=100)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    skills: list[str] | None = Field(default=None)
    preferred_roles: list[str] | None = Field(default=None)
    experience_level: Literal["entry", "mid", "senior", "lead"] | None = None


class ProfileResponse(ProfileBase):
    user_id: int
