from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.cross_spread_market import _build_mt5_snapshot, _extract_swap_value


class FakeMt5MarketData:
    ORDER_TYPE_BUY = 0

    def __init__(self) -> None:
        self.initialize_args: tuple[object, ...] | None = None
        self.initialize_kwargs: dict[str, object] | None = None
        self.login_args: tuple[object, ...] | None = None
        self.login_kwargs: dict[str, object] | None = None
        self.shutdown_called = False

    def initialize(self, *args, **kwargs):
        self.initialize_args = args
        self.initialize_kwargs = kwargs
        return True

    def login(self, *args, **kwargs):
        self.login_args = args
        self.login_kwargs = kwargs
        return True

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=4040.1, ask=4040.4, last=4040.2)

    def symbol_info(self, symbol):
        return SimpleNamespace(
            swap_long=-78.29,
            swap_short=29.49,
            swap_mode=1,
            swap_rollover3days=3,
            trade_contract_size=100.0,
        )

    def positions_get(self, **kwargs):
        return ()

    def shutdown(self):
        self.shutdown_called = True


def test_direct_mt5_snapshot_exposes_swap_values(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_LOGIN", "123456")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_PASSWORD", "not-exposed")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_SERVER", "Broker-Demo")
    mt5 = FakeMt5MarketData()

    snapshot = _build_mt5_snapshot(
        symbol="XAUUSD+",
        credential_ref="secret://environment/mt5-demo-001",
        terminal_path="C:/MT5/terminal64.exe",
        bridge_file_path=None,
        timeout_seconds=8.0,
        mt5_module=mt5,
    )

    assert snapshot.status == "available"
    assert snapshot.quote is not None
    assert snapshot.quote.bid == Decimal("4040.1")
    assert _extract_swap_value(snapshot.reason, "swapLong") == Decimal("-78.29")
    assert _extract_swap_value(snapshot.reason, "swapShort") == Decimal("29.49")
    assert snapshot.reason is not None
    assert "swapMode=1" in snapshot.reason
    assert "swapRollover3Days=3" in snapshot.reason
    assert "contractSize=100.0" in snapshot.reason
    assert mt5.initialize_args == ("C:/MT5/terminal64.exe",)
    assert mt5.initialize_kwargs == {"timeout": 8000}
    assert mt5.login_args == (123456,)
    assert mt5.login_kwargs == {
        "password": "not-exposed",
        "server": "Broker-Demo",
        "timeout": 8000,
    }
    assert mt5.shutdown_called is True
