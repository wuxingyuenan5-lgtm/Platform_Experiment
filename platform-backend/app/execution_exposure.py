from __future__ import annotations

from decimal import Decimal

from app.database import connection


def calculate_residual_exposure(batch_id: str) -> tuple[Decimal, str, str]:
    """Return unmatched directional exposure as notional, currency and quality.

    Price differences between two fully offset legs are strategy spread PnL, not
    residual directional exposure. The risk quantity is therefore netted first
    in base-asset / quantity-unit space and translated to notional only after
    unmatched contract delta remains.
    """
    with connection() as db:
        legs = db.execute(
            """
            SELECT l.role, l.side, l.quantity, l.price, l.order_id,
                   i.base_currency, i.quantity_unit, i.settle_currency,
                   cs.contract_multiplier
            FROM execution_batch_legs l
            JOIN instruments i ON i.id = l.instrument_id
            JOIN contract_specifications cs ON cs.instrument_id = l.instrument_id
            WHERE l.batch_id = ? AND l.status = 'filled'
              AND cs.effective_from = (
                  SELECT MAX(cs2.effective_from)
                  FROM contract_specifications cs2
                  WHERE cs2.instrument_id = l.instrument_id
              )
            ORDER BY l.sequence
            """,
            (batch_id,),
        ).fetchall()

        exposure_by_unit: dict[tuple[str, str], Decimal] = {}
        reference_price_by_unit: dict[tuple[str, str], Decimal] = {}
        settlement_currencies: set[str] = set()

        for leg in legs:
            fill_rows = []
            if leg["order_id"] is not None:
                fill_rows = db.execute(
                    """
                    SELECT quantity, price
                    FROM fills
                    WHERE order_id = ?
                    ORDER BY occurred_at
                    """,
                    (leg["order_id"],),
                ).fetchall()

            multiplier = Decimal(leg["contract_multiplier"])
            if fill_rows:
                exposure_quantity = sum(
                    Decimal(fill["quantity"]) * multiplier for fill in fill_rows
                )
                reference_price = max(Decimal(fill["price"]) for fill in fill_rows)
            elif leg["price"] is not None:
                exposure_quantity = Decimal(leg["quantity"]) * multiplier
                reference_price = Decimal(leg["price"])
            else:
                return Decimal("0"), "UNKNOWN", "incomplete"

            if leg["side"] == "sell":
                exposure_quantity = -exposure_quantity

            unit_key = (leg["base_currency"], leg["quantity_unit"])
            exposure_by_unit[unit_key] = (
                exposure_by_unit.get(unit_key, Decimal("0")) + exposure_quantity
            )
            reference_price_by_unit[unit_key] = max(
                reference_price_by_unit.get(unit_key, Decimal("0")),
                reference_price,
            )
            settlement_currencies.add(leg["settle_currency"])

    nonzero_exposures = {
        unit_key: exposure
        for unit_key, exposure in exposure_by_unit.items()
        if exposure != 0
    }
    if not nonzero_exposures:
        return Decimal("0"), next(iter(settlement_currencies), "UNKNOWN"), "complete"

    residual = sum(
        abs(exposure) * reference_price_by_unit[unit_key]
        for unit_key, exposure in nonzero_exposures.items()
    )
    if len(nonzero_exposures) == 1 and len(settlement_currencies) == 1:
        return residual, next(iter(settlement_currencies)), "complete"
    return residual, "MIXED", "incomplete"
