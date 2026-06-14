from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    database_url: str = "postgresql+asyncpg://tarot:tarot@postgres:5432/tarot"
    telegram_webapp_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
