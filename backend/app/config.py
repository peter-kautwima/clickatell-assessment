"""Environment-driven settings: ANTHROPIC_API_KEY present -> real LLM calls,
absent -> mock fallback (DECISIONS.md D4 — LLM integration & prompt design).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchored to this file's location, NOT the process working directory:
# pydantic-settings resolves a bare ".env" relative to wherever uvicorn was
# launched, and README documents two equivalent launch directories (repo root
# and backend/) — started from the root, a bare ".env" silently skipped
# backend/.env, so the DECISIONS.md D4 (LLM integration & prompt design) key
# toggle never saw a configured key.
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """Typed, validated environment settings, loaded once at import time."""

    # SettingsConfigDict, not the deprecated class-based `Config`: the class
    # form emits PydanticDeprecatedSince20 on pydantic-settings 2.x, which
    # surfaces once the test suite imports this module (CLAUDE.md rule 11(d) —
    # warnings sweep). Behaviour is identical: read values from .env if present.
    model_config = SettingsConfigDict(env_file=_ENV_FILE)

    anthropic_api_key: str | None = None


settings = Settings()
