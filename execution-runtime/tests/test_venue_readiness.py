import time

from app.venue_readiness import check_bybit_contract, check_mt5_symbol


class FakeBybitSession:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.ticker_calls: list[dict[str, str]] = []
        self.wallet_calls: list[dict[str, str]] = []

    def get_tickers(self, *, category: str, symbol: str):
        self.calls.append("ticker")
        self.ticker_calls.append({"category": category, "symbol": symbol})
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": symbol,
                        "bid1Price": "3320.1",
                        "ask1Price": "3320.5",
                    }
                ]
            },
        }

    def get_wallet_balance(self, *, accountType: str):
        self.calls.append("wallet")
        self.wallet_calls.append({"accountType": accountType})
        return {"retCode": 0, "result": {"list": [{"totalEquity": "1000"}]}}


class SlowBybitSession(FakeBybitSession):
    def get_tickers(self, *, category: str, symbol: str):
        time.sleep(0.2)
        return super().get_tickers(category=category, symbol=symbol)


class FakeMt5Module:
    def __init__(self) -> None:
        self.initialized_with = None
        self.shutdown_called = False

    def initialize(self, **kwargs):
        self.initialized_with = kwargs
        return True

    def symbol_info(self, symbol: str):
        return {"name": symbol}

    def shutdown(self) -> None:
        self.shutdown_called = True


class SlowMt5Module(FakeMt5Module):
    def initialize(self, *, login: int, password: str, server: str):
        time.sleep(0.2)
        return True


def test_bybit_contract_readiness_uses_linear_xautusdt_without_exposing_secret(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_API_KEY", "real-key")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_SECRET", "real-secret")
    session = FakeBybitSession()
    factory_calls = []

    result = check_bybit_contract(
        credential_ref="secret://crypto-test-001",
        symbol="XAUTUSDT",
        demo=False,
        session_factory=lambda **kwargs: factory_calls.append(kwargs) or session,
    )

    assert result.status == "available"
    assert result.venue == "bybit"
    assert result.symbol == "XAUTUSDT"
    assert result.market_type == "linear"
    assert factory_calls == [
        {
            "testnet": False,
            "demo": False,
            "recv_window": 20000,
            "api_key": "real-key",
            "api_secret": "real-secret",
        }
    ]
    assert session.wallet_calls == [{"accountType": "UNIFIED"}]
    assert session.ticker_calls == [{"category": "linear", "symbol": "XAUTUSDT"}]
    assert session.calls == ["wallet", "ticker"]
    serialized = result.model_dump_json().lower()
    assert "real-key" not in serialized
    assert "real-secret" not in serialized


def test_bybit_contract_readiness_times_out_without_blocking_runtime(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_API_KEY", "real-key")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_SECRET", "real-secret")

    result = check_bybit_contract(
        credential_ref="secret://crypto-test-001",
        symbol="XAUTUSDT",
        timeout_seconds=0.01,
        session_factory=lambda **_: SlowBybitSession(),
    )

    assert result.status == "timeout"
    assert result.venue == "bybit"


def test_mt5_symbol_readiness_initializes_terminal_and_checks_xauusd_plus(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_API_KEY", "1234567")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_SECRET", "mt5-password")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_PASSPHRASE", "BrokerDemo")
    mt5_module = FakeMt5Module()

    result = check_mt5_symbol(
        credential_ref="secret://mt5-demo-001",
        symbol="XAUUSD+",
        terminal_path="C:\\Program Files\\Bybit MT5 Terminal\\terminal64.exe",
        mt5_module=mt5_module,
    )

    assert result.status == "available"
    assert result.venue == "mt5"
    assert result.symbol == "XAUUSD+"
    assert mt5_module.initialized_with == {
        "login": 1234567,
        "password": "mt5-password",
        "server": "BrokerDemo",
        "path": "C:\\Program Files\\Bybit MT5 Terminal\\terminal64.exe",
    }
    assert mt5_module.shutdown_called is True
    serialized = result.model_dump_json().lower()
    assert "mt5-password" not in serialized


def test_mt5_symbol_readiness_times_out_without_blocking_runtime(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_API_KEY", "1234567")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_SECRET", "mt5-password")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_PASSPHRASE", "BrokerDemo")

    result = check_mt5_symbol(
        credential_ref="secret://mt5-demo-001",
        symbol="XAUUSD+",
        mt5_module=SlowMt5Module(),
        timeout_seconds=0.01,
    )

    assert result.status == "timeout"
    assert result.venue == "mt5"
