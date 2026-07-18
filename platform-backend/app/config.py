from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VG_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Variable-Global Platform Backend"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_path: str = "./data/platform.db"
    runtime_base_url: str = "http://127.0.0.1:8100"
    runtime_timeout_seconds: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
