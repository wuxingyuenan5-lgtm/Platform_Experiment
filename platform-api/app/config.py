from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLATFORM_API_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VG_",
        env_file=str(PLATFORM_API_ROOT / ".env"),
        extra="ignore",
    )

    app_name: str = "Platform API"
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

    # Browser users use opaque, server-side sessions. These are security defaults,
    # not user-editable business settings. Production cookies are configured by the
    # response writer and must remain Secure, HttpOnly, SameSite=Lax and host-only.
    browser_sessions_enabled: bool = True
    session_cookie_name: str = "vg_session"
    session_absolute_ttl_minutes: int = 720
    session_idle_ttl_minutes: int = 30
    session_recent_reauth_minutes: int = 10
    session_last_seen_write_minutes: int = 5
    session_max_active_per_user: int = 5
    password_reset_ticket_ttl_minutes: int = 30
    login_failure_limit: int = 5
    login_lock_minutes: int = 15

    # Public endpoint limits are a bounded application safeguard. The production
    # reverse proxy must enforce equivalent or stricter distributed limits.
    public_auth_rate_window_seconds: int = 60
    public_login_rate_limit: int = 20
    public_registration_rate_limit: int = 5
    public_password_reset_rate_limit: int = 10
    public_rate_limit_max_keys: int = 10_000

    # User avatars are application data outside the repository. Uploaded bytes are
    # decoded, bounded and re-encoded before an opaque key is stored in the database.
    avatar_data_directory: str = "./data/avatars"
    avatar_max_bytes: int = 2 * 1024 * 1024
    avatar_max_pixels: int = 20_000_000
    avatar_output_size: int = 512

    # Member holdings are a customer-reporting read model, not formal accounting.
    # A missing available NAV remains unavailable; an older NAV is explicitly stale.
    fund_nav_stale_after_hours: int = 36

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

    @field_validator(
        "database_path",
        "avatar_data_directory",
        "runtime_journal_path",
        "operations_backup_root",
        "operations_restore_root",
        mode="before",
    )
    @classmethod
    def resolve_local_paths_from_platform_api_root(cls, value: str) -> str:
        path = Path(str(value)).expanduser()
        if path.is_absolute():
            return str(path)
        return str((PLATFORM_API_ROOT / path).resolve())

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def development_role_list(self) -> list[str]:
        return [role.strip() for role in self.development_roles.split(",") if role.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
