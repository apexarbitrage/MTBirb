from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mtbirb:mtbirb@localhost:5432/mtbirb"
    ebird_api_key: str = ""
    weather_user_agent: str = "mtbirb (set WEATHER_USER_AGENT in .env)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
