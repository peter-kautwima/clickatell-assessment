"""Environment-driven settings: ANTHROPIC_API_KEY present -> real LLM calls,
absent -> mock fallback (DECISIONS.md D4 — LLM integration & prompt design).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated environment settings, loaded once at import time."""

    # SettingsConfigDict, not the deprecated class-based `Config`: the class
    # form emits PydanticDeprecatedSince20 on pydantic-settings 2.x, which
    # surfaces once the test suite imports this module (CLAUDE.md rule 11(d) —
    # warnings sweep). Behaviour is identical: read values from .env if present.
    model_config = SettingsConfigDict(env_file=".env")

    anthropic_api_key: str | None = None


settings = Settings()
