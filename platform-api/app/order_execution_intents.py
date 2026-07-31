from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException

from app.database import connection

ExecutionPolicy = Literal["default", "fok", "post_only_chase"]


@dataclass(frozen=True, slots=True)
class OrderExecutionIntent:
    idempotency_key: str
    reduce_only: bool
    position_id: str | None
    execution_policy: ExecutionPolicy


def register_order_execution_intent(
    idempotency_key: str,
    *,
    reduce_only: bool,
    position_id: str | None = None,
    execution_policy: ExecutionPolicy = "default",
) -> None:
    with connection() as db:
        existing = db.execute(
            """
            SELECT reduce_only, position_id, execution_policy
            FROM order_execution_intents
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            matches = (
                bool(existing["reduce_only"]) == reduce_only
                and existing["position_id"] == position_id
                and existing["execution_policy"] == execution_policy
            )
            if not matches:
                raise HTTPException(
                    status_code=409,
                    detail="Order execution intent conflicts with an existing idempotency key",
                )
            return
        db.execute(
            """
            INSERT INTO order_execution_intents (
                idempotency_key, reduce_only, position_id, execution_policy
            ) VALUES (?, ?, ?, ?)
            """,
            (idempotency_key, int(reduce_only), position_id, execution_policy),
        )


def get_order_execution_intent(idempotency_key: str) -> OrderExecutionIntent:
    with connection() as db:
        row = db.execute(
            """
            SELECT idempotency_key, reduce_only, position_id, execution_policy
            FROM order_execution_intents
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
    if row is None:
        return OrderExecutionIntent(
            idempotency_key=idempotency_key,
            reduce_only=False,
            position_id=None,
            execution_policy="default",
        )
    return OrderExecutionIntent(
        idempotency_key=row["idempotency_key"],
        reduce_only=bool(row["reduce_only"]),
        position_id=row["position_id"],
        execution_policy=row["execution_policy"],
    )
