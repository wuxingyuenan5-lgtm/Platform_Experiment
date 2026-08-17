import os
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MT5_BRIDGE_FILENAME = "variable_global_mt5_bridge.json"


def default_mt5_bridge_file_path() -> str:
    """Return a portable bridge path without binding the repository to one workstation."""

    appdata = os.environ.get("APPDATA")
    if appdata:
        return str(
            Path(appdata)
            / "MetaQuotes"
            / "Terminal"
            / "Common"
            / "Files"
            / MT5_BRIDGE_FILENAME
        )
    return str(Path("data") / MT5_BRIDGE_FILENAME)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VG_RUNTIME_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Platform Execution Runtime"
    environment: str = "development"
    journal_path: str = "./data/runtime_journal.db"
    gateway_name: str = "fake"
    credential_refs: str = (
        "secret://environment/bybit-live-001,"
        "secret://environment/mt5-live-001"
    )

    live_write_enabled: bool = False
    live_account_allowlist: str = ""
    live_strategy_allowlist: str = ""
    live_symbol_allowlist: str = ""
    live_max_order_notional: Decimal = Decimal("0")
    live_max_daily_notional: Decimal = Decimal("0")

    # Temporary real-money acceptance controls. They do not authorize writes;
    # the independent live-write gate and allowlists remain mandatory.
    live_acceptance_max_order_quantity: Decimal = Decimal("1")
    live_acceptance_max_positions_per_symbol: int = 1

    bybit_credential_ref: str = "secret://environment/bybit-live-001"
    bybit_account_ids: str = ""
    bybit_instrument_map: str = ""
    bybit_category: str = "linear"
    bybit_settle_coin: str = "USDT"
    bybit_contract_symbol: str = "XAUTUSDT"
    bybit_demo_mode: bool = False
    bybit_recv_window: int = 20000
    bybit_timestamp_offset_ms: int = 0
    bybit_check_timeout_seconds: float = 8.0
    bybit_fill_confirmation_timeout_seconds: float = 5.0
    bybit_fill_confirmation_poll_seconds: float = 0.1
    bybit_postonly_chase_enabled: bool = False
    bybit_postonly_chase_ttl_seconds: float = 15.0
    bybit_postonly_chase_event_timeout_seconds: float = 1.0
    bybit_postonly_chase_min_amend_ticks: int = 1
    bybit_postonly_chase_max_mutations: int = 5
    bybit_postonly_chase_cooldown_seconds: float = 1.0
    bybit_postonly_chase_rest_reconcile_seconds: float = 3.0

    mt5_credential_ref: str = "secret://environment/mt5-live-001"
    mt5_account_ids: str = ""
    mt5_instrument_map: str = ""
    mt5_symbol: str = "XAUUSD+"
    mt5_terminal_path: str | None = None
    mt5_bridge_file_path: str = Field(default_factory=default_mt5_bridge_file_path)
    mt5_check_timeout_seconds: float = 5.0
    mt5_magic_number: int = 5604001
    mt5_deviation_points: int = 20
    mt5_history_lookback_days: int = 7

    @property
    def configured_credential_refs(self) -> list[str]:
        return self._csv(self.credential_refs)

    @property
    def allowed_live_accounts(self) -> set[str]:
        return set(self._csv(self.live_account_allowlist))

    @property
    def allowed_live_strategies(self) -> set[str]:
        return set(self._csv(self.live_strategy_allowlist))

    @property
    def allowed_live_symbols(self) -> set[str]:
        return {item.upper() for item in self._csv(self.live_symbol_allowlist)}

    @property
    def bybit_accounts(self) -> set[str]:
        return set(self._csv(self.bybit_account_ids))

    @property
    def mt5_accounts(self) -> set[str]:
        return set(self._csv(self.mt5_account_ids))

    @property
    def bybit_instruments(self) -> dict[str, str]:
        return self._mapping(self.bybit_instrument_map)

    @property
    def mt5_instruments(self) -> dict[str, str]:
        return self._mapping(self.mt5_instrument_map)

    @staticmethod
    def _csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _mapping(value: str) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for item in Settings._csv(value):
            if "=" not in item:
                continue
            symbol, instrument_id = item.split("=", 1)
            symbol = symbol.strip().upper()
            instrument_id = instrument_id.strip()
            if symbol and instrument_id:
                mapping[symbol] = instrument_id
        return mapping


@lru_cache
def get_settings() -> Settings:
    return Settings()
