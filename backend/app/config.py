"""Environment-driven settings: ANTHROPIC_API_KEY present -> real LLM calls,
absent -> mock fallback (DECISIONS.md D4 — LLM integration & prompt design).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated environment settings, loaded once at import time."""

    # SettingsConfigDict, not the class-based `class Config`: the latter is
    # deprecated in pydantic v2 and warns on import.
    model_config = SettingsConfigDict(env_file=".env")

    anthropic_api_key: str | None = None


settings = Settings()
