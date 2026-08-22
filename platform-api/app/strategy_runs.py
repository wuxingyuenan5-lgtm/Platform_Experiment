from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.database import connection
from app.execution_batches import create_execution_batch, get_execution_batch
from app.schemas import (
    CreateExecutionBatchRequest,
    CreateStrategyRunRequest,
    ExecutionBatchResponse,
    StrategyRunResponse,
)
from app.strategies.instruction_service import attach_legacy_batch_to_instruction


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_strategy_run(
    strategy_instance_id: str,
    request: CreateStrategyRunRequest,
    *,
    requested_by: str,
) -> StrategyRunResponse:
    existing_run_id = find_strategy_run_by_idempotency_key(request.idempotency_key)
    if existing_run_id is not None:
        return get_strategy_run(existing_run_id)

    strategy_key = get_runnable_strategy_key(strategy_instance_id)
    run_id = str(uuid4())
    created_at = now_iso()

    with connection() as db:
        db.execute(
            """
            INSERT INTO strategy_runs (
                id, idempotency_key, strategy_instance_id, strategy_key, direction,
                status, execution_batch_id, reason, failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                request.idempotency_key,
                strategy_instance_id,
                strategy_key,
                request.direction,
                "pending",
                None,
                request.reason,
                None,
                created_at,
                created_at,
            ),
        )

    update_strategy_run_status(run_id, "executing")
    batch = create_execution_batch(
        CreateExecutionBatchRequest(
            idempotencyKey=f"strategy-run:{request.idempotency_key}",
            strategyInstanceId=strategy_instance_id,
            strategyKey=strategy_key,
            direction=request.direction,
            legs=request.legs,
        )
    )
    attach_legacy_batch_to_instruction(
        instruction_id=run_id,
        batch_id=batch.batch_id,
        strategy_key=strategy_key,
        action=request.direction,
        parameters=request.model_dump(by_alias=True, mode="json"),
        legs=request.legs,
        requested_by=requested_by,
    )
    final_status = map_batch_status(batch)
    update_strategy_run_status(
        run_id,
        final_status,
        execution_batch_id=batch.batch_id,
        failure_reason=batch.failure_reason,
    )
    return get_strategy_run(run_id)


def list_strategy_runs(strategy_instance_id: str) -> list[StrategyRunResponse]:
    get_runnable_or_existing_strategy_key(strategy_instance_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT id
            FROM strategy_runs
            WHERE strategy_instance_id = ?
            ORDER BY created_at DESC
            """,
            (strategy_instance_id,),
        ).fetchall()
    return [get_strategy_run(row["id"]) for row in rows]


def get_strategy_run(strategy_run_id: str) -> StrategyRunResponse:
    with connection() as db:
        row = db.execute(
            """
            SELECT id, idempotency_key, strategy_instance_id, strategy_key, direction,
                   status, execution_batch_id, reason, failure_reason, created_at, updated_at
            FROM strategy_runs
            WHERE id = ?
            """,
            (strategy_run_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy run not found")

    execution_batch: ExecutionBatchResponse | None = None
    if row["execution_batch_id"] is not None:
        execution_batch = get_execution_batch(row["execution_batch_id"])

    return StrategyRunResponse(
        strategyRunId=row["id"],
        idempotencyKey=row["idempotency_key"],
        strategyInstanceId=row["strategy_instance_id"],
        strategyKey=row["strategy_key"],
        direction=row["direction"],
        status=row["status"],
        executionBatchId=row["execution_batch_id"],
        executionBatch=execution_batch,
        reason=row["reason"],
        failureReason=row["failure_reason"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def find_strategy_run_by_idempotency_key(idempotency_key: str) -> str | None:
    with connection() as db:
        row = db.execute(
            "SELECT id FROM strategy_runs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
    return row["id"] if row is not None else None


def get_runnable_strategy_key(strategy_instance_id: str) -> str:
    row = get_strategy_instance_row(strategy_instance_id)
    if row["v1_scope"] != "closed_loop" or row["instance_status"] != "active":
        raise HTTPException(status_code=422, detail="Strategy instance is not runnable in V1")
    return row["strategy_key"]


def get_runnable_or_existing_strategy_key(strategy_instance_id: str) -> str:
    row = get_strategy_instance_row(strategy_instance_id)
    return row["strategy_key"]


def get_strategy_instance_row(strategy_instance_id: str):
    with connection() as db:
        row = db.execute(
            """
            SELECT sd.strategy_key, sd.v1_scope, si.status AS instance_status
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ?
            """,
            (strategy_instance_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy instance not found")
    return row


def update_strategy_run_status(
    strategy_run_id: str,
    status: str,
    *,
    execution_batch_id: str | None = None,
    failure_reason: str | None = None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE strategy_runs
            SET status = ?,
                execution_batch_id = COALESCE(?, execution_batch_id),
                failure_reason = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (status, execution_batch_id, failure_reason, now_iso(), strategy_run_id),
        )


def map_batch_status(batch: ExecutionBatchResponse) -> str:
    if batch.status == "hedged":
        return "completed"
    if batch.status == "manual_intervention":
        return "manual_intervention"
    if batch.status == "failed":
        return "failed"
    return "executing"
