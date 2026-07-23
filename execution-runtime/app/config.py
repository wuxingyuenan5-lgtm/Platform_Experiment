from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VG_RUNTIME_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Variable-Global Execution Runtime"
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

    bybit_credential_ref: str = "secret://environment/bybit-live-001"
    bybit_account_ids: str = ""
    bybit_instrument_map: str = ""
    bybit_category: str = "linear"
    bybit_settle_coin: str = "USDT"
    bybit_contract_symbol: str = "XAUTUSDT"
    bybit_demo_mode: bool = False
    bybit_recv_window: int = 20000
    bybit_check_timeout_seconds: float = 8.0

    mt5_credential_ref: str = "secret://environment/mt5-live-001"
    mt5_account_ids: str = ""
    mt5_instrument_map: str = ""
    mt5_symbol: str = "XAUUSD+"
    mt5_terminal_path: str | None = None
    mt5_bridge_file_path: str = (
        "C:\\Users\\jiuxi\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files\\"
        "variable_global_mt5_bridge.json"
    )
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
