from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app import financial_fact_repository as repository
from app.config import get_settings
from app.financial_fact_schemas import (
    TRADE_FACT_TYPES,
    CreateFinancialFactRequest,
    FinancialFactResponse,
    FinancialFactType,
    FinancialProjectionRebuildResponse,
    FormalNavSnapshotResponse,
    FormalPnlResponse,
    FormalPositionResponse,
)

__all__ = [
    "CreateFinancialFactRequest",
    "FinancialFactResponse",
    "FinancialFactType",
    "FinancialProjectionRebuildResponse",
    "FormalNavSnapshotResponse",
    "FormalPnlResponse",
    "FormalPositionResponse",
]

PROJECTED_FACT_TYPES = {"trade_fill", "deal", "funding", "swap", "fee", "fx"}
MONETARY_FACT_TYPES = {"funding", "swap", "fee", "balance", "fx"}

# Compatibility aliases for callers that previously imported persistence helpers from this module.
ensure_schema = repository.ensure_schema
financial_fact_from_row = repository.financial_fact_from_row
formal_pnl_from_row = repository.formal_pnl_from_row
formal_position_from_row = repository.formal_position_from_row
formal_nav_from_row = repository.formal_nav_from_row


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def utc_iso(value: datetime | None) -> str:
    moment = value or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat()


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def optional_decimal(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def load_strategy(strategy_instance_id: str):
    row = repository.load_strategy_row(strategy_instance_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy instance not found")
    if row["status"] != "active" or row["v1_scope"] != "closed_loop":
        raise HTTPException(status_code=422, detail="Strategy instance is not active closed-loop")
    return row


def validate_account_binding(strategy_instance_id: str, account_id: str) -> None:
    if not repository.has_active_account_binding(strategy_instance_id, account_id):
        raise HTTPException(status_code=403, detail="Account is not actively bound to strategy")


def load_instrument(instrument_id: str):
    row = repository.load_instrument_row(instrument_id)
    if row is None:
        raise HTTPException(
            status_code=422,
            detail="Instrument or contract specification is unavailable",
        )
    return row


def normalize_fact(request: CreateFinancialFactRequest) -> dict[str, str | None]:
    strategy = load_strategy(request.strategy_instance_id)
    base_currency = strategy["base_currency"]
    instrument = None
    if request.account_id is not None:
        validate_account_binding(request.strategy_instance_id, request.account_id)
    if request.instrument_id is not None:
        instrument = load_instrument(request.instrument_id)

    currency = request.currency.upper() if request.currency else None
    quantity_unit = None
    contract_multiplier = None
    if request.fact_type in TRADE_FACT_TYPES:
        if instrument is None:
            raise HTTPException(status_code=422, detail="Trade fact instrument is unavailable")
        settle_currency = instrument["settle_currency"]
        if currency is not None and currency != settle_currency:
            raise HTTPException(
                status_code=422,
                detail="Trade fact currency must match instrument settlement currency",
            )
        currency = settle_currency
        quantity_unit = instrument["quantity_unit"]
        contract_multiplier = Decimal(instrument["contract_multiplier"])

    amount = request.amount
    fx_rate = request.fx_rate_to_base
    converted_amount = None
    data_quality_state = "complete"
    if request.fact_type in MONETARY_FACT_TYPES:
        if amount is None or currency is None:
            raise HTTPException(status_code=422, detail="Monetary fact is incomplete")
        if currency == base_currency:
            fx_rate = Decimal("1")
            converted_amount = amount
        elif fx_rate is not None:
            converted_amount = amount * fx_rate
        else:
            data_quality_state = "incomplete"
    elif request.fact_type in TRADE_FACT_TYPES and currency != base_currency and fx_rate is None:
        data_quality_state = "incomplete"

    return {
        "fact_type": request.fact_type,
        "source": request.source,
        "external_id": request.external_id,
        "strategy_instance_id": request.strategy_instance_id,
        "account_id": request.account_id,
        "instrument_id": request.instrument_id,
        "side": request.side,
        "quantity": decimal_text(request.quantity) if request.quantity is not None else None,
        "quantity_unit": quantity_unit,
        "price": decimal_text(request.price) if request.price is not None else None,
        "contract_multiplier": (
            decimal_text(contract_multiplier) if contract_multiplier is not None else None
        ),
        "amount": decimal_text(amount) if amount is not None else None,
        "currency": currency,
        "base_currency": base_currency,
        "fx_rate_to_base": decimal_text(fx_rate) if fx_rate is not None else None,
        "converted_amount": (
            decimal_text(converted_amount) if converted_amount is not None else None
        ),
        "available_balance": (
            decimal_text(request.available_balance)
            if request.available_balance is not None
            else None
        ),
        "occurred_at": utc_iso(request.occurred_at),
        "payload_json": json.dumps(request.payload, ensure_ascii=False, sort_keys=True),
        "data_quality_state": data_quality_state,
    }


def record_financial_fact(request: CreateFinancialFactRequest) -> FinancialFactResponse:
    repository.ensure_schema()
    normalized = normalize_fact(request)
    content_hash = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    fact_id = str(uuid4())
    created_at = now_iso()
    status, response = repository.store_financial_fact(
        fact_id=fact_id,
        audit_event_id=str(uuid4()),
        idempotency_key=request.idempotency_key,
        content_hash=content_hash,
        source=request.source,
        external_id=request.external_id,
        fact_type=request.fact_type,
        strategy_instance_id=request.strategy_instance_id,
        normalized=normalized,
        audit_details_json=json.dumps(
            {
                "factType": request.fact_type,
                "strategyInstanceId": request.strategy_instance_id,
                "source": request.source,
                "externalId": request.external_id,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        created_at=created_at,
    )
    if status == "conflict":
        raise HTTPException(
            status_code=409,
            detail="Financial fact identity was reused with a different payload",
        )
    if status == "existing":
        return response

    if request.fact_type in PROJECTED_FACT_TYPES:
        rebuild_account_instrument_projection(
            request.strategy_instance_id,
            request.account_id or "",
            request.instrument_id or "",
        )
    return response


def list_financial_facts(
    strategy_instance_id: str | None = None,
    fact_type: str | None = None,
    limit: int = 200,
) -> list[FinancialFactResponse]:
    repository.ensure_schema()
    return repository.list_financial_facts(strategy_instance_id, fact_type, limit)


def conversion_rate(row) -> Decimal | None:
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
    load_strategy(strategy_instance_id)
    fact_count, pairs = repository.prepare_strategy_rebuild(strategy_instance_id)

    for pair in pairs:
        rebuild_account_instrument_projection(
            strategy_instance_id,
            pair["account_id"],
            pair["instrument_id"],
        )

    completed_at = now_iso()
    repository.record_projection_rebuild_audit(
        audit_event_id=str(uuid4()),
        strategy_instance_id=strategy_instance_id,
        details_json=json.dumps(
            {"rebuiltPairCount": len(pairs), "factCount": fact_count},
            sort_keys=True,
        ),
        created_at=completed_at,
    )
    return FinancialProjectionRebuildResponse(
        strategyInstanceId=strategy_instance_id,
        rebuiltPairCount=len(pairs),
        factCount=fact_count,
        completedAt=completed_at,
    )


def list_formal_pnl(strategy_instance_id: str) -> list[FormalPnlResponse]:
    repository.ensure_schema()
    load_strategy(strategy_instance_id)
    return repository.list_formal_pnl(strategy_instance_id)


def list_formal_positions(strategy_instance_id: str) -> list[FormalPositionResponse]:
    repository.ensure_schema()
    load_strategy(strategy_instance_id)
    return repository.list_formal_positions(strategy_instance_id)


def run_formal_nav_snapshot(
    strategy_instance_id: str,
    valuation_time: datetime | None = None,
) -> FormalNavSnapshotResponse:
    repository.ensure_schema()
    strategy = load_strategy(strategy_instance_id)
    capital_base = optional_decimal(strategy["capital_base"])
    if capital_base is None or capital_base <= 0:
        raise HTTPException(status_code=422, detail="Strategy instance has no valid capital base")
    valuation_iso = utc_iso(valuation_time)

    accounts = repository.list_active_account_rows(strategy_instance_id)
    if not accounts:
        raise HTTPException(status_code=422, detail="Strategy has no active account bindings")

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
        currency=strategy["base_currency"],
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


def list_formal_nav_snapshots(strategy_instance_id: str) -> list[FormalNavSnapshotResponse]:
    repository.ensure_schema()
    load_strategy(strategy_instance_id)
    return repository.list_formal_nav_snapshots(strategy_instance_id)


router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/financial-facts",
    response_model=FinancialFactResponse,
    tags=["financial-facts"],
    summary="Record one immutable external financial fact",
)
def create_financial_fact(request: CreateFinancialFactRequest) -> FinancialFactResponse:
    return record_financial_fact(request)


@router.get(
    "/financial-facts",
    response_model=list[FinancialFactResponse],
    tags=["financial-facts"],
)
def get_financial_facts(
    strategy_instance_id: str | None = Query(default=None, alias="strategyInstanceId"),
    fact_type: str | None = Query(default=None, alias="factType"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[FinancialFactResponse]:
    return list_financial_facts(strategy_instance_id, fact_type, limit)


@router.post(
    "/strategies/instances/{strategy_instance_id}/financials/rebuild",
    response_model=FinancialProjectionRebuildResponse,
    tags=["financial-facts"],
)
def rebuild_financials(
    strategy_instance_id: str,
) -> FinancialProjectionRebuildResponse:
    return rebuild_strategy_financials(strategy_instance_id)


@router.get(
    "/strategies/instances/{strategy_instance_id}/formal-pnl",
    response_model=list[FormalPnlResponse],
    tags=["pnl"],
)
def get_formal_pnl(strategy_instance_id: str) -> list[FormalPnlResponse]:
    return list_formal_pnl(strategy_instance_id)


@router.get(
    "/strategies/instances/{strategy_instance_id}/formal-positions",
    response_model=list[FormalPositionResponse],
    tags=["pnl"],
)
def get_formal_positions(strategy_instance_id: str) -> list[FormalPositionResponse]:
    return list_formal_positions(strategy_instance_id)


@router.get(
    "/strategies/instances/{strategy_instance_id}/formal-nav-snapshots",
    response_model=list[FormalNavSnapshotResponse],
    tags=["pnl"],
)
def get_formal_nav_snapshots(
    strategy_instance_id: str,
) -> list[FormalNavSnapshotResponse]:
    return list_formal_nav_snapshots(strategy_instance_id)


@router.post(
    "/strategies/instances/{strategy_instance_id}/formal-nav-snapshots/run",
    response_model=FormalNavSnapshotResponse,
    tags=["pnl"],
)
def run_formal_nav(
    strategy_instance_id: str,
    valuation_time: datetime | None = Query(default=None, alias="valuationTime"),
) -> FormalNavSnapshotResponse:
    return run_formal_nav_snapshot(strategy_instance_id, valuation_time)
