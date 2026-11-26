"""Auth-related request/response schemas with strict validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import BCRYPT_MAX_BYTES


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=BCRYPT_MAX_BYTES)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty")
        return cleaned

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError("Password must be at most 72 bytes")
        if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
            raise ValueError("Password must contain at least one letter and one number")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=BCRYPT_MAX_BYTES)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic
