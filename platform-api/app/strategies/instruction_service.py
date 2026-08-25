from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.database import connection
from app.execution_batches import (
    create_execution_batch,
    get_execution_batch,
    update_batch_status,
)
from app.execution_schemas import (
    BatchLegRequest,
    CreateExecutionBatchRequest,
    ExecutionBatchResponse,
)
from app.strategies.domain import (
    ExecutionPlan,
    ExecutionPlanLeg,
    ExecutionPolicy,
    StrategyInstructionAction,
    StrategyInstructionStatus,
)
from app.strategies.funding_orchestration import execute_funding_instruction
from app.strategies.plan_service import build_plan, normalize_parameters


class CreateStrategyInstructionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    action: StrategyInstructionAction
    parameters: dict[str, object]
    position_group_id: str | None = Field(default=None, alias="positionGroupId")
    reason: str | None = Field(default=None, max_length=256)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _json_plan(plan: ExecutionPlan) -> str:
    return plan.model_dump_json(by_alias=False)


def _camel(value: object) -> object:
    if isinstance(value, dict):
        converted: dict[str, object] = {}
        for key, item in value.items():
            camel_key = (
                key.split("_")[0] + "".join(part.title() for part in key.split("_")[1:])
                if "_" in key
                else key
            )
            # Map keys are business identifiers, not API field names.  Converting
            # them corrupts account IDs such as account_sim_usdt.
            converted[camel_key] = (
                {str(identifier): _camel(capability) for identifier, capability in item.items()}
                if key == "account_capability_snapshot" and isinstance(item, dict)
                else _camel(item)
            )
        return converted
    if isinstance(value, list):
        return [_camel(item) for item in value]
    if isinstance(value, tuple):
        return [_camel(item) for item in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    return value


def _response(row) -> dict[str, object]:
    plan = json.loads(row["execution_plan_json"])
    return {
        "instructionId": row["id"],
        "idempotencyKey": row["idempotency_key"],
        "strategyInstanceId": row["strategy_instance_id"],
        "strategyKey": row["strategy_key"],
        "action": row["action"],
        "status": row["status"],
        "positionGroupId": row["position_group_id"],
        "requestedBy": row["requested_by"],
        "requestedParameters": json.loads(row["requested_parameters_json"]),
        "executionPlan": _camel(plan),
        "executionBatchId": row["execution_batch_id"],
        "reason": row["reason"],
        "failureReason": row["failure_reason"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def get_instruction(instruction_id: str) -> dict[str, object]:
    with connection() as db:
        row = db.execute("SELECT * FROM strategy_runs WHERE id = ?", (instruction_id,)).fetchone()
    if row is None or row["execution_plan_json"] is None:
        raise HTTPException(status_code=404, detail="Strategy instruction not found")
    return _response(row)


def list_instructions(strategy_instance_id: str) -> list[dict[str, object]]:
    with connection() as db:
        rows = db.execute(
            (
                "SELECT * FROM strategy_runs WHERE strategy_instance_id = ? "
                "AND execution_plan_json IS NOT NULL ORDER BY created_at DESC"
            ),
            (strategy_instance_id,),
        ).fetchall()
    return [_response(row) for row in rows]


def attach_legacy_batch_to_instruction(
    *,
    instruction_id: str,
    batch_id: str,
    strategy_key: str,
    action: str,
    parameters: dict[str, object],
    legs: list[BatchLegRequest],
    requested_by: str,
) -> None:
    """Freeze an old endpoint's already-authorised request on its one batch.

    This is compatibility glue: old response contracts still execute through
    their proven batch path, but the business record is now an Instruction.
    """
    with connection() as db:
        plan_legs = []
        capabilities: dict[str, str] = {}
        for sequence, leg in enumerate(legs, start=1):
            spec = db.execute(
                """
                SELECT min_order_quantity, quantity_step, contract_multiplier
                FROM contract_specifications WHERE instrument_id = ?
                AND data_quality_state = 'complete'
                """,
                (leg.instrument_id,),
            ).fetchone()
            if spec is None:
                raise HTTPException(
                    status_code=422, detail="Legacy leg contract specification is unavailable"
                )
            account_id = leg.account_id
            if account_id is None:
                raise HTTPException(status_code=422, detail="Legacy leg account is unavailable")
            capabilities[account_id] = "trade_and_read"
            plan_legs.append(
                ExecutionPlanLeg(
                    role=leg.role,
                    account_id=account_id,
                    instrument_id=leg.instrument_id,
                    external_symbol=leg.symbol,
                    side=leg.side,
                    maximum_quantity=leg.quantity,
                    sequence=sequence,
                    execution_policy=(
                        ExecutionPolicy.MARKET
                        if leg.order_type == "market"
                        else ExecutionPolicy.POST_ONLY_CHASE
                    ),
                    quantity_step=Decimal(spec["quantity_step"]),
                    contract_multiplier=Decimal(spec["contract_multiplier"]),
                    minimum_quantity=Decimal(spec["min_order_quantity"]),
                )
            )
        plan = ExecutionPlan(
            adapter_version="legacy_batch.v1",
            strategy_key=strategy_key,
            action=StrategyInstructionAction.OPEN,
            legs=tuple(plan_legs),
            account_capability_snapshot=capabilities,
            created_at=datetime.now(UTC),
        )
        db.execute(
            """
            UPDATE execution_batches SET strategy_instruction_id = ? WHERE id = ?
            """,
            (instruction_id, batch_id),
        )
        db.execute(
            """
            UPDATE strategy_runs
            SET action = ?, requested_parameters_json = ?, execution_plan_json = ?,
                requested_by = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                action,
                _canonical(parameters),
                _json_plan(plan),
                requested_by,
                _utc_now(),
                instruction_id,
            ),
        )


def create_instruction(
    strategy_instance_id: str,
    request: CreateStrategyInstructionRequest,
    *,
    requested_by: str,
) -> dict[str, object]:
    with connection() as db:
        instance = db.execute(
            """
            SELECT sd.strategy_key
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ?
            """,
            (strategy_instance_id,),
        ).fetchone()
    strategy_key = str(instance["strategy_key"]) if instance is not None else None
    if request.action is StrategyInstructionAction.RISK_DISPOSITION:
        raise HTTPException(status_code=423, detail="Position Group close planning is unavailable")
    if (
        request.action is StrategyInstructionAction.CLOSE
        and strategy_key != "funding_arbitrage"
    ):
        # Position Groups are not materialised in Phase 0–1. Funding is the
        # only strategy that now has a bounded, strategy-owned close path.
        raise HTTPException(status_code=423, detail="Position Group close planning is unavailable")
    normalized_parameters = normalize_parameters(strategy_instance_id, request.parameters)
    requested_json = _canonical(normalized_parameters)
    request_fingerprint = _canonical(
        {
            "action": request.action.value,
            "parameters": normalized_parameters,
            "position_group_id": request.position_group_id,
            "reason": request.reason,
            "strategy_instance_id": strategy_instance_id,
        }
    )
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM strategy_runs WHERE idempotency_key = ?", (request.idempotency_key,)
        ).fetchone()
        if existing is not None:
            if existing["request_fingerprint"] == request_fingerprint:
                return _response(existing)
            raise HTTPException(
                status_code=409,
                detail=(
                    "Idempotency key is already used by a different strategy instruction payload"
                ),
            )
        plan = build_plan(strategy_instance_id, request.action, normalized_parameters)
        instruction_id, batch_id, timestamp = str(uuid4()), str(uuid4()), _utc_now()
        first_leg = plan.legs[0]
        db.execute(
            """INSERT INTO execution_batches (
                id, idempotency_key, strategy_instruction_id,
                strategy_instance_id, account_id, strategy_key, direction,
                status, requires_manual_intervention, failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, NULL, ?, ?)""",
            (
                batch_id,
                f"instruction:{request.idempotency_key}",
                instruction_id,
                strategy_instance_id,
                first_leg.account_id,
                plan.strategy_key,
                request.action.value,
                timestamp,
                timestamp,
            ),
        )
        db.execute(
            """INSERT INTO strategy_runs (
                id, idempotency_key, strategy_instance_id, strategy_key, direction,
                action, position_group_id, requested_parameters_json, request_fingerprint,
                execution_plan_json,
                requested_by, status, execution_batch_id, reason, failure_reason,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                instruction_id,
                request.idempotency_key,
                strategy_instance_id,
                plan.strategy_key,
                request.action.value,
                request.action.value,
                request.position_group_id,
                requested_json,
                request_fingerprint,
                _json_plan(plan),
                requested_by,
                StrategyInstructionStatus.ACCEPTED.value,
                batch_id,
                request.reason,
                None,
                timestamp,
                timestamp,
            ),
        )
        for leg in plan.legs:
            order_type = "limit" if leg.execution_policy.value == "post_only_chase" else "market"
            db.execute(
                """INSERT INTO execution_batch_legs (
                    id, batch_id, sequence, role, account_id, instrument_id, symbol,
                    side, order_type, quantity, price, order_id, status,
                    failure_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'pending', NULL, ?, ?)""",
                (
                    str(uuid4()),
                    batch_id,
                    leg.sequence,
                    leg.role,
                    leg.account_id,
                    leg.instrument_id,
                    leg.external_symbol,
                    leg.side,
                    order_type,
                    format(leg.maximum_quantity, "f"),
                    timestamp,
                    timestamp,
                ),
            )
        row = db.execute("SELECT * FROM strategy_runs WHERE id = ?", (instruction_id,)).fetchone()
    return _response(row)


def execute_instruction(
    instruction_id: str,
) -> ExecutionBatchResponse:
    """Dispatch an instruction's atomically declared Batch exactly once.

    The immutable plan is the execution-policy authority. Unsupported policies
    fail closed; this seam never rewrites a persisted Batch leg at dispatch time.
    """
    timestamp = _utc_now()
    with connection() as db:
        instruction = db.execute(
            "SELECT * FROM strategy_runs WHERE id = ?", (instruction_id,)
        ).fetchone()
        if instruction is None or instruction["execution_plan_json"] is None:
            raise HTTPException(status_code=404, detail="Strategy instruction not found")
        plan = ExecutionPlan.model_validate_json(instruction["execution_plan_json"])
        if plan.strategy_key == "funding_arbitrage":
            return execute_funding_instruction(
                instruction_id,
                instruction_row=instruction,
                plan=plan,
            )
        unsupported = [
            leg.execution_policy.value
            for leg in plan.legs
            if leg.execution_policy is not ExecutionPolicy.MARKET
        ]
        if unsupported:
            detail = (
                "Execution Plan policy is unavailable in the Phase 0-1 shared executor: "
                + ", ".join(dict.fromkeys(unsupported))
            )
            update_batch_status(instruction["execution_batch_id"], "failed", failure_reason=detail)
            _update_instruction_result(
                instruction_id,
                StrategyInstructionStatus.REJECTED,
                failure_reason=detail,
            )
            raise HTTPException(status_code=423, detail=detail)
        db.execute(
            """
            UPDATE strategy_runs SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (
                StrategyInstructionStatus.EXECUTING.value,
                timestamp,
                instruction_id,
                StrategyInstructionStatus.ACCEPTED.value,
            ),
        )

    request = CreateExecutionBatchRequest(
        idempotencyKey=f"instruction:{instruction['idempotency_key']}",
        strategyInstanceId=instruction["strategy_instance_id"],
        accountId=plan.legs[0].account_id,
        strategyKey=instruction["strategy_key"],
        direction=plan.action.value,
        legs=[
            BatchLegRequest(
                role=leg.role,
                accountId=leg.account_id,
                instrumentId=leg.instrument_id,
                symbol=leg.external_symbol,
                side=leg.side,
                orderType="market",
                quantity=leg.maximum_quantity,
            )
            for leg in plan.legs
        ],
    )
    try:
        result = create_execution_batch(request)
    except HTTPException as exc:
        _synchronise_instruction_after_dispatch_error(instruction_id, str(exc.detail))
        raise
    except Exception as exc:
        _synchronise_instruction_after_dispatch_error(instruction_id, str(exc))
        raise
    status = {
        "hedged": StrategyInstructionStatus.COMPLETED,
        "completed": StrategyInstructionStatus.COMPLETED,
        "manual_intervention": StrategyInstructionStatus.MANUAL_INTERVENTION,
        "failed": StrategyInstructionStatus.FAILED,
    }.get(result.status, StrategyInstructionStatus.EXECUTING)
    _update_instruction_result(instruction_id, status, failure_reason=result.failure_reason)
    return result


def _synchronise_instruction_after_dispatch_error(
    instruction_id: str,
    failure_reason: str,
) -> None:
    with connection() as db:
        row = db.execute(
            "SELECT execution_batch_id FROM strategy_runs WHERE id = ?",
            (instruction_id,),
        ).fetchone()
    if row is None or row["execution_batch_id"] is None:
        return
    batch = get_execution_batch(row["execution_batch_id"])
    if batch.status == "pending":
        update_batch_status(batch.batch_id, "failed", failure_reason=failure_reason)
        status = StrategyInstructionStatus.REJECTED
    elif batch.status == "failed":
        status = StrategyInstructionStatus.FAILED
    else:
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=failure_reason,
            requires_manual_intervention=True,
        )
        status = StrategyInstructionStatus.MANUAL_INTERVENTION
    _update_instruction_result(instruction_id, status, failure_reason=failure_reason)


def _update_instruction_result(
    instruction_id: str,
    status: StrategyInstructionStatus,
    *,
    failure_reason: str | None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE strategy_runs
            SET status = ?, failure_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (status.value, failure_reason, _utc_now(), instruction_id),
        )
