"""Persist one optional, one-shot spread exit per original Funding opening."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.database import connection
from app.strategies.funding_schemas import FundingExitPlanRequest, FundingExitPlanResponse


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _audit(db, event: str, open_id: str, payload: dict) -> None:
    db.execute(
        "INSERT INTO audit_events(id,event_type,subject_type,subject_id,details_json,created_at) "
        "VALUES (?,?,'funding_exit_plan',?,?,?)",
        (str(uuid4()), event, open_id, json.dumps(payload, default=str), _now()),
    )


def list_plans(*, pending_only: bool = False) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM funding_exit_plans "
            + ("WHERE enabled=1 AND close_instruction_id IS NULL " if pending_only else "")
            + "ORDER BY open_instruction_id"
        ).fetchall()
    return [dict(row) for row in rows]


def response(row: dict[str, Any]) -> FundingExitPlanResponse:
    trigger = json.loads(row["trigger_json"]) if row["trigger_json"] else {}
    return FundingExitPlanResponse(
        openInstructionId=row["open_instruction_id"],
        revision=row["revision"],
        enabled=bool(row["enabled"]),
        takeProfitSpread=row["take_profit_spread"],
        stopLossSpread=row["stop_loss_spread"],
        triggerReason=trigger.get("reason"),
        triggerSpread=trigger.get("spread"),
        triggeredAt=trigger.get("triggeredAt"),
        closeInstructionId=row["close_instruction_id"],
        lastError=row["last_error"],
        updatedAt=row["updated_at"],
    )


def save_plan(
    open_id: str, account_id: str, request: FundingExitPlanRequest, *, actor: str
) -> FundingExitPlanResponse:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute(
            "SELECT * FROM funding_exit_plans WHERE open_instruction_id=?", (open_id,)
        ).fetchone()
        revision = current["revision"] if current else 0
        if current and current["close_key"]:
            raise ValueError("自动平仓已触发，请按原平仓指令核对或处理，不能重置触发身份")
        if revision != request.expectedRevision:
            raise ValueError("自动平仓设置已变化，请刷新后重新确认")
        db.execute(
            "INSERT INTO funding_exit_plans(open_instruction_id,account_id,revision,enabled,"
            "take_profit_spread,stop_loss_spread,configured_by,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(open_instruction_id) DO UPDATE SET revision=excluded.revision,"
            "enabled=excluded.enabled,take_profit_spread=excluded.take_profit_spread,"
            "stop_loss_spread=excluded.stop_loss_spread,configured_by=excluded.configured_by,"
            "last_error=NULL,updated_at=excluded.updated_at",
            (
                open_id,
                account_id,
                revision + 1,
                int(request.enabled),
                str(request.takeProfitSpread) if request.takeProfitSpread is not None else None,
                str(request.stopLossSpread) if request.stopLossSpread is not None else None,
                actor,
                _now(),
            ),
        )
        _audit(
            db,
            "funding_exit_plan_configured",
            open_id,
            {**request.model_dump(mode="json"), "actor": actor, "revision": revision + 1},
        )
        row = db.execute(
            "SELECT * FROM funding_exit_plans WHERE open_instruction_id=?", (open_id,)
        ).fetchone()
    return response(dict(row))


def claim_trigger(plan: dict[str, Any], trigger: dict[str, Any]) -> dict[str, Any] | None:
    open_id = plan["open_instruction_id"]
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        changed = db.execute(
            "UPDATE funding_exit_plans SET close_key=?,trigger_json=?,updated_at=?,last_error=NULL "
            "WHERE open_instruction_id=? AND revision=? AND enabled=1 AND close_key IS NULL",
            (f"funding-exit:{open_id}", json.dumps(trigger), _now(), open_id, plan["revision"]),
        )
        if changed.rowcount != 1:
            return None
        _audit(db, "funding_exit_plan_triggered", open_id, trigger)
        row = db.execute(
            "SELECT * FROM funding_exit_plans WHERE open_instruction_id=?", (open_id,)
        ).fetchone()
    return dict(row)


def attach_close(open_id: str, close_id: str) -> None:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        plan = db.execute(
            "SELECT * FROM funding_exit_plans WHERE open_instruction_id=?", (open_id,)
        ).fetchone()
        run = db.execute("SELECT * FROM strategy_runs WHERE id=?", (close_id,)).fetchone()
        if (
            not plan
            or not plan["close_key"]
            or not run
            or run["action"] != "close"
            or run["idempotency_key"] != plan["close_key"]
            or json.loads(run["requested_parameters_json"]).get("targetOpenInstructionId")
            != open_id
        ):
            raise ValueError("自动平仓与原持仓身份不一致")
        if plan["close_instruction_id"] and plan["close_instruction_id"] != close_id:
            raise ValueError("自动平仓已关联其他指令")
        if plan["close_instruction_id"] == close_id:
            return
        db.execute(
            "UPDATE funding_exit_plans SET close_instruction_id=?,last_error=NULL,updated_at=? "
            "WHERE open_instruction_id=?",
            (close_id, _now(), open_id),
        )
        _audit(db, "funding_exit_plan_close_linked", open_id, {"closeInstructionId": close_id})


def set_error(open_id: str, error: str | None) -> None:
    with connection() as db:
        db.execute(
            "UPDATE funding_exit_plans SET last_error=?,updated_at=? "
            "WHERE open_instruction_id=? AND last_error IS NOT ?",
            (error, _now(), open_id, error),
        )
