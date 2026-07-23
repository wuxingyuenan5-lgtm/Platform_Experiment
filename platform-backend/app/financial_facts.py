from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from app.config import get_settings
from app.database import connection

FinancialFactType = Literal[
    "external_order",
    "trade_fill",
    "deal",
    "funding",
    "swap",
    "fee",
    "balance",
    "position",
    "fx",
]
PROJECTED_FACT_TYPES = {"trade_fill", "deal", "funding", "swap", "fee", "fx"}
TRADE_FACT_TYPES = {"trade_fill", "deal"}
MONETARY_FACT_TYPES = {"funding", "swap", "fee", "balance", "fx"}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS financial_facts (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT,
    instrument_id TEXT,
    side TEXT,
    quantity TEXT,
    quantity_unit TEXT,
    price TEXT,
    contract_multiplier TEXT,
    amount TEXT,
    currency TEXT,
    base_currency TEXT NOT NULL,
    fx_rate_to_base TEXT,
    converted_amount TEXT,
    available_balance TEXT,
    occurred_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(source, external_id, fact_type, strategy_instance_id),
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(instrument_id) REFERENCES instruments(id)
);

CREATE TABLE IF NOT EXISTS formal_positions (
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    net_quantity TEXT NOT NULL,
    average_price TEXT,
    quantity_unit TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(strategy_instance_id, account_id, instrument_id),
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(instrument_id) REFERENCES instruments(id)
);

CREATE TABLE IF NOT EXISTS formal_pnl_results (
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    trading_pnl TEXT NOT NULL,
    funding_pnl TEXT NOT NULL,
    swap_pnl TEXT NOT NULL,
    fee_pnl TEXT NOT NULL,
    fx_pnl TEXT NOT NULL,
    total_pnl TEXT NOT NULL,
    fact_count INTEGER NOT NULL,
    data_quality_state TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(strategy_instance_id, account_id, instrument_id),
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(instrument_id) REFERENCES instruments(id)
);

CREATE TABLE IF NOT EXISTS formal_strategy_nav_snapshots (
    id TEXT PRIMARY KEY,
    strategy_instance_id TEXT NOT NULL,
    valuation_time TEXT NOT NULL,
    equity TEXT,
    capital_base TEXT NOT NULL,
    nav TEXT,
    currency TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    required_account_count INTEGER NOT NULL,
    included_account_count INTEGER NOT NULL,
    missing_account_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id)
);

CREATE INDEX IF NOT EXISTS idx_financial_facts_strategy_time
ON financial_facts(strategy_instance_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_financial_facts_account_instrument
ON financial_facts(account_id, instrument_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_formal_nav_strategy_time
ON formal_strategy_nav_snapshots(strategy_instance_id, valuation_time);
"""


class CreateFinancialFactRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    fact_type: FinancialFactType = Field(alias="factType")
    source: str = Field(min_length=1, max_length=64)
    external_id: str = Field(alias="externalId", min_length=1, max_length=128)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str | None = Field(default=None, alias="accountId")
    instrument_id: str | None = Field(default=None, alias="instrumentId")
    side: Literal["buy", "sell"] | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=16)
    available_balance: Decimal | None = Field(default=None, alias="availableBalance")
    fx_rate_to_base: Decimal | None = Field(default=None, alias="fxRateToBase", gt=0)
    occurred_at: datetime = Field(alias="occurredAt")
    payload: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_fact_shape(self) -> "CreateFinancialFactRequest":
        if self.fact_type in TRADE_FACT_TYPES:
            if (
                self.account_id is None
                or self.instrument_id is None
                or self.side is None
                or self.quantity is None
                or self.price is None
            ):
                raise ValueError(
                    "Trade facts require account, instrument, side, quantity and price"
                )
        elif self.fact_type in {"funding", "swap", "fee", "fx"}:
            if self.account_id is None or self.instrument_id is None:
                raise ValueError("PnL component facts require account and instrument")
            if self.amount is None or self.currency is None:
                raise ValueError("PnL component facts require amount and currency")
        elif self.fact_type == "balance":
            if self.account_id is None or self.amount is None or self.currency is None:
                raise ValueError("Balance facts require account, amount and currency")
        elif self.fact_type in {"external_order", "position"}:
            if self.account_id is None or self.instrument_id is None:
                raise ValueError("Order and position facts require account and instrument")
        return self


class FinancialFactResponse(BaseModel):
    fact_id: str = Field(alias="factId")
    idempotency_key: str = Field(alias="idempotencyKey")
    fact_type: FinancialFactType = Field(alias="factType")
    source: str
    external_id: str = Field(alias="externalId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str | None = Field(default=None, alias="accountId")
    instrument_id: str | None = Field(default=None, alias="instrumentId")
    side: str | None = None
    quantity: Decimal | None = None
    quantity_unit: str | None = Field(default=None, alias="quantityUnit")
    price: Decimal | None = None
    contract_multiplier: Decimal | None = Field(default=None, alias="contractMultiplier")
    amount: Decimal | None = None
    currency: str | None = None
    base_currency: str = Field(alias="baseCurrency")
    fx_rate_to_base: Decimal | None = Field(default=None, alias="fxRateToBase")
    converted_amount: Decimal | None = Field(default=None, alias="convertedAmount")
    available_balance: Decimal | None = Field(default=None, alias="availableBalance")
    occurred_at: datetime = Field(alias="occurredAt")
    data_quality_state: str = Field(alias="dataQualityState")
    created_at: datetime = Field(alias="createdAt")


class FormalPositionResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    net_quantity: Decimal = Field(alias="netQuantity")
    average_price: Decimal | None = Field(default=None, alias="averagePrice")
    quantity_unit: str = Field(alias="quantityUnit")
    data_quality_state: str = Field(alias="dataQualityState")
    updated_at: datetime = Field(alias="updatedAt")


class FormalPnlResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    currency: str
    trading_pnl: Decimal = Field(alias="tradingPnl")
    funding_pnl: Decimal = Field(alias="fundingPnl")
    swap_pnl: Decimal = Field(alias="swapPnl")
    fee_pnl: Decimal = Field(alias="feePnl")
    fx_pnl: Decimal = Field(alias="fxPnl")
    total_pnl: Decimal = Field(alias="totalPnl")
    fact_count: int = Field(alias="factCount")
    data_quality_state: str = Field(alias="dataQualityState")
    updated_at: datetime = Field(alias="updatedAt")


class FormalNavSnapshotResponse(BaseModel):
    snapshot_id: str = Field(alias="snapshotId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    valuation_time: datetime = Field(alias="valuationTime")
    equity: Decimal | None = None
    capital_base: Decimal = Field(alias="capitalBase")
    nav: Decimal | None = None
    currency: str
    data_quality_state: str = Field(alias="dataQualityState")
    required_account_count: int = Field(alias="requiredAccountCount")
    included_account_count: int = Field(alias="includedAccountCount")
    missing_account_ids: list[str] = Field(alias="missingAccountIds")
    created_at: datetime = Field(alias="createdAt")


class FinancialProjectionRebuildResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    rebuilt_pair_count: int = Field(alias="rebuiltPairCount")
    fact_count: int = Field(alias="factCount")
    completed_at: datetime = Field(alias="completedAt")


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


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
    with connection() as db:
        row = db.execute(
            """
            SELECT si.id, si.status, si.base_currency, si.capital_base, sd.v1_scope
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ?
            """,
            (strategy_instance_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy instance not found")
    if row["status"] != "active" or row["v1_scope"] != "closed_loop":
        raise HTTPException(status_code=422, detail="Strategy instance is not active closed-loop")
    return row


def validate_account_binding(strategy_instance_id: str, account_id: str) -> None:
    with connection() as db:
        row = db.execute(
            """
            SELECT sab.id
            FROM strategy_account_bindings sab
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ?
              AND sab.account_id = ?
              AND sab.status = 'active'
              AND a.status = 'active'
            """,
            (strategy_instance_id, account_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="Account is not actively bound to strategy")


def load_instrument(instrument_id: str):
    with connection() as db:
        row = db.execute(
            """
            SELECT i.id, i.settle_currency, i.quantity_unit, cs.contract_multiplier
            FROM instruments i
            JOIN contract_specifications cs ON cs.instrument_id = i.id
            WHERE i.id = ?
            ORDER BY cs.effective_from DESC
            LIMIT 1
            """,
            (instrument_id,),
        ).fetchone()
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
    ensure_schema()
    normalized = normalize_fact(request)
    content_hash = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with connection() as db:
        existing = db.execute(
            """
            SELECT * FROM financial_facts
            WHERE idempotency_key = ?
               OR (
                    source = ? AND external_id = ? AND fact_type = ?
                    AND strategy_instance_id = ?
               )
            ORDER BY created_at
            LIMIT 1
            """,
            (
                request.idempotency_key,
                request.source,
                request.external_id,
                request.fact_type,
                request.strategy_instance_id,
            ),
        ).fetchone()
        if existing is not None:
            if existing["content_hash"] != content_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Financial fact identity was reused with a different payload",
                )
            return financial_fact_from_row(existing)

        fact_id = str(uuid4())
        created_at = now_iso()
        db.execute(
            """
            INSERT INTO financial_facts (
                id, idempotency_key, content_hash, fact_type, source, external_id,
                strategy_instance_id, account_id, instrument_id, side, quantity,
                quantity_unit, price, contract_multiplier, amount, currency,
                base_currency, fx_rate_to_base, converted_amount, available_balance,
                occurred_at, payload_json, data_quality_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                request.idempotency_key,
                content_hash,
                normalized["fact_type"],
                normalized["source"],
                normalized["external_id"],
                normalized["strategy_instance_id"],
                normalized["account_id"],
                normalized["instrument_id"],
                normalized["side"],
                normalized["quantity"],
                normalized["quantity_unit"],
                normalized["price"],
                normalized["contract_multiplier"],
                normalized["amount"],
                normalized["currency"],
                normalized["base_currency"],
                normalized["fx_rate_to_base"],
                normalized["converted_amount"],
                normalized["available_balance"],
                normalized["occurred_at"],
                normalized["payload_json"],
                normalized["data_quality_state"],
                created_at,
            ),
        )
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "financial_fact_recorded",
                "financial_fact",
                fact_id,
                json.dumps(
                    {
                        "factType": request.fact_type,
                        "strategyInstanceId": request.strategy_instance_id,
                        "source": request.source,
                        "externalId": request.external_id,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                created_at,
            ),
        )
        row = db.execute("SELECT * FROM financial_facts WHERE id = ?", (fact_id,)).fetchone()

    if request.fact_type in PROJECTED_FACT_TYPES:
        rebuild_account_instrument_projection(
            request.strategy_instance_id,
            request.account_id or "",
            request.instrument_id or "",
        )
    return financial_fact_from_row(row)


def list_financial_facts(
    strategy_instance_id: str | None = None,
    fact_type: str | None = None,
    limit: int = 200,
) -> list[FinancialFactResponse]:
    ensure_schema()
    clauses: list[str] = []
    parameters: list[object] = []
    if strategy_instance_id is not None:
        clauses.append("strategy_instance_id = ?")
        parameters.append(strategy_instance_id)
    if fact_type is not None:
        clauses.append("fact_type = ?")
        parameters.append(fact_type)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    parameters.append(limit)
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT * FROM financial_facts
            {where}
            ORDER BY occurred_at DESC, created_at DESC
            LIMIT ?
            """,
            tuple(parameters),
        ).fetchall()
    return [financial_fact_from_row(row) for row in rows]


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
    ensure_schema()
    if not account_id or not instrument_id:
        return
    with connection() as db:
        facts = db.execute(
            """
            SELECT * FROM financial_facts
            WHERE strategy_instance_id = ?
              AND account_id = ?
              AND instrument_id = ?
              AND fact_type IN ('trade_fill', 'deal', 'funding', 'swap', 'fee', 'fx')
            ORDER BY occurred_at, created_at, id
            """,
            (strategy_instance_id, account_id, instrument_id),
        ).fetchall()
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
    with connection() as db:
        if has_trade:
            db.execute(
                """
                INSERT INTO formal_positions (
                    strategy_instance_id, account_id, instrument_id, net_quantity,
                    average_price, quantity_unit, data_quality_state, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(strategy_instance_id, account_id, instrument_id) DO UPDATE SET
                    net_quantity = excluded.net_quantity,
                    average_price = excluded.average_price,
                    quantity_unit = excluded.quantity_unit,
                    data_quality_state = excluded.data_quality_state,
                    updated_at = excluded.updated_at
                """,
                (
                    strategy_instance_id,
                    account_id,
                    instrument_id,
                    decimal_text(old_quantity),
                    decimal_text(old_average) if old_average is not None else None,
                    quantity_unit,
                    quality,
                    updated_at,
                ),
            )
        db.execute(
            """
            INSERT INTO formal_pnl_results (
                strategy_instance_id, account_id, instrument_id, currency,
                trading_pnl, funding_pnl, swap_pnl, fee_pnl, fx_pnl, total_pnl,
                fact_count, data_quality_state, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(strategy_instance_id, account_id, instrument_id) DO UPDATE SET
                currency = excluded.currency,
                trading_pnl = excluded.trading_pnl,
                funding_pnl = excluded.funding_pnl,
                swap_pnl = excluded.swap_pnl,
                fee_pnl = excluded.fee_pnl,
                fx_pnl = excluded.fx_pnl,
                total_pnl = excluded.total_pnl,
                fact_count = excluded.fact_count,
                data_quality_state = excluded.data_quality_state,
                updated_at = excluded.updated_at
            """,
            (
                strategy_instance_id,
                account_id,
                instrument_id,
                base_currency,
                decimal_text(trading_pnl),
                decimal_text(funding_pnl),
                decimal_text(swap_pnl),
                decimal_text(fee_pnl),
                decimal_text(fx_pnl),
                decimal_text(total_pnl),
                len(facts),
                quality,
                updated_at,
            ),
        )


def rebuild_strategy_financials(
    strategy_instance_id: str,
) -> FinancialProjectionRebuildResponse:
    ensure_schema()
    load_strategy(strategy_instance_id)
    with connection() as db:
        fact_count = db.execute(
            "SELECT COUNT(*) AS count FROM financial_facts WHERE strategy_instance_id = ?",
            (strategy_instance_id,),
        ).fetchone()["count"]
        pairs = db.execute(
            """
            SELECT DISTINCT account_id, instrument_id
            FROM financial_facts
            WHERE strategy_instance_id = ?
              AND fact_type IN ('trade_fill', 'deal', 'funding', 'swap', 'fee', 'fx')
              AND account_id IS NOT NULL
              AND instrument_id IS NOT NULL
            """,
            (strategy_instance_id,),
        ).fetchall()
        db.execute(
            "DELETE FROM formal_positions WHERE strategy_instance_id = ?",
            (strategy_instance_id,),
        )
        db.execute(
            "DELETE FROM formal_pnl_results WHERE strategy_instance_id = ?",
            (strategy_instance_id,),
        )

    for pair in pairs:
        rebuild_account_instrument_projection(
            strategy_instance_id,
            pair["account_id"],
            pair["instrument_id"],
        )

    completed_at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "formal_financial_projection_rebuilt",
                "strategy_instance",
                strategy_instance_id,
                json.dumps(
                    {"rebuiltPairCount": len(pairs), "factCount": fact_count},
                    sort_keys=True,
                ),
                completed_at,
            ),
        )
    return FinancialProjectionRebuildResponse(
        strategyInstanceId=strategy_instance_id,
        rebuiltPairCount=len(pairs),
        factCount=fact_count,
        completedAt=completed_at,
    )


def list_formal_pnl(strategy_instance_id: str) -> list[FormalPnlResponse]:
    ensure_schema()
    load_strategy(strategy_instance_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT * FROM formal_pnl_results
            WHERE strategy_instance_id = ?
            ORDER BY account_id, instrument_id
            """,
            (strategy_instance_id,),
        ).fetchall()
    return [formal_pnl_from_row(row) for row in rows]


def list_formal_positions(strategy_instance_id: str) -> list[FormalPositionResponse]:
    ensure_schema()
    load_strategy(strategy_instance_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT * FROM formal_positions
            WHERE strategy_instance_id = ?
            ORDER BY account_id, instrument_id
            """,
            (strategy_instance_id,),
        ).fetchall()
    return [formal_position_from_row(row) for row in rows]


def run_formal_nav_snapshot(
    strategy_instance_id: str,
    valuation_time: datetime | None = None,
) -> FormalNavSnapshotResponse:
    ensure_schema()
    strategy = load_strategy(strategy_instance_id)
    capital_base = optional_decimal(strategy["capital_base"])
    if capital_base is None or capital_base <= 0:
        raise HTTPException(status_code=422, detail="Strategy instance has no valid capital base")
    valuation_iso = utc_iso(valuation_time)

    with connection() as db:
        accounts = db.execute(
            """
            SELECT DISTINCT sab.account_id
            FROM strategy_account_bindings sab
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ?
              AND sab.status = 'active'
              AND a.status = 'active'
            ORDER BY sab.account_id
            """,
            (strategy_instance_id,),
        ).fetchall()
    if not accounts:
        raise HTTPException(status_code=422, detail="Strategy has no active account bindings")

    equity = Decimal("0")
    included = 0
    missing: list[str] = []
    with connection() as db:
        for account in accounts:
            row = db.execute(
                """
                SELECT converted_amount
                FROM financial_facts
                WHERE strategy_instance_id = ?
                  AND account_id = ?
                  AND fact_type = 'balance'
                  AND occurred_at <= ?
                ORDER BY occurred_at DESC, created_at DESC
                LIMIT 1
                """,
                (strategy_instance_id, account["account_id"], valuation_iso),
            ).fetchone()
            if row is None or row["converted_amount"] is None:
                missing.append(account["account_id"])
                continue
            equity += Decimal(row["converted_amount"])
            included += 1

    required = len(accounts)
    quality = "complete" if included == required else ("partial" if included else "incomplete")
    equity_value = equity if included else None
    nav = equity / capital_base if included else None
    snapshot_id = str(uuid4())
    created_at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT INTO formal_strategy_nav_snapshots (
                id, strategy_instance_id, valuation_time, equity, capital_base, nav,
                currency, data_quality_state, required_account_count,
                included_account_count, missing_account_ids_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                strategy_instance_id,
                valuation_iso,
                decimal_text(equity_value) if equity_value is not None else None,
                decimal_text(capital_base),
                decimal_text(nav) if nav is not None else None,
                strategy["base_currency"],
                quality,
                required,
                included,
                json.dumps(missing, sort_keys=True),
                created_at,
            ),
        )
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "formal_nav_snapshot_created",
                "strategy_instance",
                strategy_instance_id,
                json.dumps(
                    {
                        "valuationTime": valuation_iso,
                        "requiredAccountCount": required,
                        "includedAccountCount": included,
                        "missingAccountIds": missing,
                        "dataQualityState": quality,
                    },
                    sort_keys=True,
                ),
                created_at,
            ),
        )
        row = db.execute(
            "SELECT * FROM formal_strategy_nav_snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
    return formal_nav_from_row(row)


def list_formal_nav_snapshots(strategy_instance_id: str) -> list[FormalNavSnapshotResponse]:
    ensure_schema()
    load_strategy(strategy_instance_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT * FROM formal_strategy_nav_snapshots
            WHERE strategy_instance_id = ?
            ORDER BY valuation_time DESC
            """,
            (strategy_instance_id,),
        ).fetchall()
    return [formal_nav_from_row(row) for row in rows]


def financial_fact_from_row(row) -> FinancialFactResponse:
    return FinancialFactResponse(
        factId=row["id"],
        idempotencyKey=row["idempotency_key"],
        factType=row["fact_type"],
        source=row["source"],
        externalId=row["external_id"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        side=row["side"],
        quantity=optional_decimal(row["quantity"]),
        quantityUnit=row["quantity_unit"],
        price=optional_decimal(row["price"]),
        contractMultiplier=optional_decimal(row["contract_multiplier"]),
        amount=optional_decimal(row["amount"]),
        currency=row["currency"],
        baseCurrency=row["base_currency"],
        fxRateToBase=optional_decimal(row["fx_rate_to_base"]),
        convertedAmount=optional_decimal(row["converted_amount"]),
        availableBalance=optional_decimal(row["available_balance"]),
        occurredAt=row["occurred_at"],
        dataQualityState=row["data_quality_state"],
        createdAt=row["created_at"],
    )


def formal_pnl_from_row(row) -> FormalPnlResponse:
    return FormalPnlResponse(
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        currency=row["currency"],
        tradingPnl=Decimal(row["trading_pnl"]),
        fundingPnl=Decimal(row["funding_pnl"]),
        swapPnl=Decimal(row["swap_pnl"]),
        feePnl=Decimal(row["fee_pnl"]),
        fxPnl=Decimal(row["fx_pnl"]),
        totalPnl=Decimal(row["total_pnl"]),
        factCount=row["fact_count"],
        dataQualityState=row["data_quality_state"],
        updatedAt=row["updated_at"],
    )


def formal_position_from_row(row) -> FormalPositionResponse:
    return FormalPositionResponse(
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        netQuantity=Decimal(row["net_quantity"]),
        averagePrice=optional_decimal(row["average_price"]),
        quantityUnit=row["quantity_unit"],
        dataQualityState=row["data_quality_state"],
        updatedAt=row["updated_at"],
    )


def formal_nav_from_row(row) -> FormalNavSnapshotResponse:
    return FormalNavSnapshotResponse(
        snapshotId=row["id"],
        strategyInstanceId=row["strategy_instance_id"],
        valuationTime=row["valuation_time"],
        equity=optional_decimal(row["equity"]),
        capitalBase=Decimal(row["capital_base"]),
        nav=optional_decimal(row["nav"]),
        currency=row["currency"],
        dataQualityState=row["data_quality_state"],
        requiredAccountCount=row["required_account_count"],
        includedAccountCount=row["included_account_count"],
        missingAccountIds=json.loads(row["missing_account_ids_json"]),
        createdAt=row["created_at"],
    )


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
