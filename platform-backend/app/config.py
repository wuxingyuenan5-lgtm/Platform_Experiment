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
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    live_trading_enabled: bool = False
    default_trading_environment: str = "simulation"

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
