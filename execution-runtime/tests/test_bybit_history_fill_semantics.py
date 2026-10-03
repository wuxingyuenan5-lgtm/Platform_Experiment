from types import SimpleNamespace

import pytest

from app.bybit_acceptance_adapter import BybitAcceptanceAdapter


@pytest.mark.parametrize("kind", ["Funding", "Settlement", "BustTrade"])
def test_non_trade_executions_are_not_fills(kind):
    adapter = object.__new__(BybitAcceptanceAdapter)
    assert adapter._fill_snapshot({"execType": kind}, "account") is None


def test_trade_execution_keeps_native_quantity_and_identity(monkeypatch):
    monkeypatch.setattr("app.bybit_acceptance_adapter.get_order_route", lambda **_: None)
    adapter = object.__new__(BybitAcceptanceAdapter)
    adapter.settings = SimpleNamespace(
        bybit_instruments={"XAUTUSDT": "gold"}, bybit_settle_coin="USDT"
    )
    fill = adapter._fill_snapshot(
        dict(
            execType="Trade",
            orderId="order",
            execId="fill",
            symbol="XAUTUSDT",
            side="Sell",
            execQty="0.039",
            execPrice="4123.9",
            execTime="1790611929478",
        ),
        "account",
    )
    assert str(fill.quantity) == "0.039"
    assert fill.external_fill_id == "fill" and fill.side == "sell"
