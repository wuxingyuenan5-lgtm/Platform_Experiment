from decimal import Decimal

import pytest

from app.cross_spread_limit_policy import derive_cross_spread_fok_price


@pytest.mark.parametrize("action", ["OPEN_LONG", "CLOSE_SHORT"])
def test_buy_bybit_direction_uses_maximum_spread_and_rounds_down(action) -> None:
    result = derive_cross_spread_fok_price(
        action,
        limit_spread=Decimal("-0.73"),
        bybit_bid=Decimal("2500.10"),
        bybit_ask=Decimal("2500.20"),
        mt5_bid=Decimal("2501.00"),
        mt5_ask=Decimal("2501.10"),
        bybit_tick_size=Decimal("0.10"),
        hedge_reserve=Decimal("0.05"),
    )

    assert result.direction == "BUY_BYBIT_SELL_MT5"
    assert result.executable_spread == Decimal("-0.80")
    assert result.raw_bybit_limit_price == Decimal("2500.22")
    assert result.bybit_limit_price == Decimal("2500.20")
    assert result.currently_executable is True
    assert result.bybit_limit_price - (result.mt5_reference_price - result.hedge_reserve) <= Decimal("-0.73")


@pytest.mark.parametrize("action", ["OPEN_SHORT", "CLOSE_LONG"])
def test_sell_bybit_direction_uses_minimum_spread_and_rounds_up(action) -> None:
    result = derive_cross_spread_fok_price(
        action,
        limit_spread=Decimal("-1.03"),
        bybit_bid=Decimal("2500.10"),
        bybit_ask=Decimal("2500.20"),
        mt5_bid=Decimal("2501.00"),
        mt5_ask=Decimal("2501.10"),
        bybit_tick_size=Decimal("0.10"),
        hedge_reserve=Decimal("0.05"),
    )

    assert result.direction == "SELL_BYBIT_BUY_MT5"
    assert result.executable_spread == Decimal("-1.00")
    assert result.raw_bybit_limit_price == Decimal("2500.12")
    assert result.bybit_limit_price == Decimal("2500.20")
    assert result.currently_executable is True
    assert result.bybit_limit_price - (result.mt5_reference_price + result.hedge_reserve) >= Decimal("-1.03")


def test_non_executable_spread_is_reported_without_weakening_limit() -> None:
    result = derive_cross_spread_fok_price(
        "OPEN_LONG",
        limit_spread=Decimal("-1.00"),
        bybit_bid=Decimal("2500.10"),
        bybit_ask=Decimal("2500.20"),
        mt5_bid=Decimal("2501.00"),
        mt5_ask=Decimal("2501.10"),
        bybit_tick_size=Decimal("0.10"),
        hedge_reserve=Decimal("0"),
    )

    assert result.executable_spread == Decimal("-0.80")
    assert result.currently_executable is False
    assert result.bybit_limit_price == Decimal("2500.00")


@pytest.mark.parametrize(
    ("tick_size", "reserve", "message"),
    [
        (Decimal("0"), Decimal("0"), "tick size"),
        (Decimal("0.1"), Decimal("-0.01"), "reserve"),
    ],
)
def test_invalid_pricing_inputs_fail_closed(tick_size, reserve, message) -> None:
    with pytest.raises(ValueError, match=message):
        derive_cross_spread_fok_price(
            "OPEN_LONG",
            limit_spread=Decimal("0"),
            bybit_bid=Decimal("2500"),
            bybit_ask=Decimal("2500.1"),
            mt5_bid=Decimal("2501"),
            mt5_ask=Decimal("2501.1"),
            bybit_tick_size=tick_size,
            hedge_reserve=reserve,
        )
