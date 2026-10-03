"""Owner-confirmed completion of a Funding close after its perpetual leg filled."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.database import connection
from app.execution_exposure import exposure_evidence
from app.security import assert_live_account_execution_allowed
from app.strategies import funding_orchestration as execution
from app.strategies.domain import ExecutionPlan
from app.strategies.plan_service import funding_account_binding, validate_funding_plan_markets
from app.venue_reconciliation_service import reconcile_order_with_venue


def close_recovery_details(instruction_id: str, *, db=None):
    if db is None:
        with connection() as local:
            return close_recovery_details(instruction_id, db=local)
    row = db.execute(
        "SELECT r.*,b.status AS batch_status FROM strategy_runs r "
        "JOIN execution_batches b ON b.id=r.execution_batch_id "
        "WHERE r.id=? AND r.strategy_key='funding_arbitrage' AND r.action='close'",
        (instruction_id,),
    ).fetchone()
    if (
        row is None
        or row["status"] not in {"failed", "manual_intervention"}
        or row["batch_status"] not in {"failed", "manual_intervention"}
    ):
        return None
    plan = ExecutionPlan.model_validate_json(row["execution_plan_json"])
    legs = {leg.role: leg for leg in plan.legs}
    if set(legs) != {"perpetual_leg", "spot_leg"} or plan.action.value != "close":
        return None
    perp, spot = legs["perpetual_leg"], legs["spot_leg"]
    if (
        not perp.reduce_only
        or perp.side != "buy"
        or spot.side != "sell"
        or perp.account_id != spot.account_id
    ):
        return None
    batch_id = row["execution_batch_id"]
    _, _, quality, proof = exposure_evidence(db, batch_id)
    if quality != "complete":
        return None
    if db.execute(
        "SELECT 1 FROM funding_spot_release_commands WHERE batch_id=? "
        "AND status NOT IN ('filled','failed','rejected','canceled') "
        "UNION SELECT 1 FROM execution_risk_actions WHERE batch_id=? "
        "AND action!='hold_and_escalate' LIMIT 1",
        (batch_id, batch_id),
    ).fetchone():
        return None
    quantities = {perp.instrument_id: Decimal(0), spot.instrument_id: Decimal(0)}
    for item in proof:
        order = db.execute("SELECT * FROM orders WHERE id=?", (item["orderId"],)).fetchone()
        leg = next((leg for leg in plan.legs if leg.instrument_id == order["instrument_id"]), None)
        if leg is None or order["account_id"] != leg.account_id or order["side"] != leg.side:
            return None
        quantities[leg.instrument_id] += Decimal(item["quantity"])
    if quantities[perp.instrument_id] != perp.maximum_quantity:
        return None
    remaining = spot.maximum_quantity - quantities[spot.instrument_id]
    if remaining <= 0 or remaining % spot.quantity_step:
        return None
    # A child without an order is eligible only when admission definitively rejected it.
    releases = db.execute(
        "SELECT * FROM funding_spot_release_commands WHERE batch_id=?", (batch_id,)
    ).fetchall()
    for release in releases:
        if release["order_id"]:
            continue
        key = execution._spot_child_idempotency_key(
            request_idempotency_key=row["idempotency_key"], child_id=release["child_id"]
        )
        command = db.execute(
            "SELECT c.status,o.id AS order_id FROM trade_commands c "
            "LEFT JOIN orders o ON o.command_id=c.id WHERE c.idempotency_key=?",
            (key,),
        ).fetchone()
        if command is None or command["status"] != "rejected" or command["order_id"] is not None:
            return None
    target = str(json.loads(row["requested_parameters_json"]).get("targetOpenInstructionId") or "")
    original = db.execute(
        "SELECT execution_plan_json FROM strategy_runs WHERE id=? "
        "AND action='open' AND strategy_instance_id=?",
        (target, row["strategy_instance_id"]),
    ).fetchone()
    if original is None:
        return None
    original_plan = ExecutionPlan.model_validate_json(original[0])
    if {(leg.role, leg.account_id, leg.instrument_id) for leg in original_plan.legs} != {
        (leg.role, leg.account_id, leg.instrument_id) for leg in plan.legs
    }:
        return None
    return {
        "instruction": dict(row),
        "plan": plan,
        "perp": perp,
        "spot": spot,
        "remaining": remaining,
        "target": target,
        "proof": proof,
        "key": f"funding-close-recovery:{instruction_id}:{len(releases)}",
    }


def has_completed_close_recovery(batch_id: str) -> bool:
    with connection() as db:
        row = db.execute(
            "SELECT execution_plan_json FROM strategy_runs WHERE execution_batch_id=? "
            "AND action='close' AND strategy_key='funding_arbitrage'",
            (batch_id,),
        ).fetchone()
        recovery = db.execute(
            "SELECT 1 FROM funding_spot_release_commands WHERE batch_id=? "
            "AND child_id LIKE 'funding-close-recovery:%' AND status='filled'",
            (batch_id,),
        ).fetchone()
        if row is None or recovery is None:
            return False
        if db.execute(
            "SELECT 1 FROM funding_spot_release_commands WHERE batch_id=? "
            "AND status NOT IN ('filled','failed','rejected','canceled')",
            (batch_id,),
        ).fetchone():
            return False
        _, _, quality, _ = exposure_evidence(db, batch_id)
    plan = ExecutionPlan.model_validate_json(row[0])
    legs = {leg.role: leg for leg in plan.legs}
    return (
        quality == "complete"
        and execution._latest_perpetual_cumulative_fill(batch_id)
        == legs["perpetual_leg"].maximum_quantity
        and execution._filled_cumulative_spot(batch_id) == legs["spot_leg"].maximum_quantity
    )


def pending_recovery_reconciliation(instruction_id: str):
    """Expose an existing recovery identity until its final reconciliation completes."""
    with connection() as db:
        row = db.execute(
            "SELECT * FROM strategy_runs WHERE id=? AND action='close' "
            "AND strategy_key='funding_arbitrage' AND status='manual_intervention'",
            (instruction_id,),
        ).fetchone()
        if row is None:
            return None
        child = db.execute(
            "SELECT child_id,order_id FROM funding_spot_release_commands WHERE batch_id=? "
            "AND child_id LIKE 'funding-close-recovery:%' "
            "AND status IN ('filled','result_unknown','declared','processing',"
            "'accepted','acknowledged') "
            "ORDER BY created_at DESC LIMIT 1",
            (row["execution_batch_id"],),
        ).fetchone()
        if child is None:
            return None
        audit = db.execute(
            "SELECT details_json FROM audit_events "
            "WHERE event_type='funding_close_recovery_confirmed' "
            "AND subject_id=? AND json_extract(details_json,'$.childId')=?",
            (instruction_id, child["child_id"]),
        ).fetchone()
        if audit is None:
            return None
    return {
        "target": json.loads(row["requested_parameters_json"])["targetOpenInstructionId"],
        "instruction": dict(row),
        "remaining": Decimal(0),
        "key": json.loads(audit[0])["idempotencyKey"],
        "reconcileOnly": True,
    }


def unsubmitted_release_rejection(batch_id: str, release) -> bool:
    with connection() as db:
        row = db.execute(
            "SELECT idempotency_key FROM strategy_runs WHERE execution_batch_id=?", (batch_id,)
        ).fetchone()
        if (
            row is None
            or release.order_id is not None
            or release.status not in {"failed", "rejected"}
        ):
            return False
        key = execution._spot_child_idempotency_key(
            request_idempotency_key=row[0], child_id=release.child_id
        )
        command = db.execute(
            "SELECT c.status,o.id AS order_id FROM trade_commands c "
            "LEFT JOIN orders o ON o.command_id=c.id WHERE c.idempotency_key=?",
            (key,),
        ).fetchone()
        return (
            command is not None and command["status"] == "rejected" and command["order_id"] is None
        )


def confirmed_native_rejection(order_id: str) -> bool:
    """Absence is insufficient: require the exact Runtime rejection event."""
    with connection() as db:
        order = db.execute(
            "SELECT o.*,c.status AS command_status FROM orders o JOIN trade_commands c "
            "ON c.id=o.command_id WHERE o.id=?",
            (order_id,),
        ).fetchone()
        if (
            order is None
            or order["status"] != "rejected"
            or order["command_status"] != "rejected"
            or order["external_order_id"]
        ):
            return False
        if db.execute("SELECT 1 FROM fills WHERE order_id=?", (order_id,)).fetchone():
            return False
    events = execution._runtime_get(f"/commands/{order['command_id']}/events", allow_not_found=True)
    return (
        bool(events)
        and isinstance(events, list)
        and all(
            event.get("event_type") == "order_rejected"
            and event.get("command_id") == order["command_id"]
            and event.get("platform_order_id") == order_id
            and not event.get("external_order_id")
            and not event.get("fill_quantity")
            for event in events
        )
    )


def recover_funding_close(instruction_id: str, idempotency_key: str, actor: str):
    from app.strategies.funding_workspace import get_funding_instruction_workspace

    digest = hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]
    child_id = f"funding-close-recovery:{instruction_id}:{digest}"
    with connection() as db:
        existing = db.execute(
            "SELECT batch_id FROM funding_spot_release_commands WHERE child_id=?", (child_id,)
        ).fetchone()
    if existing is not None:
        # A lost response never creates a second child or repeats a Venue write.
        _finish_existing_recovery(instruction_id, existing["batch_id"], child_id)
        return get_funding_instruction_workspace(instruction_id)
    details = close_recovery_details(instruction_id)
    if details is None or idempotency_key != details["key"]:
        raise HTTPException(409, "原平仓成交或恢复身份已变化，请刷新核对；不会重复平永续")
    row, plan, perp, spot = (details[key] for key in ("instruction", "plan", "perp", "spot"))
    batch_id = row["execution_batch_id"]
    with connection() as db:
        binding = funding_account_binding(db, row["strategy_instance_id"])
    if binding["account_id"] != spot.account_id:
        raise HTTPException(409, "原平仓账户与当前绑定不一致")
    assert_live_account_execution_allowed(spot.account_id, row["strategy_instance_id"])
    validate_funding_plan_markets(plan)
    for item in details["proof"]:
        if confirmed_native_rejection(item["orderId"]):
            continue
        reconciled = reconcile_order_with_venue(item["orderId"])
        if reconciled.difference_ids:
            raise HTTPException(409, "原平仓委托及成交尚未核对一致")
    _verify_remaining_inventory(details)
    execution._claim_funding_batch(
        instruction_id=instruction_id,
        batch_id=batch_id,
        strategy_instance_id=row["strategy_instance_id"],
        account_ids=[spot.account_id],
        legs=list(plan.legs),
    )
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        current = close_recovery_details(instruction_id, db=db)
        if (
            current is None
            or current["key"] != idempotency_key
            or current["remaining"] != details["remaining"]
        ):
            raise HTTPException(409, "平仓恢复已由其他请求处理，请核对原指令")
        stamp = datetime.now(UTC).isoformat()
        db.execute(
            "INSERT INTO funding_spot_release_commands(child_id,batch_id,cumulative_perpetual_fill,"
            "release_quantity,cumulative_spot_quantity,status,created_at,updated_at) "
            "VALUES(?,?,?,?,?,'declared',?,?)",
            (
                child_id,
                batch_id,
                str(perp.maximum_quantity),
                str(details["remaining"]),
                str(spot.maximum_quantity),
                stamp,
                stamp,
            ),
        )
        db.execute(
            "INSERT INTO audit_events(id,event_type,subject_type,subject_id,"
            "details_json,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (
                str(uuid4()),
                "funding_close_recovery_confirmed",
                "strategy_instruction",
                instruction_id,
                json.dumps(
                    {
                        "actor": actor,
                        "idempotencyKey": idempotency_key,
                        "childId": child_id,
                        "spotQuantity": str(details["remaining"]),
                        "orders": details["proof"],
                    }
                ),
                stamp,
            ),
        )
    try:
        execution._submit_spot_release(
            instruction_id=instruction_id,
            batch_id=batch_id,
            strategy_instance_id=row["strategy_instance_id"],
            request_idempotency_key=row["idempotency_key"],
            spot_leg=spot,
            child_id=child_id,
            quantity=details["remaining"],
        )
        _finish_existing_recovery(instruction_id, batch_id, child_id)
    except Exception as exc:
        execution._manual_intervention(instruction_id, batch_id, str(exc))
        raise
    return get_funding_instruction_workspace(instruction_id)


def _finish_existing_recovery(instruction_id: str, batch_id: str, child_id: str):
    """Retry only authoritative reads after a submitted child; never dispatch it again."""
    with connection() as db:
        row = db.execute(
            "SELECT status,execution_plan_json FROM strategy_runs WHERE id=?", (instruction_id,)
        ).fetchone()
        child = db.execute(
            "SELECT order_id,status FROM funding_spot_release_commands "
            "WHERE child_id=? AND batch_id=?",
            (child_id, batch_id),
        ).fetchone()
    if row is None or row["status"] == "completed" or child is None or not child["order_id"]:
        return
    if child["status"] in {"failed", "rejected", "canceled"}:
        return
    reconciled = reconcile_order_with_venue(child["order_id"])
    if reconciled.difference_ids:
        raise HTTPException(409, "补平现货成交尚未核对一致")
    with connection() as db:
        order = db.execute("SELECT status FROM orders WHERE id=?", (child["order_id"],)).fetchone()
        if order is None or order["status"] != "filled":
            return
        db.execute(
            "UPDATE funding_spot_release_commands SET status='filled',updated_at=? "
            "WHERE child_id=?",
            (datetime.now(UTC).isoformat(), child_id),
        )
    plan = ExecutionPlan.model_validate_json(row["execution_plan_json"])
    legs = {leg.role: leg for leg in plan.legs}
    execution._refresh_batch_after_release(
        instruction_id, batch_id, legs["perpetual_leg"], legs["spot_leg"]
    )
    if execution._batch_status(batch_id) == "hedged":
        execution._complete_reconciliation(
            instruction_id, batch_id, legs["perpetual_leg"], legs["spot_leg"]
        )


def _verify_remaining_inventory(details):
    from app.strategies.funding_workspace import list_funding_position_groups

    perp, spot = details["perp"], details["spot"]
    group = next(
        (
            g
            for g in list_funding_position_groups(scope="all")
            if g["instructionId"] == details["target"]
        ),
        None,
    )
    if (
        group is None
        or group["remainingSpotHolding"] is None
        or Decimal(group["remainingSpotHolding"]) < details["remaining"]
    ):
        raise HTTPException(409, "原组合现货剩余持币不足或缺少手续费证据")
    positions = execution._runtime_get("/venue/positions", params={"accountId": perp.account_id})
    risk = execution._runtime_get("/venue/account-risk", params={"accountId": perp.account_id})
    balances = execution._runtime_get("/venue/balances", params={"accountId": spot.account_id})
    if (
        not isinstance(positions, list)
        or not isinstance(balances, list)
        or not isinstance(risk, dict)
        or risk.get("accountId") != perp.account_id
        or risk.get("dataQualityState") != "complete"
    ):
        raise HTTPException(409, "原生仓位及余额不可核实")
    if any(p.get("accountId") != perp.account_id for p in positions):
        raise HTTPException(409, "原生仓位账户不一致")
    actual = sum(
        (Decimal(p["netQuantity"]) for p in positions if p["instrumentId"] == perp.instrument_id),
        Decimal(0),
    )
    expected, _, _ = execution._account_fill_position(perp, [])
    if actual != expected:
        raise HTTPException(409, "原生永续剩余仓位与已记录成交不一致")
    with connection() as db:
        currency = db.execute(
            "SELECT base_currency FROM instruments WHERE id=?", (spot.instrument_id,)
        ).fetchone()[0]
    cash = [
        b
        for b in balances
        if b.get("currency") == currency and b.get("accountId") == spot.account_id
    ]
    if (
        len(cash) != 1
        or cash[0].get("dataQualityState") != "complete"
        or Decimal(str(cash[0].get("availableBalance") or "0")) < details["remaining"]
    ):
        raise HTTPException(409, "原生现货可卖余额不足或不可核实")
    stamp = datetime.fromisoformat(str(cash[0]["asOf"]).replace("Z", "+00:00"))
    if stamp.tzinfo is None or not -5 <= (datetime.now(UTC) - stamp).total_seconds() <= 120:
        raise HTTPException(409, "原生现货余额已过期")
