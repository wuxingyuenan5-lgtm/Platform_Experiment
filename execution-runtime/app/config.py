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
    credential_refs: str = "secret://crypto-test-001,secret://mt5-demo-001"
    bybit_contract_symbol: str = "XAUTUSDT"
    bybit_demo_mode: bool = False
    bybit_recv_window: int = 20000
    bybit_check_timeout_seconds: float = 8.0
    mt5_symbol: str = "XAUUSD+"
    mt5_terminal_path: str | None = None
    mt5_bridge_file_path: str = (
        "C:\\Users\\jiuxi\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files\\variable_global_mt5_bridge.json"
    )
    mt5_check_timeout_seconds: float = 5.0

    @property
    def configured_credential_refs(self) -> list[str]:
        return [item.strip() for item in self.credential_refs.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
