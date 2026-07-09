from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
