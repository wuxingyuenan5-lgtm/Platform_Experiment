"""Finish an explicitly requested close whose MT5 command never reached Runtime."""

from decimal import Decimal

from fastapi import HTTPException

from app.cross_spread_exit_repository import (
    load_batch_fill_summaries,
    mark_plan_closed,
    mark_plan_manual_intervention,
)
from app.cross_spread_exit_schemas import CrossSpreadExitPlanResponse
from app.cross_spread_live_read_client import CrossSpreadLiveReadError, list_positions
from app.database import connection
from app.execution_batches import (
    get_execution_batch,
    now_iso,
    update_batch_status,
    update_leg_status,
)
from app.execution_risk import complete_batch_risk
from app.order_execution_intents import get_order_execution_intent
from app.schemas import CreateTradeCommandRequest
from app.security import assert_live_account_execution_allowed
from app.strategies.domain import ExecutionPlan
from app.trade_commands import (
    find_trade_command_by_idempotency_key,
    retry_unsubmitted_trade_command,
)


def prepare_unsubmitted_mt5_close(plan: CrossSpreadExitPlanResponse, quantity: Decimal):
    """Keep the original instruction, batch, Ticket, quantity and command identity.

    Called only by a new explicit user close request. It never replays Bybit and
    never resets an order that could have been dispatched.
    """
    batch = get_execution_batch(str(plan.close_batch_id))
    with connection() as db:
        instruction = db.execute(
            "SELECT * FROM strategy_runs WHERE execution_batch_id=? AND action='close' "
            "AND strategy_instance_id=?",
            (batch.batch_id, plan.strategy_instance_id),
        ).fetchone()
        persisted_legs = {
            r["role"]: dict(r)
            for r in db.execute(
                "SELECT * FROM execution_batch_legs WHERE batch_id=?",
                (batch.batch_id,),
            )
        }
    if instruction is None or not instruction["execution_plan_json"]:
        raise HTTPException(409, "Close recovery requires the original execution plan")
    frozen = ExecutionPlan.model_validate_json(instruction["execution_plan_json"])
    legs = {leg.role: leg for leg in batch.legs}
    original = {leg.role: leg for leg in frozen.legs}
    if set(legs) != {"bybit_leg", "mt5_leg"} or set(original) != set(legs):
        raise HTTPException(409, "Close recovery requires the original two legs")
    bybit, mt5 = original["bybit_leg"], original["mt5_leg"]
    key = f"instruction:{instruction['idempotency_key']}:mt5_leg"
    prior = find_trade_command_by_idempotency_key(key)
    if (
        prior is None
        or prior["status"] != "rejected"
        or prior["order_id"] is not None
        or legs["mt5_leg"].order_id is not None
        or legs["mt5_leg"].status not in {"failed", "blocked", "rejected"}
    ):
        raise HTTPException(409, "MT5 close may have reached the venue; reconcile before recovery")
    intent = get_order_execution_intent(key)
    summaries = load_batch_fill_summaries(batch.batch_id)
    bybit_fill = summaries.get("bybit_leg")
    if (
        frozen.strategy_key != "cross_venue_spread"
        or frozen.action.value != "close"
        or legs["bybit_leg"].status != "filled"
        or bybit_fill is None
        or bybit_fill.quantity != bybit.maximum_quantity
        or bybit_fill.side != bybit.side
        or bybit.side != ("sell" if plan.direction == "LONG_SPREAD" else "buy")
        or any(
            (
                persisted_legs[role]["account_id"],
                persisted_legs[role]["instrument_id"],
                persisted_legs[role]["side"],
                Decimal(persisted_legs[role]["quantity"]),
            )
            != (leg.account_id, leg.instrument_id, leg.side, leg.maximum_quantity)
            for role, leg in original.items()
        )
        or quantity != bybit.maximum_quantity
        or quantity > plan.quantity_oz
        or mt5.maximum_quantity * mt5.contract_multiplier != quantity
        or not mt5.reduce_only
        or mt5.position_id != plan.mt5_position_id
        or mt5.side != ("buy" if plan.direction == "LONG_SPREAD" else "sell")
        or mt5.execution_policy.value != "market"
        or not intent.reduce_only
        or intent.position_id != mt5.position_id
        or intent.execution_policy != "default"
    ):
        raise HTTPException(409, "Recovery must finish the original close quantity and MT5 Ticket")
    for account_id in {bybit.account_id, mt5.account_id}:
        assert_live_account_execution_allowed(account_id, plan.strategy_instance_id)
    _verify_ticket(mt5, plan.quantity_oz)
    request = CreateTradeCommandRequest(
        idempotencyKey=key,
        strategyInstanceId=plan.strategy_instance_id,
        accountId=mt5.account_id,
        instrumentId=mt5.instrument_id,
        symbol=mt5.external_symbol,
        side=mt5.side,
        orderType="market",
        quantity=mt5.maximum_quantity,
    )
    return batch, instruction, mt5, key, request, summaries


def recover_unsubmitted_mt5_close(plan: CrossSpreadExitPlanResponse, quantity: Decimal):
    batch, instruction, mt5, key, request, summaries = prepare_unsubmitted_mt5_close(plan, quantity)
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        command = find_trade_command_by_idempotency_key(key, db=db)
        current = db.execute(
            "SELECT p.status AS plan_status,b.status AS batch_status,l.status AS leg_status,"
            "l.order_id FROM cross_spread_exit_plans p JOIN execution_batches b "
            "ON b.id=p.close_batch_id JOIN execution_batch_legs l ON l.batch_id=b.id "
            "WHERE p.id=? AND b.id=? AND l.role='mt5_leg'",
            (plan.plan_id, batch.batch_id),
        ).fetchone()
        risk_action = db.execute(
            "SELECT 1 FROM execution_risk_actions WHERE batch_id=? AND action!='hold_and_escalate'",
            (batch.batch_id,),
        ).fetchone()
        if (
            current is None
            or current["plan_status"] != "manual_intervention"
            or current["batch_status"] != "manual_intervention"
            or current["leg_status"] not in {"failed", "blocked", "rejected"}
            or current["order_id"] is not None
            or risk_action is not None
            or command is None
            or command["status"] != "rejected"
            or command["order_id"] is not None
            or "mt5_leg" in summaries
        ):
            raise HTTPException(
                409, "MT5 close may have reached the venue; reconcile before recovery"
            )
        timestamp = now_iso()
        db.execute(
            "UPDATE cross_spread_exit_plans SET status='triggered',updated_at=? WHERE id=?",
            (timestamp, plan.plan_id),
        )
        db.execute(
            "UPDATE execution_batches SET status='executing',updated_at=? WHERE id=?",
            (timestamp, batch.batch_id),
        )
        db.execute(
            "UPDATE strategy_runs SET status='executing',updated_at=? WHERE id=?",
            (timestamp, instruction["id"]),
        )
    try:
        update_leg_status(batch.batch_id, "mt5_leg", "submitting")
        result = retry_unsubmitted_trade_command(request)
        update_leg_status(
            batch.batch_id, "mt5_leg", result.status, order_id=result.platform_order_id
        )
        if result.status != "filled":
            raise HTTPException(409, f"MT5 close recovery requires reconciliation: {result.status}")
        fills = load_batch_fill_summaries(batch.batch_id)
        if "mt5_leg" not in fills or fills["mt5_leg"].quantity != mt5.maximum_quantity:
            raise HTTPException(409, "MT5 close fill quantity requires reconciliation")
        _verify_ticket(mt5, plan.quantity_oz - quantity)
        if complete_batch_risk(batch.batch_id).risk_status != "clear":
            raise HTTPException(409, "Recovered close still has unresolved execution exposure")
        update_batch_status(batch.batch_id, "hedged", requires_manual_intervention=False)
        updated = mark_plan_closed(plan.plan_id, batch.batch_id, quantity)
        with connection() as db:
            db.execute(
                "UPDATE strategy_runs SET status='completed',failure_reason=NULL,updated_at=? "
                "WHERE id=?",
                (now_iso(), instruction["id"]),
            )
        return get_execution_batch(batch.batch_id), updated
    except Exception as exc:
        command = find_trade_command_by_idempotency_key(key)
        if command is not None:
            update_leg_status(
                batch.batch_id,
                "mt5_leg",
                command["status"],
                order_id=command["order_id"],
                failure_reason=str(exc),
            )
        reason = str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=reason,
            requires_manual_intervention=True,
        )
        mark_plan_manual_intervention(plan.plan_id, close_batch_id=batch.batch_id)
        with connection() as db:
            db.execute(
                "UPDATE strategy_runs SET status='manual_intervention',"
                "failure_reason=?,updated_at=? "
                "WHERE id=?",
                (reason, now_iso(), instruction["id"]),
            )
        raise


def _verify_ticket(leg, remaining_oz: Decimal) -> None:
    try:
        positions = [
            p for p in list_positions(leg.account_id) if p.external_position_id == leg.position_id
        ]
    except CrossSpreadLiveReadError as exc:
        raise HTTPException(503, str(exc)) from exc
    if remaining_oz == 0 and not positions:
        return
    expected = remaining_oz / leg.contract_multiplier * (-1 if leg.side == "buy" else 1)
    if (
        len(positions) != 1
        or positions[0].account_id != leg.account_id
        or positions[0].instrument_id != leg.instrument_id
        or positions[0].symbol.upper() != leg.external_symbol.upper()
        or positions[0].net_quantity != expected
    ):
        raise HTTPException(409, "MT5 Position Ticket quantity does not match the remaining close")
