"""Environment-driven settings: ANTHROPIC_API_KEY present -> real LLM calls,
absent -> mock fallback (DECISIONS.md D4 — LLM integration & prompt design).
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Typed, validated environment settings, loaded once at import time."""

    anthropic_api_key: str | None = None

    class Config:
        """Pydantic-settings config: read values from .env if present."""

        env_file = ".env"


settings = Settings()
