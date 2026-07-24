from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import Row
from uuid import uuid4

from app import financial_fact_repository as repository
from app.financial_fact_normalization import decimal_text, utc_iso
from app.financial_fact_schemas import (
    TRADE_FACT_TYPES,
    FinancialProjectionRebuildResponse,
    FormalNavSnapshotResponse,
)


class InvalidCapitalBaseError(ValueError):
    """Raised when formal NAV cannot use the configured strategy capital base."""


class NoActiveAccountBindingsError(ValueError):
    """Raised when formal NAV has no active strategy accounts to value."""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def optional_decimal(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def conversion_rate(row: Row) -> Decimal | None:
    if row["currency"] == row["base_currency"]:
        return Decimal("1")
    return optional_decimal(row["fx_rate_to_base"])


def calculate_position_update(
    *,
    old_quantity: Decimal,
    old_average: Decimal | None,
    signed_fill: Decimal,
    fill_price: Decimal,
) -> tuple[Decimal, Decimal | None, Decimal]:
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


def rebuild_account_instrument_projection(
    strategy_instance_id: str,
    account_id: str,
    instrument_id: str,
) -> None:
    repository.ensure_schema()
    if not account_id or not instrument_id:
        return
    facts = repository.list_projection_fact_rows(
        strategy_instance_id,
        account_id,
        instrument_id,
    )
    if not facts:
        return

    base_currency = facts[0]["base_currency"]
    quantity_unit = next(
        (row["quantity_unit"] for row in facts if row["quantity_unit"] is not None),
        "unknown",
    )
    old_quantity = Decimal("0")
    old_average: Decimal | None = None
    trading_pnl = Decimal("0")
    funding_pnl = Decimal("0")
    swap_pnl = Decimal("0")
    fee_pnl = Decimal("0")
    fx_pnl = Decimal("0")
    incomplete = False
    has_trade = False

    for row in facts:
        fact_type = row["fact_type"]
        if fact_type in TRADE_FACT_TYPES:
            has_trade = True
            signed_fill = Decimal(row["quantity"])
            if row["side"] == "sell":
                signed_fill = -signed_fill
            old_quantity, old_average, realized_native = calculate_position_update(
                old_quantity=old_quantity,
                old_average=old_average,
                signed_fill=signed_fill,
                fill_price=Decimal(row["price"]),
            )
            realized_native *= Decimal(row["contract_multiplier"])
            rate = conversion_rate(row)
            if rate is None:
                incomplete = True
            else:
                trading_pnl += realized_native * rate
            continue

        converted = optional_decimal(row["converted_amount"])
        if converted is None:
            incomplete = True
            continue
        if fact_type == "funding":
            funding_pnl += converted
        elif fact_type == "swap":
            swap_pnl += converted
        elif fact_type == "fee":
            fee_pnl += converted
        elif fact_type == "fx":
            fx_pnl += converted

    quality = "incomplete" if incomplete else "complete"
    total_pnl = trading_pnl + funding_pnl + swap_pnl + fee_pnl + fx_pnl
    updated_at = facts[-1]["occurred_at"]
    repository.save_formal_projection(
        strategy_instance_id=strategy_instance_id,
        account_id=account_id,
        instrument_id=instrument_id,
        has_trade=has_trade,
        net_quantity=decimal_text(old_quantity),
        average_price=decimal_text(old_average) if old_average is not None else None,
        quantity_unit=quantity_unit,
        currency=base_currency,
        trading_pnl=decimal_text(trading_pnl),
        funding_pnl=decimal_text(funding_pnl),
        swap_pnl=decimal_text(swap_pnl),
        fee_pnl=decimal_text(fee_pnl),
        fx_pnl=decimal_text(fx_pnl),
        total_pnl=decimal_text(total_pnl),
        fact_count=len(facts),
        data_quality_state=quality,
        updated_at=updated_at,
    )


def rebuild_strategy_financials(
    strategy_instance_id: str,
) -> FinancialProjectionRebuildResponse:
    repository.ensure_schema()
    fact_count, pairs = repository.prepare_strategy_rebuild(strategy_instance_id)

    for pair in pairs:
        rebuild_account_instrument_projection(
            strategy_instance_id,
            pair["account_id"],
            pair["instrument_id"],
        )

    completed_at_text = now_iso()
    completed_at = datetime.fromisoformat(completed_at_text)
    repository.record_projection_rebuild_audit(
        audit_event_id=str(uuid4()),
        strategy_instance_id=strategy_instance_id,
        details_json=json.dumps(
            {"rebuiltPairCount": len(pairs), "factCount": fact_count},
            sort_keys=True,
        ),
        created_at=completed_at_text,
    )
    return FinancialProjectionRebuildResponse(
        strategyInstanceId=strategy_instance_id,
        rebuiltPairCount=len(pairs),
        factCount=fact_count,
        completedAt=completed_at,
    )


def run_formal_nav_snapshot(
    strategy_instance_id: str,
    *,
    capital_base: Decimal | None,
    base_currency: str,
    valuation_time: datetime | None = None,
) -> FormalNavSnapshotResponse:
    repository.ensure_schema()
    if capital_base is None or capital_base <= 0:
        raise InvalidCapitalBaseError("Strategy instance has no valid capital base")
    valuation_iso = utc_iso(valuation_time)

    accounts = repository.list_active_account_rows(strategy_instance_id)
    if not accounts:
        raise NoActiveAccountBindingsError("Strategy has no active account bindings")

    account_ids = [account["account_id"] for account in accounts]
    balance_rows = repository.load_latest_balance_rows(
        strategy_instance_id,
        account_ids,
        valuation_iso,
    )
    equity = Decimal("0")
    included = 0
    missing: list[str] = []
    for account_id in account_ids:
        row = balance_rows[account_id]
        if row is None or row["converted_amount"] is None:
            missing.append(account_id)
            continue
        equity += Decimal(row["converted_amount"])
        included += 1

    required = len(accounts)
    quality = "complete" if included == required else ("partial" if included else "incomplete")
    equity_value = equity if included else None
    nav = equity / capital_base if included else None
    snapshot_id = str(uuid4())
    created_at = now_iso()
    return repository.store_formal_nav_snapshot(
        snapshot_id=snapshot_id,
        audit_event_id=str(uuid4()),
        strategy_instance_id=strategy_instance_id,
        valuation_time=valuation_iso,
        equity=decimal_text(equity_value) if equity_value is not None else None,
        capital_base=decimal_text(capital_base),
        nav=decimal_text(nav) if nav is not None else None,
        currency=base_currency,
        data_quality_state=quality,
        required_account_count=required,
        included_account_count=included,
        missing_account_ids_json=json.dumps(missing, sort_keys=True),
        audit_details_json=json.dumps(
            {
                "valuationTime": valuation_iso,
                "requiredAccountCount": required,
                "includedAccountCount": included,
                "missingAccountIds": missing,
                "dataQualityState": quality,
            },
            sort_keys=True,
        ),
        created_at=created_at,
    )


__all__ = [
    "InvalidCapitalBaseError",
    "NoActiveAccountBindingsError",
    "calculate_position_update",
    "conversion_rate",
    "optional_decimal",
    "rebuild_account_instrument_projection",
    "rebuild_strategy_financials",
    "run_formal_nav_snapshot",
]
