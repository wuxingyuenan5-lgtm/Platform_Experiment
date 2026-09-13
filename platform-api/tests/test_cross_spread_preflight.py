from decimal import Decimal

from app.auth import permission_for_request
from app.cross_spread import (
    CrossSpreadLiveSizing,
    prepare_cross_spread_market_command,
)
from app.schemas import CrossSpreadPreflightRequest


def test_cross_spread_preflight_prepares_both_live_legs(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.cross_spread.assert_cross_spread_market_executable", lambda *, is_close: None
    )
    monkeypatch.setattr(
        "app.cross_spread._load_live_cross_spread_sizing",
        lambda: CrossSpreadLiveSizing(
            bybit_account_id="bybit-live-main",
            mt5_account_id="mt5-live-main",
            bybit_min=Decimal("0.001"),
            bybit_step=Decimal("0.001"),
            bybit_max=Decimal("100"),
            mt5_min=Decimal("0.01"),
            mt5_step=Decimal("0.01"),
            mt5_max=Decimal("100"),
            mt5_multiplier=Decimal("100"),
        ),
    )
    monkeypatch.setattr(
        "app.execution_batches._reservation_reference_price",
        lambda **kwargs: Decimal("4400") if kwargs["symbol"] == "XAUTUSDT" else Decimal("4405"),
    )
    monkeypatch.setattr(
        "app.execution_batches._reservation_margin_estimate",
        lambda **kwargs: ("USDT", Decimal("220"))
        if kwargs["symbol"] == "XAUTUSDT"
        else ("USD", Decimal("44.05")),
    )

    result = prepare_cross_spread_market_command(
        CrossSpreadPreflightRequest(action="OPEN_SHORT", quantityOz="1")
    )

    assert result["status"] == "ready"
    assert result["legs"] == [
        {
            "accountId": "bybit-live-main",
            "symbol": "XAUTUSDT",
            "side": "sell",
            "quantity": "1",
            "referencePrice": "4400",
            "reservationCurrency": "USDT",
            "reservationAmount": "220",
        },
        {
            "accountId": "mt5-live-main",
            "symbol": "XAUUSD.s",
            "side": "buy",
            "quantity": "0.01",
            "referencePrice": "4405",
            "reservationCurrency": "USD",
            "reservationAmount": "44.05",
        },
    ]


def test_cross_spread_preflight_is_a_read_permission() -> None:
    assert (
        permission_for_request("POST", "/api/v1/trading/cross-spread/preflight")
        == "platform:read"
    )
