"""Student profile schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

_STRING_FIELDS = ["college", "degree", "branch", "target_role"]


class ProfileFields(BaseModel):
    college: str | None = Field(default=None, max_length=255)
    degree: str | None = Field(default=None, max_length=120)
    branch: str | None = Field(default=None, max_length=120)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    target_role: str | None = Field(default=None, max_length=120)

    @field_validator(*_STRING_FIELDS)
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ProfileUpdate(ProfileFields):
    """All fields optional so the client can send partial updates."""


class ProfilePublic(ProfileFields):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
