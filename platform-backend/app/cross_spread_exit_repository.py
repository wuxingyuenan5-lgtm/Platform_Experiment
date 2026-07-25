from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.cross_spread_exit_schemas import (
    CrossSpreadExitPlanResponse,
    ExecutionMode,
    SpreadDirection,
)
from app.database import connection


@dataclass(frozen=True, slots=True)
class BatchFillSummary:
    role: str
    side: str
    quantity: Decimal
    average_price: Decimal


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_batch_fill_summaries(batch_id: str) -> dict[str, BatchFillSummary]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT ebl.role, ebl.side, f.quantity, f.price
            FROM execution_batch_legs ebl
            JOIN fills f ON f.order_id = ebl.order_id
            WHERE ebl.batch_id = ?
            ORDER BY ebl.sequence, f.occurred_at, f.id
            """,
            (batch_id,),
        ).fetchall()
    grouped: dict[str, tuple[str, Decimal, Decimal]] = {}
    for row in rows:
        role = str(row["role"])
        side = str(row["side"])
        quantity = Decimal(row["quantity"])
        price = Decimal(row["price"])
        existing_side, total_quantity, total_notional = grouped.get(
            role,
            (side, Decimal("0"), Decimal("0")),
        )
        if existing_side != side:
            raise HTTPException(status_code=409, detail="Execution leg contains mixed fill sides")
        grouped[role] = (
            side,
            total_quantity + quantity,
            total_notional + quantity * price,
        )
    summaries: dict[str, BatchFillSummary] = {}
    for role, (side, quantity, notional) in grouped.items():
        if quantity <= 0:
            continue
        summaries[role] = BatchFillSummary(
            role=role,
            side=side,
            quantity=quantity,
            average_price=notional / quantity,
        )
    return summaries


def count_non_closed_exit_plans() -> int:
    with connection() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM cross_spread_exit_plans
            WHERE status != 'closed'
            """
        ).fetchone()
    return int(row["count"])


def count_unresolved_cross_spread_batches() -> int:
    with connection() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM execution_batches
            WHERE strategy_key = 'cross_venue_spread'
              AND status IN ('pending', 'executing', 'partially_executed', 'manual_intervention')
            """
        ).fetchone()
    return int(row["count"])


def create_exit_plan(
    *,
    strategy_instance_id: str,
    open_batch_id: str,
    direction: SpreadDirection,
    quantity_oz: Decimal,
    mt5_position_id: str,
    entry_spread: Decimal,
    take_profit_spread: Decimal,
    stop_loss_spread: Decimal,
    take_profit_execution_mode: ExecutionMode = "market",
    stop_loss_execution_mode: ExecutionMode = "market",
) -> CrossSpreadExitPlanResponse:
    existing = find_plan_by_open_batch(open_batch_id)
    if existing is not None:
        matches = (
            existing.direction == direction
            and existing.quantity_oz == quantity_oz
            and existing.mt5_position_id == mt5_position_id
            and existing.entry_spread == entry_spread
            and existing.take_profit_spread == take_profit_spread
            and existing.stop_loss_spread == stop_loss_spread
        )
        if not matches:
            raise HTTPException(
                status_code=409,
                detail="Open batch is already linked to a different exit plan",
            )
        return existing

    plan_id = str(uuid4())
    created_at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT INTO cross_spread_exit_plans (
                id, strategy_instance_id, open_batch_id, close_batch_id, direction,
                quantity_oz, mt5_position_id, entry_spread, take_profit_spread,
                stop_loss_spread, take_profit_execution_mode,
                stop_loss_execution_mode, status, trigger_reason, trigger_spread,
                created_at, updated_at, triggered_at, closed_at
            ) VALUES (
                ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?,
                'active', NULL, NULL, ?, ?, NULL, NULL
            )
            """,
            (
                plan_id,
                strategy_instance_id,
                open_batch_id,
                direction,
                format(quantity_oz, "f"),
                mt5_position_id,
                format(entry_spread, "f"),
                format(take_profit_spread, "f"),
                format(stop_loss_spread, "f"),
                take_profit_execution_mode,
                stop_loss_execution_mode,
                created_at,
                created_at,
            ),
        )
    return get_exit_plan(plan_id)


def configure_exit_plan_execution_modes(
    plan_id: str,
    *,
    take_profit_execution_mode: ExecutionMode,
    stop_loss_execution_mode: ExecutionMode,
) -> CrossSpreadExitPlanResponse:
    current = get_exit_plan(plan_id)
    requested = (take_profit_execution_mode, stop_loss_execution_mode)
    existing = (
        current.take_profit_execution_mode,
        current.stop_loss_execution_mode,
    )
    if existing == requested:
        return current
    if existing != ("market", "market") or current.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Exit plan execution modes are already configured differently",
        )

    updated_at = now_iso()
    with connection() as db:
        cursor = db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET take_profit_execution_mode = ?, stop_loss_execution_mode = ?,
                updated_at = ?
            WHERE id = ? AND status = 'active'
              AND take_profit_execution_mode = 'market'
              AND stop_loss_execution_mode = 'market'
            """,
            (
                take_profit_execution_mode,
                stop_loss_execution_mode,
                updated_at,
                plan_id,
            ),
        )
    if cursor.rowcount != 1:
        raise HTTPException(status_code=409, detail="Exit plan execution modes changed concurrently")
    return get_exit_plan(plan_id)


def get_exit_plan(plan_id: str) -> CrossSpreadExitPlanResponse:
    with connection() as db:
        row = db.execute(_plan_query("id = ?"), (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Cross-spread exit plan not found")
    return _plan_from_row(row)


def find_plan_by_open_batch(open_batch_id: str) -> CrossSpreadExitPlanResponse | None:
    with connection() as db:
        row = db.execute(_plan_query("open_batch_id = ?"), (open_batch_id,)).fetchone()
    return _plan_from_row(row) if row is not None else None


def list_exit_plans(status: str | None = None) -> list[CrossSpreadExitPlanResponse]:
    where = "1 = 1"
    parameters: tuple[str, ...] = ()
    if status is not None:
        where = "status = ?"
        parameters = (status,)
    with connection() as db:
        rows = db.execute(
            f"{_plan_query(where)} ORDER BY created_at DESC",
            parameters,
        ).fetchall()
    return [_plan_from_row(row) for row in rows]


def claim_exit_plan(
    plan_id: str,
    *,
    trigger_reason: str,
    trigger_spread: Decimal | None,
) -> CrossSpreadExitPlanResponse | None:
    claimed_at = now_iso()
    with connection() as db:
        cursor = db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET status = 'triggered', trigger_reason = ?, trigger_spread = ?,
                triggered_at = ?, updated_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (
                trigger_reason,
                format(trigger_spread, "f") if trigger_spread is not None else None,
                claimed_at,
                claimed_at,
                plan_id,
            ),
        )
    return get_exit_plan(plan_id) if cursor.rowcount == 1 else None


def release_exit_plan_claim(plan_id: str) -> CrossSpreadExitPlanResponse:
    updated_at = now_iso()
    with connection() as db:
        cursor = db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET status = 'active', trigger_reason = NULL, trigger_spread = NULL,
                triggered_at = NULL, updated_at = ?
            WHERE id = ? AND status = 'triggered' AND close_batch_id IS NULL
            """,
            (updated_at, plan_id),
        )
    if cursor.rowcount != 1:
        raise HTTPException(status_code=409, detail="Exit plan claim cannot be released")
    return get_exit_plan(plan_id)


def mark_plan_closing(plan_id: str, close_batch_id: str) -> CrossSpreadExitPlanResponse:
    updated_at = now_iso()
    with connection() as db:
        cursor = db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET status = 'closing', close_batch_id = ?, updated_at = ?
            WHERE id = ? AND status = 'triggered'
            """,
            (close_batch_id, updated_at, plan_id),
        )
    if cursor.rowcount != 1:
        raise HTTPException(status_code=409, detail="Exit plan is not in triggered state")
    return get_exit_plan(plan_id)


def mark_plan_closed(plan_id: str, close_batch_id: str) -> CrossSpreadExitPlanResponse:
    closed_at = now_iso()
    with connection() as db:
        db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET status = 'closed', close_batch_id = ?, updated_at = ?, closed_at = ?
            WHERE id = ? AND status IN ('triggered', 'closing')
            """,
            (close_batch_id, closed_at, closed_at, plan_id),
        )
    return get_exit_plan(plan_id)


def mark_plan_manual_intervention(
    plan_id: str,
    *,
    close_batch_id: str | None,
) -> CrossSpreadExitPlanResponse:
    updated_at = now_iso()
    with connection() as db:
        db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET status = 'manual_intervention', close_batch_id = COALESCE(?, close_batch_id),
                updated_at = ?
            WHERE id = ? AND status != 'closed'
            """,
            (close_batch_id, updated_at, plan_id),
        )
    return get_exit_plan(plan_id)


def _plan_query(where_clause: str) -> str:
    return f"""
        SELECT id, strategy_instance_id, open_batch_id, close_batch_id, direction,
               quantity_oz, mt5_position_id, entry_spread, take_profit_spread,
               stop_loss_spread, take_profit_execution_mode,
               stop_loss_execution_mode, status, trigger_reason, trigger_spread,
               created_at, updated_at, triggered_at, closed_at
        FROM cross_spread_exit_plans
        WHERE {where_clause}
    """


def _plan_from_row(row) -> CrossSpreadExitPlanResponse:
    return CrossSpreadExitPlanResponse(
        planId=row["id"],
        strategyInstanceId=row["strategy_instance_id"],
        openBatchId=row["open_batch_id"],
        closeBatchId=row["close_batch_id"],
        direction=row["direction"],
        quantityOz=Decimal(row["quantity_oz"]),
        mt5PositionId=row["mt5_position_id"],
        entrySpread=Decimal(row["entry_spread"]),
        takeProfitSpread=Decimal(row["take_profit_spread"]),
        stopLossSpread=Decimal(row["stop_loss_spread"]),
        takeProfitExecutionMode=row["take_profit_execution_mode"],
        stopLossExecutionMode=row["stop_loss_execution_mode"],
        status=row["status"],
        triggerReason=row["trigger_reason"],
        triggerSpread=(Decimal(row["trigger_spread"]) if row["trigger_spread"] else None),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
        triggeredAt=row["triggered_at"],
        closedAt=row["closed_at"],
    )
