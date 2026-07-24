from __future__ import annotations

from decimal import Decimal


def calculate_position_update(
    *,
    old_quantity: Decimal,
    old_average: Decimal | None,
    signed_fill: Decimal,
    fill_price: Decimal,
) -> tuple[Decimal, Decimal | None, Decimal]:
    """Apply one signed fill and return quantity, average price and realized PnL."""

    if old_quantity == 0 or old_quantity * signed_fill > 0:
        new_quantity = old_quantity + signed_fill
        old_notional = abs(old_quantity) * (old_average or Decimal("0"))
        new_notional = abs(signed_fill) * fill_price
        new_average = (old_notional + new_notional) / abs(new_quantity)
        return new_quantity, new_average, Decimal("0")

    closing_quantity = min(abs(old_quantity), abs(signed_fill))
    direction = Decimal("1") if old_quantity > 0 else Decimal("-1")
    realized_pnl = closing_quantity * (fill_price - (old_average or fill_price)) * direction
    new_quantity = old_quantity + signed_fill

    if new_quantity == 0:
        return new_quantity, None, realized_pnl
    if old_quantity * new_quantity > 0:
        return new_quantity, old_average, realized_pnl
    return new_quantity, fill_price, realized_pnl
