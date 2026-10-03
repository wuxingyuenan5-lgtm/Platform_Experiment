from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.cross_spread_exit_schemas import (
    CrossSpreadExitPlanResponse,
    ExecutionMode,
    LimitStrategy,
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


def load_batch_leg_external_order_id(batch_id: str, role: str) -> str:
    with connection() as db:
        row = db.execute(
            """
            SELECT o.external_order_id
            FROM execution_batch_legs ebl
            JOIN orders o ON o.id = ebl.order_id
            WHERE ebl.batch_id = ? AND ebl.role = ?
            """,
            (batch_id, role),
        ).fetchone()
    external_order_id = str(row["external_order_id"] or "") if row is not None else ""
    if not external_order_id:
        raise HTTPException(
            status_code=409,
            detail="Completed execution leg has no external order identity",
        )
    return external_order_id


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


def count_unresolved_cross_spread_batches(account_id: str | None = None) -> int:
    with connection() as db:
        if account_id:
            row = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM execution_batches
                WHERE strategy_key = 'cross_venue_spread'
                  AND account_id = ?
                  AND status IN (
                      'pending', 'executing', 'partially_executed', 'manual_intervention'
                  )
                """,
                (account_id,),
            ).fetchone()
        else:
            row = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM execution_batches
                WHERE strategy_key = 'cross_venue_spread'
                  AND status IN (
                      'pending', 'executing', 'partially_executed', 'manual_intervention'
                  )
                """
            ).fetchone()
    return int(row["count"])


def has_accepted_missing_external_order_difference(order_id: str) -> bool:
    """Require formal Owner acceptance of venue-proven absent order evidence."""
    with connection() as db:
        row = db.execute(
            """
            SELECT 1 FROM reconciliation_differences
            WHERE entity_type = 'order'
              AND difference_type = 'missing_external'
              AND local_reference = ?
              AND status IN ('accepted', 'resolved')
            LIMIT 1
            """,
            (order_id,),
        ).fetchone()
    return row is not None


def create_exit_plan(
    *,
    strategy_instance_id: str,
    open_batch_id: str,
    direction: SpreadDirection,
    quantity_oz: Decimal,
    mt5_position_id: str,
    entry_spread: Decimal,
    take_profit_spread: Decimal | None,
    stop_loss_spread: Decimal | None,
    take_profit_max_adverse_spread: Decimal = Decimal("0"),
    stop_loss_max_adverse_spread: Decimal = Decimal("0"),
    take_profit_execution_mode: ExecutionMode = "market",
    stop_loss_execution_mode: ExecutionMode = "market",
    take_profit_limit_strategy: LimitStrategy = "fok",
    stop_loss_limit_strategy: LimitStrategy = "fok",
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
                stop_loss_spread, take_profit_max_adverse_spread,
                stop_loss_max_adverse_spread, take_profit_execution_mode,
                stop_loss_execution_mode, take_profit_limit_strategy,
                stop_loss_limit_strategy, status, trigger_reason, trigger_spread,
                created_at, updated_at, triggered_at, closed_at
            ) VALUES (
                ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
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
                format(take_profit_spread, "f") if take_profit_spread is not None else "",
                format(stop_loss_spread, "f") if stop_loss_spread is not None else "",
                format(take_profit_max_adverse_spread, "f"),
                format(stop_loss_max_adverse_spread, "f"),
                take_profit_execution_mode,
                stop_loss_execution_mode,
                take_profit_limit_strategy,
                stop_loss_limit_strategy,
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
    take_profit_limit_strategy: LimitStrategy = "fok",
    stop_loss_limit_strategy: LimitStrategy = "fok",
    take_profit_max_adverse_spread: Decimal = Decimal("0"),
    stop_loss_max_adverse_spread: Decimal = Decimal("0"),
) -> CrossSpreadExitPlanResponse:
    current = get_exit_plan(plan_id)
    requested = (
        take_profit_execution_mode,
        stop_loss_execution_mode,
        take_profit_limit_strategy,
        stop_loss_limit_strategy,
    )
    existing = (
        current.take_profit_execution_mode,
        current.stop_loss_execution_mode,
        current.take_profit_limit_strategy,
        current.stop_loss_limit_strategy,
    )
    if existing == requested:
        return current
    if existing != ("market", "market", "fok", "fok") or current.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Exit plan execution settings are already configured differently",
        )

    updated_at = now_iso()
    with connection() as db:
        cursor = db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET take_profit_execution_mode = ?, stop_loss_execution_mode = ?,
                take_profit_limit_strategy = ?, stop_loss_limit_strategy = ?,
                take_profit_max_adverse_spread = ?, stop_loss_max_adverse_spread = ?,
                updated_at = ?
            WHERE id = ? AND status = 'active'
              AND take_profit_execution_mode = 'market'
              AND stop_loss_execution_mode = 'market'
              AND take_profit_limit_strategy = 'fok'
              AND stop_loss_limit_strategy = 'fok'
            """,
            (
                take_profit_execution_mode,
                stop_loss_execution_mode,
                take_profit_limit_strategy,
                stop_loss_limit_strategy,
                format(take_profit_max_adverse_spread, "f"),
                format(stop_loss_max_adverse_spread, "f"),
                updated_at,
                plan_id,
            ),
        )
    if cursor.rowcount != 1:
        raise HTTPException(
            status_code=409,
            detail="Exit plan execution settings changed concurrently",
        )
    return get_exit_plan(plan_id)


def update_exit_plan_settings(
    plan_id: str,
    *,
    take_profit_spread: Decimal | None = None,
    stop_loss_spread: Decimal | None = None,
    take_profit_execution_mode: ExecutionMode | None = None,
    stop_loss_execution_mode: ExecutionMode | None = None,
    take_profit_limit_strategy: LimitStrategy | None = None,
    stop_loss_limit_strategy: LimitStrategy | None = None,
    take_profit_max_adverse_spread: Decimal | None = None,
    stop_loss_max_adverse_spread: Decimal | None = None,
    update_take_profit: bool = False,
    update_stop_loss: bool = False,
    update_take_profit_execution_mode: bool = False,
    update_stop_loss_execution_mode: bool = False,
    update_take_profit_limit_strategy: bool = False,
    update_stop_loss_limit_strategy: bool = False,
    update_take_profit_max_adverse_spread: bool = False,
    update_stop_loss_max_adverse_spread: bool = False,
) -> CrossSpreadExitPlanResponse:
    if not any(
        (
            update_take_profit,
            update_stop_loss,
            update_take_profit_execution_mode,
            update_stop_loss_execution_mode,
            update_take_profit_limit_strategy,
            update_stop_loss_limit_strategy,
            update_take_profit_max_adverse_spread,
            update_stop_loss_max_adverse_spread,
        )
    ):
        raise HTTPException(status_code=422, detail="At least one exit setting must be provided")

    current = get_exit_plan(plan_id)
    if current.status != "active":
        raise HTTPException(status_code=409, detail="Only active exit plans can be updated")

    next_take_profit = take_profit_spread if update_take_profit else current.take_profit_spread
    next_stop_loss = stop_loss_spread if update_stop_loss else current.stop_loss_spread
    next_take_profit_execution_mode = (
        take_profit_execution_mode
        if update_take_profit_execution_mode
        else current.take_profit_execution_mode
    )
    next_stop_loss_execution_mode = (
        stop_loss_execution_mode
        if update_stop_loss_execution_mode
        else current.stop_loss_execution_mode
    )
    next_take_profit_limit_strategy = (
        take_profit_limit_strategy
        if update_take_profit_limit_strategy
        else current.take_profit_limit_strategy
    )
    next_stop_loss_limit_strategy = (
        stop_loss_limit_strategy
        if update_stop_loss_limit_strategy
        else current.stop_loss_limit_strategy
    )
    next_take_profit_max_adverse_spread = (
        take_profit_max_adverse_spread
        if update_take_profit_max_adverse_spread
        else current.take_profit_max_adverse_spread
    )
    next_stop_loss_max_adverse_spread = (
        stop_loss_max_adverse_spread
        if update_stop_loss_max_adverse_spread
        else current.stop_loss_max_adverse_spread
    )
    if next_take_profit is not None and next_stop_loss is not None:
        if current.direction == "LONG_SPREAD" and next_take_profit <= next_stop_loss:
            raise HTTPException(
                status_code=422,
                detail="LONG_SPREAD take-profit exit spread must be above stop-loss exit spread",
            )
        if current.direction == "SHORT_SPREAD" and next_take_profit >= next_stop_loss:
            raise HTTPException(
                status_code=422,
                detail="SHORT_SPREAD take-profit exit spread must be below stop-loss exit spread",
            )

    if (
        next_take_profit == current.take_profit_spread
        and next_stop_loss == current.stop_loss_spread
        and next_take_profit_execution_mode == current.take_profit_execution_mode
        and next_stop_loss_execution_mode == current.stop_loss_execution_mode
        and next_take_profit_limit_strategy == current.take_profit_limit_strategy
        and next_stop_loss_limit_strategy == current.stop_loss_limit_strategy
        and next_take_profit_max_adverse_spread == current.take_profit_max_adverse_spread
        and next_stop_loss_max_adverse_spread == current.stop_loss_max_adverse_spread
    ):
        return current

    updated_at = now_iso()
    with connection() as db:
        cursor = db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET take_profit_spread = ?, stop_loss_spread = ?,
                take_profit_execution_mode = ?, stop_loss_execution_mode = ?,
                take_profit_limit_strategy = ?, stop_loss_limit_strategy = ?,
                take_profit_max_adverse_spread = ?, stop_loss_max_adverse_spread = ?,
                updated_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (
                format(next_take_profit, "f") if next_take_profit is not None else "",
                format(next_stop_loss, "f") if next_stop_loss is not None else "",
                next_take_profit_execution_mode,
                next_stop_loss_execution_mode,
                next_take_profit_limit_strategy,
                next_stop_loss_limit_strategy,
                format(next_take_profit_max_adverse_spread, "f"),
                format(next_stop_loss_max_adverse_spread, "f"),
                updated_at,
                plan_id,
            ),
        )
    if cursor.rowcount != 1:
        raise HTTPException(status_code=409, detail="Exit plan changed concurrently")
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


def reclaim_manual_exit_plan(
    plan_id: str,
    *,
    expected_close_batch_id: str | None,
) -> CrossSpreadExitPlanResponse | None:
    reclaimed_at = now_iso()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if expected_close_batch_id is None:
            plan = db.execute(
                "SELECT strategy_instance_id,mt5_position_id FROM cross_spread_exit_plans "
                "WHERE id=? AND status='manual_intervention' AND close_batch_id IS NULL",
                (plan_id,),
            ).fetchone()
            if plan is None:
                return None
            if not plan["mt5_position_id"]:
                raise HTTPException(409, "Close recovery requires a verified MT5 Position Ticket")
            # Every current close command persists its instruction before dispatch.
            # A missing batch link is not proof of no dispatch: reject any matching
            # or unidentifiable close instruction, including one without a batch.
            runs = db.execute(
                "SELECT requested_parameters_json FROM strategy_runs "
                "WHERE strategy_instance_id=? AND action='close'",
                (plan["strategy_instance_id"],),
            ).fetchall()
            for run in runs:
                parameters = json.loads(run["requested_parameters_json"])
                ticket = parameters.get("mt5PositionId")
                if not ticket or str(ticket) == plan["mt5_position_id"]:
                    raise HTTPException(
                        409, "Close instruction exists without a linked batch; reconcile it first"
                    )
        cursor = db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET status = 'triggered', trigger_reason = 'manual', trigger_spread = NULL,
                triggered_at = ?, updated_at = ?
            WHERE id = ? AND status = 'manual_intervention' AND close_batch_id IS ?
            """,
            (reclaimed_at, reclaimed_at, plan_id, expected_close_batch_id),
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
            WHERE id = ? AND status = 'triggered'
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


def mark_plan_closed(
    plan_id: str,
    close_batch_id: str,
    closed_quantity_oz: Decimal | None = None,
) -> CrossSpreadExitPlanResponse:
    closed_at = now_iso()
    with connection() as db:
        row = db.execute(
            (
                "SELECT quantity_oz FROM cross_spread_exit_plans "
                "WHERE id = ? AND status IN ('triggered', 'closing')"
            ),
            (plan_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=409, detail="Exit plan is not ready to settle")
        before = Decimal(row["quantity_oz"])
        closed = closed_quantity_oz or before
        if closed <= 0 or closed > before:
            raise HTTPException(
                status_code=422,
                detail="Close quantity exceeds remaining group quantity",
            )
        remaining = before - closed
        db.execute(
            """
            UPDATE cross_spread_exit_plans
            SET quantity_oz = ?,
                status = CASE WHEN CAST(? AS NUMERIC) = 0 THEN 'closed' ELSE 'active' END,
                close_batch_id = ?,
                trigger_reason = CASE WHEN ? THEN trigger_reason ELSE NULL END,
                trigger_spread = CASE WHEN ? THEN trigger_spread ELSE NULL END,
                triggered_at = CASE WHEN ? THEN triggered_at ELSE NULL END,
                updated_at = ?,
                closed_at = CASE WHEN CAST(? AS NUMERIC) = 0 THEN ? ELSE NULL END
            WHERE id = ? AND status IN ('triggered', 'closing')
            """,
            (
                format(remaining, "f"),
                format(remaining, "f"),
                close_batch_id,
                remaining == 0,
                remaining == 0,
                remaining == 0,
                closed_at,
                format(remaining, "f"),
                closed_at,
                plan_id,
            ),
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


def find_close_batch(
    plan: CrossSpreadExitPlanResponse,
    idempotency_key: str,
    quantity_oz: Decimal,
) -> str | None:
    """Recover the persisted result of this exact close intent after an exception."""
    with connection() as db:
        row = db.execute(
            "SELECT execution_batch_id,requested_parameters_json FROM strategy_runs "
            "WHERE idempotency_key=? AND strategy_instance_id=? AND action='close'",
            (idempotency_key, plan.strategy_instance_id),
        ).fetchone()
    if row is None or not row["execution_batch_id"]:
        return None
    parameters = json.loads(row["requested_parameters_json"])
    if (
        parameters.get("mt5PositionId") != plan.mt5_position_id
        or parameters.get("action")
        != ("CLOSE_LONG" if plan.direction == "LONG_SPREAD" else "CLOSE_SHORT")
        or Decimal(str(parameters.get("quantityOz"))) != quantity_oz
        or parameters.get("mt5ReduceOnly") is not True
    ):
        return None
    return str(row["execution_batch_id"])


def has_close_instruction(strategy_instance_id: str, idempotency_key: str) -> bool:
    """Return whether this close key was persisted, even if its payload conflicts."""
    with connection() as db:
        row = db.execute(
            "SELECT 1 FROM strategy_runs "
            "WHERE strategy_instance_id=? AND action='close' AND idempotency_key=? LIMIT 1",
            (strategy_instance_id, idempotency_key),
        ).fetchone()
    return row is not None


def _plan_query(where_clause: str) -> str:
    return f"""
        SELECT id, strategy_instance_id, open_batch_id, close_batch_id, direction,
               quantity_oz, mt5_position_id, entry_spread, take_profit_spread,
               stop_loss_spread, take_profit_max_adverse_spread,
               stop_loss_max_adverse_spread, take_profit_execution_mode,
               stop_loss_execution_mode, take_profit_limit_strategy,
               stop_loss_limit_strategy, status, trigger_reason, trigger_spread,
               created_at, updated_at, triggered_at, closed_at,
               (SELECT json_extract(a.details_json,'$.originLabel') FROM audit_events a
                WHERE a.event_type='execution_batch_restored' AND a.subject_type='execution_batch'
                  AND a.subject_id=cross_spread_exit_plans.open_batch_id
                ORDER BY a.created_at DESC,a.id DESC LIMIT 1) AS origin_label
        FROM cross_spread_exit_plans
        WHERE {where_clause}
    """


def _plan_from_row(row) -> CrossSpreadExitPlanResponse:
    return CrossSpreadExitPlanResponse(
        planId=row["id"],
        strategyInstanceId=row["strategy_instance_id"],
        openBatchId=row["open_batch_id"],
        closeBatchId=row["close_batch_id"],
        originLabel=row["origin_label"],
        direction=row["direction"],
        quantityOz=Decimal(row["quantity_oz"]),
        mt5PositionId=row["mt5_position_id"],
        entrySpread=Decimal(row["entry_spread"]),
        takeProfitSpread=(
            Decimal(row["take_profit_spread"]) if row["take_profit_spread"] else None
        ),
        stopLossSpread=(Decimal(row["stop_loss_spread"]) if row["stop_loss_spread"] else None),
        takeProfitMaxAdverseSpread=Decimal(row["take_profit_max_adverse_spread"]),
        stopLossMaxAdverseSpread=Decimal(row["stop_loss_max_adverse_spread"]),
        takeProfitExecutionMode=row["take_profit_execution_mode"],
        stopLossExecutionMode=row["stop_loss_execution_mode"],
        takeProfitLimitStrategy=row["take_profit_limit_strategy"],
        stopLossLimitStrategy=row["stop_loss_limit_strategy"],
        status=row["status"],
        triggerReason=row["trigger_reason"],
        triggerSpread=(Decimal(row["trigger_spread"]) if row["trigger_spread"] else None),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
        triggeredAt=row["triggered_at"],
        closedAt=row["closed_at"],
    )
