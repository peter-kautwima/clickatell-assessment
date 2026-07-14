"""Application settings, loaded from environment variables and backend/.env.

A present ANTHROPIC_API_KEY selects live LLM calls; absent, the service uses
the mock. The key toggle and mock/live design: DECISIONS.md D4.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from this file's location, not the current working directory:
# the app can be started from the repo root or from backend/, and a bare
# ".env" would only be found from one of them.
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """Typed settings, loaded once at import time."""

    # SettingsConfigDict, not the class-based Config: the class form is
    # deprecated in pydantic-settings 2.x and warns on import.
    model_config = SettingsConfigDict(env_file=_ENV_FILE)

    anthropic_api_key: str | None = None


settings = Settings()
