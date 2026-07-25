from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Literal

from app.cross_spread_order_intent import LegacyMarketAction

LimitPriceDirection = Literal[
    "BUY_BYBIT_SELL_MT5",
    "SELL_BYBIT_BUY_MT5",
]


@dataclass(frozen=True, slots=True)
class CrossSpreadFokPrice:
    direction: LimitPriceDirection
    limit_spread: Decimal
    executable_spread: Decimal
    mt5_reference_price: Decimal
    hedge_reserve: Decimal
    bybit_tick_size: Decimal
    raw_bybit_limit_price: Decimal
    bybit_limit_price: Decimal
    currently_executable: bool


_BUY_BYBIT_ACTIONS: set[LegacyMarketAction] = {"OPEN_LONG", "CLOSE_SHORT"}


def derive_cross_spread_fok_price(
    action: LegacyMarketAction,
    *,
    limit_spread: Decimal,
    bybit_bid: Decimal,
    bybit_ask: Decimal,
    mt5_bid: Decimal,
    mt5_ask: Decimal,
    bybit_tick_size: Decimal,
    hedge_reserve: Decimal,
) -> CrossSpreadFokPrice:
    _validate_quotes(
        bybit_bid=bybit_bid,
        bybit_ask=bybit_ask,
        mt5_bid=mt5_bid,
        mt5_ask=mt5_ask,
    )
    if bybit_tick_size <= 0:
        raise ValueError("Bybit tick size must be positive")
    if hedge_reserve < 0:
        raise ValueError("MT5 hedge reserve cannot be negative")

    if action in _BUY_BYBIT_ACTIONS:
        executable_spread = bybit_ask - mt5_bid
        raw_price = mt5_bid + limit_spread - hedge_reserve
        rounded_price = _round_down_to_tick(raw_price, bybit_tick_size)
        direction: LimitPriceDirection = "BUY_BYBIT_SELL_MT5"
        currently_executable = executable_spread <= limit_spread
        mt5_reference_price = mt5_bid
    else:
        executable_spread = bybit_bid - mt5_ask
        raw_price = mt5_ask + limit_spread + hedge_reserve
        rounded_price = _round_up_to_tick(raw_price, bybit_tick_size)
        direction = "SELL_BYBIT_BUY_MT5"
        currently_executable = executable_spread >= limit_spread
        mt5_reference_price = mt5_ask

    if rounded_price <= 0:
        raise ValueError("Derived Bybit FOK limit price must be positive")

    return CrossSpreadFokPrice(
        direction=direction,
        limit_spread=limit_spread,
        executable_spread=executable_spread,
        mt5_reference_price=mt5_reference_price,
        hedge_reserve=hedge_reserve,
        bybit_tick_size=bybit_tick_size,
        raw_bybit_limit_price=raw_price,
        bybit_limit_price=rounded_price,
        currently_executable=currently_executable,
    )


def _round_down_to_tick(value: Decimal, tick_size: Decimal) -> Decimal:
    ticks = (value / tick_size).to_integral_value(rounding=ROUND_FLOOR)
    return ticks * tick_size


def _round_up_to_tick(value: Decimal, tick_size: Decimal) -> Decimal:
    ticks = (value / tick_size).to_integral_value(rounding=ROUND_CEILING)
    return ticks * tick_size


def _validate_quotes(
    *,
    bybit_bid: Decimal,
    bybit_ask: Decimal,
    mt5_bid: Decimal,
    mt5_ask: Decimal,
) -> None:
    if min(bybit_bid, bybit_ask, mt5_bid, mt5_ask) <= 0:
        raise ValueError("Cross-spread executable quotes must be positive")
    if bybit_bid > bybit_ask:
        raise ValueError("Bybit bid cannot exceed ask")
    if mt5_bid > mt5_ask:
        raise ValueError("MT5 bid cannot exceed ask")
