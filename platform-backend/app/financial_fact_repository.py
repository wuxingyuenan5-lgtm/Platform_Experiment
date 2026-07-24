from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal
from sqlite3 import Row
from typing import Literal

from app.database import connection
from app.financial_fact_schemas import (
    FinancialFactResponse,
    FormalNavSnapshotResponse,
    FormalPnlResponse,
    FormalPositionResponse,
)

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

FinancialFactWriteStatus = Literal["created", "existing", "conflict"]


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def load_strategy_row(strategy_instance_id: str) -> Row | None:
    with connection() as db:
        return db.execute(
            """
            SELECT si.id, si.status, si.base_currency, si.capital_base, sd.v1_scope
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ?
            """,
            (strategy_instance_id,),
        ).fetchone()


def has_active_account_binding(strategy_instance_id: str, account_id: str) -> bool:
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
    return row is not None


def load_instrument_row(instrument_id: str) -> Row | None:
    with connection() as db:
        return db.execute(
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


def store_financial_fact(
    *,
    fact_id: str,
    audit_event_id: str,
    idempotency_key: str,
    content_hash: str,
    source: str,
    external_id: str,
    fact_type: str,
    strategy_instance_id: str,
    normalized: Mapping[str, str | None],
    audit_details_json: str,
    created_at: str,
) -> tuple[FinancialFactWriteStatus, FinancialFactResponse]:
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
                idempotency_key,
                source,
                external_id,
                fact_type,
                strategy_instance_id,
            ),
        ).fetchone()
        if existing is not None:
            status: FinancialFactWriteStatus = (
                "existing" if existing["content_hash"] == content_hash else "conflict"
            )
            return status, financial_fact_from_row(existing)

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
                idempotency_key,
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
                audit_event_id,
                "financial_fact_recorded",
                "financial_fact",
                fact_id,
                audit_details_json,
                created_at,
            ),
        )
        row = db.execute("SELECT * FROM financial_facts WHERE id = ?", (fact_id,)).fetchone()

    if row is None:
        raise RuntimeError("Financial fact insert did not return a persisted row")
    return "created", financial_fact_from_row(row)


def list_financial_facts(
    strategy_instance_id: str | None = None,
    fact_type: str | None = None,
    limit: int = 200,
) -> list[FinancialFactResponse]:
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


def list_projection_fact_rows(
    strategy_instance_id: str,
    account_id: str,
    instrument_id: str,
) -> list[Row]:
    with connection() as db:
        return db.execute(
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


def save_formal_projection(
    *,
    strategy_instance_id: str,
    account_id: str,
    instrument_id: str,
    has_trade: bool,
    net_quantity: str,
    average_price: str | None,
    quantity_unit: str,
    currency: str,
    trading_pnl: str,
    funding_pnl: str,
    swap_pnl: str,
    fee_pnl: str,
    fx_pnl: str,
    total_pnl: str,
    fact_count: int,
    data_quality_state: str,
    updated_at: str,
) -> None:
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
                    net_quantity,
                    average_price,
                    quantity_unit,
                    data_quality_state,
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
                currency,
                trading_pnl,
                funding_pnl,
                swap_pnl,
                fee_pnl,
                fx_pnl,
                total_pnl,
                fact_count,
                data_quality_state,
                updated_at,
            ),
        )


def prepare_strategy_rebuild(strategy_instance_id: str) -> tuple[int, list[Row]]:
    with connection() as db:
        fact_count_row = db.execute(
            "SELECT COUNT(*) AS count FROM financial_facts WHERE strategy_instance_id = ?",
            (strategy_instance_id,),
        ).fetchone()
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
    if fact_count_row is None:
        raise RuntimeError("Financial fact count query returned no row")
    return int(fact_count_row["count"]), pairs


def record_projection_rebuild_audit(
    *,
    audit_event_id: str,
    strategy_instance_id: str,
    details_json: str,
    created_at: str,
) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                audit_event_id,
                "formal_financial_projection_rebuilt",
                "strategy_instance",
                strategy_instance_id,
                details_json,
                created_at,
            ),
        )


def list_formal_pnl(strategy_instance_id: str) -> list[FormalPnlResponse]:
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


def list_active_account_rows(strategy_instance_id: str) -> list[Row]:
    with connection() as db:
        return db.execute(
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


def load_latest_balance_rows(
    strategy_instance_id: str,
    account_ids: list[str],
    valuation_iso: str,
) -> dict[str, Row | None]:
    rows: dict[str, Row | None] = {}
    with connection() as db:
        for account_id in account_ids:
            rows[account_id] = db.execute(
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
                (strategy_instance_id, account_id, valuation_iso),
            ).fetchone()
    return rows


def store_formal_nav_snapshot(
    *,
    snapshot_id: str,
    audit_event_id: str,
    strategy_instance_id: str,
    valuation_time: str,
    equity: str | None,
    capital_base: str,
    nav: str | None,
    currency: str,
    data_quality_state: str,
    required_account_count: int,
    included_account_count: int,
    missing_account_ids_json: str,
    audit_details_json: str,
    created_at: str,
) -> FormalNavSnapshotResponse:
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
                valuation_time,
                equity,
                capital_base,
                nav,
                currency,
                data_quality_state,
                required_account_count,
                included_account_count,
                missing_account_ids_json,
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
                audit_event_id,
                "formal_nav_snapshot_created",
                "strategy_instance",
                strategy_instance_id,
                audit_details_json,
                created_at,
            ),
        )
        row = db.execute(
            "SELECT * FROM formal_strategy_nav_snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("Formal NAV snapshot insert did not return a persisted row")
    return formal_nav_from_row(row)


def list_formal_nav_snapshots(strategy_instance_id: str) -> list[FormalNavSnapshotResponse]:
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


def _optional_decimal(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def financial_fact_from_row(row: Row) -> FinancialFactResponse:
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
        quantity=_optional_decimal(row["quantity"]),
        quantityUnit=row["quantity_unit"],
        price=_optional_decimal(row["price"]),
        contractMultiplier=_optional_decimal(row["contract_multiplier"]),
        amount=_optional_decimal(row["amount"]),
        currency=row["currency"],
        baseCurrency=row["base_currency"],
        fxRateToBase=_optional_decimal(row["fx_rate_to_base"]),
        convertedAmount=_optional_decimal(row["converted_amount"]),
        availableBalance=_optional_decimal(row["available_balance"]),
        occurredAt=row["occurred_at"],
        dataQualityState=row["data_quality_state"],
        createdAt=row["created_at"],
    )


def formal_pnl_from_row(row: Row) -> FormalPnlResponse:
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


def formal_position_from_row(row: Row) -> FormalPositionResponse:
    return FormalPositionResponse(
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        netQuantity=Decimal(row["net_quantity"]),
        averagePrice=_optional_decimal(row["average_price"]),
        quantityUnit=row["quantity_unit"],
        dataQualityState=row["data_quality_state"],
        updatedAt=row["updated_at"],
    )


def formal_nav_from_row(row: Row) -> FormalNavSnapshotResponse:
    return FormalNavSnapshotResponse(
        snapshotId=row["id"],
        strategyInstanceId=row["strategy_instance_id"],
        valuationTime=row["valuation_time"],
        equity=_optional_decimal(row["equity"]),
        capitalBase=Decimal(row["capital_base"]),
        nav=_optional_decimal(row["nav"]),
        currency=row["currency"],
        dataQualityState=row["data_quality_state"],
        requiredAccountCount=row["required_account_count"],
        includedAccountCount=row["included_account_count"],
        missingAccountIds=json.loads(row["missing_account_ids_json"]),
        createdAt=row["created_at"],
    )
