"""Application configuration.

All settings are loaded from environment variables (and a local .env file).
Pydantic's BaseSettings validates and types everything for us, so if a value
is missing or has the wrong type, the app fails fast with a clear error.
"""

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] is the "backend" directory.
BASE_DIR = Path(__file__).resolve().parents[2]

JWT_ISSUER = "preppilot"
JWT_AUDIENCE = "preppilot-web"


class Settings(BaseSettings):
    # --- App ---
    PROJECT_NAME: str = "Placement Prep API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # --- CORS ---
    # Comma-separated list of allowed frontend origins.
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/placement_prep"
    )

    # --- Auth / JWT ---
    SECRET_KEY: str = "dev-insecure-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- AI (Phase 4: job description analysis) ---
    # Any OpenAI-compatible endpoint works (OpenAI, Groq, OpenRouter, Ollama…).
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TIMEOUT_SECONDS: float = 30.0

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as a clean Python list."""
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        """Accept hosted `postgres://` URLs and normalize them for SQLAlchemy."""
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        prefix = "postgres://"
        if normalized.startswith(prefix):
            return "postgresql://" + normalized[len(prefix) :]
        return normalized

    @field_validator("ENVIRONMENT")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        normalized = value.strip().lower() or "development"
        allowed = {"development", "dev", "test", "testing", "staging", "production", "prod"}
        if normalized not in allowed:
            raise ValueError("ENVIRONMENT must be development, staging or production")
        return normalized

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_token_expiry(cls, value: int) -> int:
        if not 1 <= value <= 1440:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440")
        return value

    @field_validator("LLM_TIMEOUT_SECONDS")
    @classmethod
    def validate_llm_timeout(cls, value: float) -> float:
        if not 1.0 <= value <= 300.0:
            raise ValueError("LLM_TIMEOUT_SECONDS must be between 1 and 300")
        return value

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.ENVIRONMENT in {"staging", "production", "prod"}:
            secret = self.SECRET_KEY.strip().lower()
            weak = {"dev-insecure-change-me", "change-me", "secret", "password"}
            if len(self.SECRET_KEY.strip()) < 32 or secret in weak:
                raise ValueError("A strong SECRET_KEY is required outside development")
            if self.ALGORITHM.upper() != "HS256":
                raise ValueError("Only HS256 is supported for production JWTs")
            if "postgres:postgres@" in self.DATABASE_URL:
                raise ValueError("Default database credentials are not allowed outside development")

        origins = self.cors_origins
        if not origins:
            raise ValueError("BACKEND_CORS_ORIGINS must contain at least one origin")
        for raw in origins:
            parsed = urlparse(raw)
            if "*" in raw or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("BACKEND_CORS_ORIGINS must be explicit http(s) origins")

        if self.LLM_API_KEY.strip():
            parsed = urlparse(self.LLM_BASE_URL)
            local_hosts = {"localhost", "127.0.0.1", "::1"}
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or (parsed.scheme == "http" and parsed.hostname not in local_hosts)
            ):
                raise ValueError("LLM_BASE_URL must be HTTPS except for local development hosts")
        return self

    @property
    def llm_enabled(self) -> bool:
        """True only when a real-looking API key is configured."""
        key = self.LLM_API_KEY.strip()
        if not key:
            return False
        return not key.lower().startswith(("your", "change", "placeholder", "<"))


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (read once, reused everywhere)."""
    return Settings()


settings = get_settings()
