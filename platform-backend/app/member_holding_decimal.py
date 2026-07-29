from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

_DECIMAL_PATTERN = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_MAX_INTEGER_DIGITS = 24
_MAX_FRACTION_DIGITS = 18


class HoldingDecimalError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class HoldingCalculation:
    market_value: Decimal | None
    cumulative_return: Decimal | None
    return_rate: Decimal | None


def parse_non_negative_decimal(value: str, *, field: str) -> Decimal:
    if not isinstance(value, str) or not _DECIMAL_PATTERN.fullmatch(value):
        raise HoldingDecimalError(
            f"{field} must be a non-negative plain decimal string without exponent notation"
        )
    integer_part, _, fraction_part = value.partition(".")
    if len(integer_part) > _MAX_INTEGER_DIGITS:
        raise HoldingDecimalError(f"{field} has too many integer digits")
    if len(fraction_part) > _MAX_FRACTION_DIGITS:
        raise HoldingDecimalError(f"{field} has too many fractional digits")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise HoldingDecimalError(f"{field} is invalid") from exc
    if not parsed.is_finite() or parsed < 0:
        raise HoldingDecimalError(f"{field} must be finite and non-negative")
    return parsed


def canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise HoldingDecimalError("calculated decimal must be finite")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def calculate_holding(
    *,
    share_quantity: Decimal,
    cumulative_invested: Decimal,
    unit_nav: Decimal | None,
) -> HoldingCalculation:
    if unit_nav is None:
        return HoldingCalculation(
            market_value=None,
            cumulative_return=None,
            return_rate=None,
        )
    with localcontext() as context:
        context.prec = 50
        market_value = share_quantity * unit_nav
        cumulative_return = market_value - cumulative_invested
        return_rate = (
            cumulative_return / cumulative_invested
            if cumulative_invested != Decimal("0")
            else None
        )
    return HoldingCalculation(
        market_value=market_value,
        cumulative_return=cumulative_return,
        return_rate=return_rate,
    )
