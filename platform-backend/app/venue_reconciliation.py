from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import connection
from app.financial_facts import CreateFinancialFactRequest, record_financial_fact
from app.trading import (
    apply_execution_events,
    get_order_response,
    get_order_row,
    reconcile_order,
    request_from_order_row,
    synchronize_trade_command_status,
)

DifferenceType = Literal[
    "missing_local",
    "missing_external",
    "quantity_mismatch",
    "price_mismatch",
    "currency_mismatch",
    "status_mismatch",
]
DifferenceStatus = Literal["open", "resolved", "accepted"]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS venue_reconciliation_runs (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    run_type TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    order_count INTEGER NOT NULL,
    fill_count INTEGER NOT NULL,
    position_count INTEGER NOT NULL,
    balance_count INTEGER NOT NULL,
    fact_count INTEGER NOT NULL,
    difference_count INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS reconciliation_differences (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    difference_key TEXT NOT NULL,
    difference_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    local_reference TEXT,
    external_reference TEXT,
    local_value_json TEXT NOT NULL,
    external_value_json TEXT NOT NULL,
    status TEXT NOT NULL,
    resolution_actor TEXT,
    resolution_reason TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, difference_key),
    FOREIGN KEY(run_id) REFERENCES venue_reconciliation_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_runs_account
ON venue_reconciliation_runs(account_id, started_at);

CREATE INDEX IF NOT EXISTS idx_reconciliation_differences_run
ON reconciliation_differences(run_id, status, difference_type);
"""


class VenueReconciliationRunRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    actor: str = Field(min_length=1, max_length=128)


class VenueReconciliationRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    idempotency_key: str = Field(alias="idempotencyKey")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    run_type: str = Field(alias="runType")
    source: str
    status: str
    order_count: int = Field(alias="orderCount")
    fill_count: int = Field(alias="fillCount")
    position_count: int = Field(alias="positionCount")
    balance_count: int = Field(alias="balanceCount")
    fact_count: int = Field(alias="factCount")
    difference_count: int = Field(alias="differenceCount")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class ReconciliationDifferenceResponse(BaseModel):
    difference_id: str = Field(alias="differenceId")
    run_id: str = Field(alias="runId")
    difference_key: str = Field(alias="differenceKey")
    difference_type: DifferenceType = Field(alias="differenceType")
    entity_type: str = Field(alias="entityType")
    local_reference: str | None = Field(default=None, alias="localReference")
    external_reference: str | None = Field(default=None, alias="externalReference")
    local_value: dict[str, object] = Field(alias="localValue")
    external_value: dict[str, object] = Field(alias="externalValue")
    status: DifferenceStatus
    resolution_actor: str | None = Field(default=None, alias="resolutionActor")
    resolution_reason: str | None = Field(default=None, alias="resolutionReason")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    created_at: datetime = Field(alias="createdAt")


class ResolveDifferenceRequest(BaseModel):
    status: Literal["resolved", "accepted"]
    actor: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class OrderVenueReconciliationResponse(BaseModel):
    order_id: str = Field(alias="orderId")
    command_id: str = Field(alias="commandId")
    source: str
    external_order_id: str | None = Field(default=None, alias="externalOrderId")
    status_before: str = Field(alias="statusBefore")
    status_after: str = Field(alias="statusAfter")
    recovered: bool
    imported_fact_ids: list[str] = Field(alias="importedFactIds")
    difference_ids: list[str] = Field(alias="differenceIds")
    reconciled_at: datetime = Field(alias="reconciledAt")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def runtime_get(path: str, params: dict[str, str] | None = None):
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.runtime_base_url}{path}",
            params=params,
            timeout=settings.runtime_timeout_seconds,
        )
        return response
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Execution Runtime query failed") from exc


def audit(event_type: str, subject_type: str, subject_id: str, details: dict[str, object]) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                event_type,
                subject_type,
                subject_id,
                json.dumps(details, ensure_ascii=False, sort_keys=True, default=str),
                now_iso(),
            ),
        )


def strategy_for_order(order_row) -> str:
    with connection() as db:
        row = db.execute(
            "SELECT strategy_instance_id FROM trade_commands WHERE id = ?",
            (order_row["command_id"],),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=422,
            detail="Order has no authoritative StrategyInstance and cannot enter formal reconciliation",
        )
    return row["strategy_instance_id"]


def reconcile_order_with_venue(order_id: str) -> OrderVenueReconciliationResponse:
    ensure_schema()
    initial = get_order_row(order_id)
    status_before = initial["status"]
    if status_before == "result_unknown":
        reconcile_order(order_id)
    row = get_order_row(order_id)
    strategy_instance_id = strategy_for_order(row)

    response = runtime_get(f"/venue/orders/by-platform/{order_id}")
    if response.status_code == 404:
        difference_id = standalone_order_difference(
            order_id,
            "missing_external",
            {"status": row["status"]},
            {},
        )
        return OrderVenueReconciliationResponse(
            orderId=order_id,
            commandId=row["command_id"],
            source="runtime",
            externalOrderId=None,
            statusBefore=status_before,
            statusAfter=row["status"],
            recovered=False,
            importedFactIds=[],
            differenceIds=[difference_id],
            reconciledAt=datetime.now(UTC),
        )
    response.raise_for_status()
    external_order = response.json()
    source = str(external_order["source"])

    imported_fact_ids: list[str] = []
    order_fact = record_financial_fact(
        CreateFinancialFactRequest(
            idempotencyKey=(
                f"venue-order:{source}:{external_order['externalOrderId']}:"
                f"{external_order['asOf']}"
            ),
            factType="external_order",
            source=source,
            externalId=f"{external_order['externalOrderId']}:{external_order['asOf']}",
            strategyInstanceId=strategy_instance_id,
            accountId=row["account_id"],
            instrumentId=row["instrument_id"],
            occurredAt=external_order["asOf"],
            payload=external_order,
        )
    )
    imported_fact_ids.append(order_fact.fact_id)

    fill_response = runtime_get(
        "/venue/fills",
        params={"platformOrderId": order_id},
    )
    fill_response.raise_for_status()
    fills = fill_response.json()
    request = request_from_order_row(row)
    events: list[dict[str, object]] = []
    for fill in fills:
        fact = record_financial_fact(
            CreateFinancialFactRequest(
                idempotencyKey=f"venue-fill:{source}:{fill['externalFillId']}",
                factType="trade_fill",
                source=source,
                externalId=str(fill["externalFillId"]),
                strategyInstanceId=strategy_instance_id,
                accountId=row["account_id"],
                instrumentId=row["instrument_id"],
                side=fill["side"],
                quantity=fill["quantity"],
                price=fill["price"],
                currency=fill["currency"],
                occurredAt=fill["occurredAt"],
                payload=fill,
            )
        )
        imported_fact_ids.append(fact.fact_id)
        events.append(
            {
                "event_id": fill["externalFillId"],
                "command_id": row["command_id"],
                "platform_order_id": order_id,
                "event_type": "order_filled",
                "external_order_id": fill["externalOrderId"],
                "fill_price": fill["price"],
                "fill_quantity": fill["quantity"],
                "occurred_at": fill["occurredAt"],
                "reason": None,
            }
        )

    if events:
        apply_execution_events(
            order_id,
            request,
            events,
            expected_command_id=row["command_id"],
        )
        synchronize_trade_command_status(row["command_id"], order_id)
    elif external_order["status"] in {"accepted", "rejected", "canceled"}:
        update_order_from_external(row, external_order)

    final = get_order_row(order_id)
    differences = compare_order(order_id, final, external_order, fills)
    audit(
        "venue_order_reconciled",
        "order",
        order_id,
        {
            "source": source,
            "externalOrderId": external_order["externalOrderId"],
            "statusBefore": status_before,
            "statusAfter": final["status"],
            "factIds": imported_fact_ids,
            "differenceIds": differences,
        },
    )
    return OrderVenueReconciliationResponse(
        orderId=order_id,
        commandId=row["command_id"],
        source=source,
        externalOrderId=external_order["externalOrderId"],
        statusBefore=status_before,
        statusAfter=final["status"],
        recovered=status_before == "result_unknown" and final["status"] != "result_unknown",
        importedFactIds=imported_fact_ids,
        differenceIds=differences,
        reconciledAt=datetime.now(UTC),
    )


def update_order_from_external(row, external_order: dict[str, object]) -> None:
    mapping = {
        "accepted": "acknowledged",
        "rejected": "rejected",
        "canceled": "canceled",
        "unknown": "result_unknown",
    }
    local_status = mapping.get(str(external_order["status"]))
    if local_status is None:
        return
    with connection() as db:
        db.execute(
            """
            UPDATE orders
            SET status = ?, external_order_id = ?, updated_at = ?
            WHERE id = ? AND status != 'filled'
            """,
            (
                local_status,
                external_order["externalOrderId"],
                external_order["asOf"],
                row["id"],
            ),
        )


def compare_order(
    order_id: str,
    local_row,
    external_order: dict[str, object],
    fills: list[dict[str, object]],
) -> list[str]:
    difference_ids: list[str] = []
    expected_status = {
        "accepted": "acknowledged",
        "filled": "filled",
        "rejected": "rejected",
        "canceled": "canceled",
        "unknown": "result_unknown",
    }.get(str(external_order["status"]), "result_unknown")
    if local_row["status"] != expected_status:
        difference_ids.append(
            standalone_order_difference(
                order_id,
                "status_mismatch",
                {"status": local_row["status"]},
                {"status": external_order["status"]},
            )
        )
    external_quantity = sum(Decimal(str(fill["quantity"])) for fill in fills)
    with connection() as db:
        local_fill = db.execute(
            "SELECT COALESCE(SUM(CAST(quantity AS REAL)), 0) AS quantity FROM fills WHERE order_id = ?",
            (order_id,),
        ).fetchone()
    local_quantity = Decimal(str(local_fill["quantity"]))
    if local_quantity != external_quantity:
        difference_ids.append(
            standalone_order_difference(
                order_id,
                "quantity_mismatch",
                {"filledQuantity": format(local_quantity, "f")},
                {"filledQuantity": format(external_quantity, "f")},
            )
        )
    return difference_ids


def standalone_order_difference(
    order_id: str,
    difference_type: DifferenceType,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    ensure_schema()
    run_id = f"order-reconcile:{order_id}"
    at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            )
            SELECT ?, ?, ?, tc.strategy_instance_id, o.account_id, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            FROM orders o JOIN trade_commands tc ON tc.id = o.command_id
            WHERE o.id = ?
            """,
            (
                run_id,
                run_id,
                canonical_hash({"orderId": order_id}),
                "order",
                "runtime",
                "completed_with_differences",
                1,
                0,
                0,
                0,
                0,
                1,
                at,
                at,
                order_id,
            ),
        )
    return create_difference(
        run_id,
        f"order:{order_id}:{difference_type}",
        difference_type,
        "order",
        order_id,
        None,
        local_value,
        external_value,
    )


def run_account_reconciliation(
    request: VenueReconciliationRunRequest,
) -> VenueReconciliationRunResponse:
    ensure_schema()
    validate_strategy_account(request.strategy_instance_id, request.account_id)
    payload = request.model_dump(by_alias=True, mode="json")
    payload_hash = canonical_hash(payload)
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Reconciliation idempotency key was reused with a different payload",
                )
            return run_from_row(existing)

    positions_response = runtime_get(
        "/venue/positions",
        params={"accountId": request.account_id},
    )
    balances_response = runtime_get(
        "/venue/balances",
        params={"accountId": request.account_id},
    )
    positions_response.raise_for_status()
    balances_response.raise_for_status()
    positions = positions_response.json()
    balances = balances_response.json()
    source = str((positions or balances or [{"source": "runtime"}])[0]["source"])

    run_id = str(uuid4())
    started_at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                request.idempotency_key,
                payload_hash,
                request.strategy_instance_id,
                request.account_id,
                "account_snapshot",
                source,
                "processing",
                0,
                0,
                len(positions),
                len(balances),
                0,
                0,
                started_at,
                None,
            ),
        )

    fact_count = 0
    difference_ids: list[str] = []
    for position in positions:
        fact = record_financial_fact(
            CreateFinancialFactRequest(
                idempotencyKey=(
                    f"venue-position:{source}:{position['externalPositionId']}:"
                    f"{position['asOf']}"
                ),
                factType="position",
                source=source,
                externalId=f"{position['externalPositionId']}:{position['asOf']}",
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                instrumentId=position["instrumentId"],
                occurredAt=position["asOf"],
                payload=position,
            )
        )
        fact_count += 1
        difference_ids.extend(compare_position(run_id, request, position, fact.fact_id))

    for balance in balances:
        record_financial_fact(
            CreateFinancialFactRequest(
                idempotencyKey=f"venue-balance:{source}:{balance['externalBalanceId']}",
                factType="balance",
                source=source,
                externalId=balance["externalBalanceId"],
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                amount=balance["equity"],
                availableBalance=balance["availableBalance"],
                currency=balance["currency"],
                occurredAt=balance["asOf"],
                payload=balance,
            )
        )
        fact_count += 1
        difference_ids.extend(compare_balance(run_id, request, balance))

    completed_at = now_iso()
    status = "completed" if not difference_ids else "completed_with_differences"
    with connection() as db:
        db.execute(
            """
            UPDATE venue_reconciliation_runs
            SET status = ?, fact_count = ?, difference_count = ?, completed_at = ?
            WHERE id = ?
            """,
            (status, fact_count, len(difference_ids), completed_at, run_id),
        )
        row = db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    audit(
        "venue_reconciliation_completed",
        "venue_reconciliation_run",
        run_id,
        {
            "strategyInstanceId": request.strategy_instance_id,
            "accountId": request.account_id,
            "source": source,
            "factCount": fact_count,
            "differenceIds": difference_ids,
            "actor": request.actor,
        },
    )
    return run_from_row(row)


def validate_strategy_account(strategy_instance_id: str, account_id: str) -> None:
    with connection() as db:
        row = db.execute(
            """
            SELECT sab.id
            FROM strategy_account_bindings sab
            JOIN strategy_instances si ON si.id = sab.strategy_instance_id
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ? AND sab.account_id = ?
              AND sab.status = 'active' AND si.status = 'active' AND a.status = 'active'
            """,
            (strategy_instance_id, account_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="Account is not actively bound to strategy")


def compare_position(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
    fact_id: str,
) -> list[str]:
    with connection() as db:
        local = db.execute(
            """
            SELECT net_quantity, average_price
            FROM formal_positions
            WHERE strategy_instance_id = ? AND account_id = ? AND instrument_id = ?
            """,
            (
                request.strategy_instance_id,
                request.account_id,
                external["instrumentId"],
            ),
        ).fetchone()
        if local is None:
            local = db.execute(
                """
                SELECT net_quantity, average_price
                FROM positions
                WHERE account_id = ? AND instrument_id = ?
                """,
                (request.account_id, external["instrumentId"]),
            ).fetchone()
    if local is None:
        return [
            create_difference(
                run_id,
                f"position:{external['instrumentId']}:missing_local",
                "missing_local",
                "position",
                None,
                str(external["externalPositionId"]),
                {},
                external,
            )
        ]
    if Decimal(local["net_quantity"]) != Decimal(str(external["netQuantity"])):
        return [
            create_difference(
                run_id,
                f"position:{external['instrumentId']}:quantity_mismatch",
                "quantity_mismatch",
                "position",
                f"{request.account_id}:{external['instrumentId']}",
                str(external["externalPositionId"]),
                {"netQuantity": local["net_quantity"]},
                {"netQuantity": external["netQuantity"], "factId": fact_id},
            )
        ]
    return []


def compare_balance(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
) -> list[str]:
    with connection() as db:
        local = db.execute(
            """
            SELECT equity, available_balance, currency
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC, created_at DESC
            LIMIT 1
            """,
            (request.account_id,),
        ).fetchone()
    if local is None:
        return [
            create_difference(
                run_id,
                f"balance:{external['currency']}:missing_local",
                "missing_local",
                "balance",
                request.account_id,
                str(external["externalBalanceId"]),
                {},
                external,
            )
        ]
    if local["currency"] != external["currency"]:
        return [
            create_difference(
                run_id,
                f"balance:{external['currency']}:currency_mismatch",
                "currency_mismatch",
                "balance",
                request.account_id,
                str(external["externalBalanceId"]),
                {"currency": local["currency"]},
                {"currency": external["currency"]},
            )
        ]
    if Decimal(local["equity"]) != Decimal(str(external["equity"])):
        return [
            create_difference(
                run_id,
                f"balance:{external['currency']}:quantity_mismatch",
                "quantity_mismatch",
                "balance",
                request.account_id,
                str(external["externalBalanceId"]),
                {"equity": local["equity"]},
                {"equity": external["equity"]},
            )
        ]
    return []


def create_difference(
    run_id: str,
    difference_key: str,
    difference_type: DifferenceType,
    entity_type: str,
    local_reference: str | None,
    external_reference: str | None,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    difference_id = str(uuid4())
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO reconciliation_differences (
                id, run_id, difference_key, difference_type, entity_type,
                local_reference, external_reference, local_value_json,
                external_value_json, status, resolution_actor, resolution_reason,
                resolved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                difference_id,
                run_id,
                difference_key,
                difference_type,
                entity_type,
                local_reference,
                external_reference,
                json.dumps(local_value, sort_keys=True, default=str),
                json.dumps(external_value, sort_keys=True, default=str),
                "open",
                None,
                None,
                None,
                now_iso(),
            ),
        )
        row = db.execute(
            """
            SELECT id FROM reconciliation_differences
            WHERE run_id = ? AND difference_key = ?
            """,
            (run_id, difference_key),
        ).fetchone()
    return row["id"]


def get_run(run_id: str) -> VenueReconciliationRunResponse:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Reconciliation run not found")
    return run_from_row(row)


def list_differences(run_id: str) -> list[ReconciliationDifferenceResponse]:
    ensure_schema()
    get_run(run_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT * FROM reconciliation_differences
            WHERE run_id = ? ORDER BY created_at, difference_key
            """,
            (run_id,),
        ).fetchall()
    return [difference_from_row(row) for row in rows]


def resolve_difference(
    difference_id: str,
    request: ResolveDifferenceRequest,
) -> ReconciliationDifferenceResponse:
    ensure_schema()
    at = now_iso()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM reconciliation_differences WHERE id = ?",
            (difference_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Reconciliation difference not found")
        if row["status"] != "open":
            return difference_from_row(row)
        db.execute(
            """
            UPDATE reconciliation_differences
            SET status = ?, resolution_actor = ?, resolution_reason = ?, resolved_at = ?
            WHERE id = ?
            """,
            (request.status, request.actor, request.reason, at, difference_id),
        )
        row = db.execute(
            "SELECT * FROM reconciliation_differences WHERE id = ?",
            (difference_id,),
        ).fetchone()
    audit(
        "reconciliation_difference_resolved",
        "reconciliation_difference",
        difference_id,
        {
            "status": request.status,
            "actor": request.actor,
            "reason": request.reason,
        },
    )
    return difference_from_row(row)


def run_from_row(row) -> VenueReconciliationRunResponse:
    return VenueReconciliationRunResponse(
        runId=row["id"],
        idempotencyKey=row["idempotency_key"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        runType=row["run_type"],
        source=row["source"],
        status=row["status"],
        orderCount=row["order_count"],
        fillCount=row["fill_count"],
        positionCount=row["position_count"],
        balanceCount=row["balance_count"],
        factCount=row["fact_count"],
        differenceCount=row["difference_count"],
        startedAt=row["started_at"],
        completedAt=row["completed_at"],
    )


def difference_from_row(row) -> ReconciliationDifferenceResponse:
    return ReconciliationDifferenceResponse(
        differenceId=row["id"],
        runId=row["run_id"],
        differenceKey=row["difference_key"],
        differenceType=row["difference_type"],
        entityType=row["entity_type"],
        localReference=row["local_reference"],
        externalReference=row["external_reference"],
        localValue=json.loads(row["local_value_json"]),
        externalValue=json.loads(row["external_value_json"]),
        status=row["status"],
        resolutionActor=row["resolution_actor"],
        resolutionReason=row["resolution_reason"],
        resolvedAt=row["resolved_at"],
        createdAt=row["created_at"],
    )


router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/trading/orders/{order_id}/venue-reconcile",
    response_model=OrderVenueReconciliationResponse,
    tags=["venue-reconciliation"],
)
def reconcile_platform_order(order_id: str) -> OrderVenueReconciliationResponse:
    return reconcile_order_with_venue(order_id)


@router.post(
    "/ops/venue-reconciliation/runs",
    response_model=VenueReconciliationRunResponse,
    tags=["venue-reconciliation"],
)
def create_reconciliation_run(
    request: VenueReconciliationRunRequest,
) -> VenueReconciliationRunResponse:
    return run_account_reconciliation(request)


@router.get(
    "/ops/venue-reconciliation/runs/{run_id}",
    response_model=VenueReconciliationRunResponse,
    tags=["venue-reconciliation"],
)
def read_reconciliation_run(run_id: str) -> VenueReconciliationRunResponse:
    return get_run(run_id)


@router.get(
    "/ops/venue-reconciliation/runs/{run_id}/differences",
    response_model=list[ReconciliationDifferenceResponse],
    tags=["venue-reconciliation"],
)
def read_reconciliation_differences(run_id: str) -> list[ReconciliationDifferenceResponse]:
    return list_differences(run_id)


@router.post(
    "/ops/venue-reconciliation/differences/{difference_id}/resolve",
    response_model=ReconciliationDifferenceResponse,
    tags=["venue-reconciliation"],
)
def resolve_reconciliation_difference(
    difference_id: str,
    request: ResolveDifferenceRequest,
) -> ReconciliationDifferenceResponse:
    return resolve_difference(difference_id, request)
