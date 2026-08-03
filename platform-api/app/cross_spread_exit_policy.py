from __future__ import annotations

from decimal import Decimal
from typing import Literal

SpreadDirection = Literal["LONG_SPREAD", "SHORT_SPREAD"]
ExitTriggerReason = Literal["take_profit", "stop_loss"]


def select_executable_close_spread(
    direction: SpreadDirection,
    *,
    long_spread: Decimal | None,
    short_spread: Decimal | None,
) -> Decimal | None:
    if direction == "LONG_SPREAD":
        return short_spread
    return long_spread


def evaluate_exit_threshold(
    direction: SpreadDirection,
    *,
    close_spread: Decimal,
    take_profit_spread: Decimal,
    stop_loss_spread: Decimal,
) -> ExitTriggerReason | None:
    if direction == "LONG_SPREAD":
        if close_spread >= take_profit_spread:
            return "take_profit"
        if close_spread <= stop_loss_spread:
            return "stop_loss"
        return None

    if close_spread <= take_profit_spread:
        return "take_profit"
    if close_spread >= stop_loss_spread:
        return "stop_loss"
    return None
