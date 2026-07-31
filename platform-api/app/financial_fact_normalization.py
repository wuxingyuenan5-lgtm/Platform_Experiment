from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TypedDict

from fastapi import HTTPException

from app.financial_fact_schemas import TRADE_FACT_TYPES, CreateFinancialFactRequest

MONETARY_FACT_TYPES = {"funding", "swap", "fee", "balance", "fx"}


class NormalizedFinancialFact(TypedDict):
    fact_type: str
    source: str
    external_id: str
    strategy_instance_id: str
    account_id: str | None
    instrument_id: str | None
    side: str | None
    quantity: str | None
    quantity_unit: str | None
    price: str | None
    contract_multiplier: str | None
    amount: str | None
    currency: str | None
    base_currency: str
    fx_rate_to_base: str | None
    converted_amount: str | None
    available_balance: str | None
    occurred_at: str
    payload_json: str
    data_quality_state: str


@dataclass(frozen=True)
class FinancialFactNormalizationContext:
    base_currency: str
    settle_currency: str | None = None
    quantity_unit: str | None = None
    contract_multiplier: Decimal | None = None


def utc_iso(value: datetime | None) -> str:
    moment = value or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat()


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def normalize_financial_fact(
    request: CreateFinancialFactRequest,
    context: FinancialFactNormalizationContext,
) -> NormalizedFinancialFact:
    currency = request.currency.upper() if request.currency else None
    quantity_unit = None
    contract_multiplier = None
    if request.fact_type in TRADE_FACT_TYPES:
        if (
            context.settle_currency is None
            or context.quantity_unit is None
            or context.contract_multiplier is None
        ):
            raise HTTPException(status_code=422, detail="Trade fact instrument is unavailable")
        if currency is not None and currency != context.settle_currency:
            raise HTTPException(
                status_code=422,
                detail="Trade fact currency must match instrument settlement currency",
            )
        currency = context.settle_currency
        quantity_unit = context.quantity_unit
        contract_multiplier = context.contract_multiplier

    amount = request.amount
    fx_rate = request.fx_rate_to_base
    converted_amount = None
    data_quality_state = "complete"
    if request.fact_type in MONETARY_FACT_TYPES:
        if amount is None or currency is None:
            raise HTTPException(status_code=422, detail="Monetary fact is incomplete")
        if currency == context.base_currency:
            fx_rate = Decimal("1")
            converted_amount = amount
        elif fx_rate is not None:
            converted_amount = amount * fx_rate
        else:
            data_quality_state = "incomplete"
    elif (
        request.fact_type in TRADE_FACT_TYPES
        and currency != context.base_currency
        and fx_rate is None
    ):
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
        "base_currency": context.base_currency,
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


def normalized_content_hash(normalized: Mapping[str, str | None]) -> str:
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
