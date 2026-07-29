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
    cors_origins: str = "http://127.0.0.1:4373,http://localhost:4373"
    live_trading_enabled: bool = False
    default_trading_environment: str = "simulation"

    # The market-exit monitor is a separate capability gate. It remains off unless
    # operations explicitly enables it on a controlled host; Live Write gates still apply.
    cross_spread_exit_monitor_enabled: bool = False
    cross_spread_exit_monitor_interval_seconds: float = 1.0

    # Synthetic FOK pricing reserves a fixed MT5 price amount before deriving the
    # Bybit limit. Zero is the safe default until the controlled host sets evidence-based
    # broker slippage. The value must remain non-negative.
    cross_spread_limit_hedge_reserve_price: Decimal = Decimal("0")

    # Temporary real-money acceptance controls. They remain enforced until a
    # separate Issue/PR reviews evidence from Issue #39 and explicitly changes them.
    cross_spread_acceptance_max_quantity_oz: Decimal = Decimal("1")
    cross_spread_acceptance_max_active_plans: int = 1
    cross_spread_definitive_failure_rollback_enabled: bool = True
    cross_spread_position_verification_required: bool = True

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

    # Production operations use local, explicit filesystem roots. The backup and
    # restore roots must never point at the active Platform or Runtime data paths.
    runtime_journal_path: str = "../execution-runtime/data/runtime_journal.db"
    operations_backup_root: str = "./data/backups"
    operations_restore_root: str = "./data/restore-drills"
    operations_alert_default_owner: str = "operations"
    operations_eod_overdue_grace_minutes: int = 0

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def development_role_list(self) -> list[str]:
        return [role.strip() for role in self.development_roles.split(",") if role.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
