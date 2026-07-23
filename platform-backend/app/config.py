from decimal import Decimal
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

    # Authentication is permissive only in non-live development. A live process
    # must use api_key mode with SHA-256 token hashes; raw tokens never belong in
    # settings, source control, logs, database rows, or API responses.
    auth_mode: str = "development"
    auth_credentials_json: str = "[]"
    development_user_id: str = "development-user"
    development_roles: str = "admin"

    # Platform LiveTradingSession is a separate authorization boundary from the
    # Runtime live-write gate. Zero absolute limits keep all live sessions blocked.
    require_live_trading_session: bool = True
    live_session_absolute_max_order_notional: Decimal = Decimal("0")
    live_session_absolute_max_daily_notional: Decimal = Decimal("0")

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def development_role_list(self) -> list[str]:
        return [role.strip() for role in self.development_roles.split(",") if role.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
