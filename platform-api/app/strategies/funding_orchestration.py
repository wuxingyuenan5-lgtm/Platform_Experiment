from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app import execution_risk_repository as risk_repository
from app.config import get_settings
from app.database import connection
from app.execution_batches import (
    _claim_batch_execution_resources,
    _find_blocking_batch_for_accounts,
    get_execution_batch,
    update_batch_status,
    update_leg_status,
)
from app.execution_risk import (
    assert_execution_allowed,
    complete_batch_risk,
    initialize_batch_risk,
    record_filled_leg,
)
from app.execution_schemas import ExecutionBatchResponse
from app.order_execution_intents import register_order_execution_intent
from app.schemas import CreateTradeCommandRequest
from app.strategies.domain import (
    ExecutionPlan,
    ExecutionPlanLeg,
    StrategyInstructionStatus,
)
from app.trade_commands import create_trade_command
from app.trading import get_order_row, synchronize_order_with_authoritative_facts

PERPETUAL_ROLE = "perpetual_leg"
SPOT_ROLE = "spot_leg"
ACTIVE_ATTEMPT_STATUSES = {
    "declared",
    "acknowledged",
    "accepted",
    "partially_filled",
    "cancel_pending",
}
TERMINAL_ATTEMPT_STATUSES = {"filled", "canceled", "rejected", "result_unknown"}
PHASE_2_CAPABILITY_MESSAGE = (
    "Funding controlled-live execution requires Phase 2 post-only "
    "chase and authoritative incremental release"
)
FUNDING_RUNTIME_REQUIRED_CAPABILITIES = frozenset(
    {
        "post_only_single_attempt_submit",
        "order_query",
        "fill_query",
        "position_query",
        "account_risk_query",
        "cancel_order_gated",
    }
)


@dataclass(frozen=True, slots=True)
class FundingReleaseRow:
    child_id: str
    cumulative_perpetual_fill: Decimal
    release_quantity: Decimal
    cumulative_spot_quantity: Decimal
    status: str
    trade_command_id: str | None
    order_id: str | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class FundingAttemptRow:
    attempt_id: str
    attempt_number: int
    idempotency_key: str
    limit_price: Decimal
    requested_quantity: Decimal
    trade_command_id: str | None
    order_id: str | None
    status: str
    cancel_requested_at: str | None
    cancel_terminal_at: str | None
    failure_reason: str | None
    created_at: str


def execute_funding_instruction(
    instruction_id: str,
    *,
    instruction_row,
    plan: ExecutionPlan,
) -> ExecutionBatchResponse:
    strategy_instance_id = str(instruction_row["strategy_instance_id"])
    trading_mode = _strategy_trading_mode(strategy_instance_id)
    if trading_mode != "simulation":
        readiness = get_funding_controlled_live_readiness(
            strategy_instance_id=strategy_instance_id,
            account_id=_leg(plan, PERPETUAL_ROLE).account_id,
        )
        if not readiness["ready"]:
            raise HTTPException(status_code=423, detail=PHASE_2_CAPABILITY_MESSAGE)

    perpetual_leg = _leg(plan, PERPETUAL_ROLE)
    spot_leg = _leg(plan, SPOT_ROLE)
    batch_id = str(instruction_row["execution_batch_id"])
    batch_status = _batch_status(batch_id)
    instruction_status = str(instruction_row["status"])

    if batch_status in {"failed", "manual_intervention", "completed"}:
        return get_execution_batch(batch_id)
    if (
        batch_status == "hedged"
        or instruction_status == StrategyInstructionStatus.RECONCILING.value
    ):
        return _complete_reconciliation(instruction_id, batch_id, perpetual_leg, spot_leg)

    _claim_funding_batch(
        instruction_id=instruction_id,
        batch_id=batch_id,
        strategy_instance_id=strategy_instance_id,
        account_ids=[perpetual_leg.account_id, spot_leg.account_id],
        legs=[perpetual_leg, spot_leg],
    )
    _set_instruction_status(instruction_id, StrategyInstructionStatus.EXECUTING)
    try:
        active_attempt = _active_attempt(batch_id)
        latest_attempt = _latest_attempt(batch_id)
        if (
            active_attempt is None
            and latest_attempt is not None
            and latest_attempt.status == "result_unknown"
        ):
            return _manual_intervention(
                instruction_id,
                batch_id,
                "Funding perpetual PostOnly result is unknown",
            )
        created_attempt = False
        if active_attempt is None:
            next_number = (_latest_attempt_number(batch_id) or 0) + 1
            if _ttl_expired(batch_id, perpetual_leg):
                return _bounded_stop(
                    instruction_id,
                    batch_id,
                    "Funding perpetual chase TTL expired before the next attempt",
                )
            if next_number > perpetual_leg.max_mutations + 1:
                return _bounded_stop(
                    instruction_id,
                    batch_id,
                    "Funding perpetual chase maxMutations exhausted",
                )
            created_attempt = _create_attempt(
                batch_id=batch_id,
                strategy_instance_id=strategy_instance_id,
                request_idempotency_key=str(instruction_row["idempotency_key"]),
                leg=perpetual_leg,
                attempt_number=next_number,
            )
            active_attempt = _active_attempt(batch_id)
            if active_attempt is None:
                latest_attempt = _latest_attempt(batch_id)
                if latest_attempt is not None and latest_attempt.status == "result_unknown":
                    return _manual_intervention(
                        instruction_id,
                        batch_id,
                        "Funding perpetual PostOnly result is unknown",
                    )
                if (
                        latest_attempt is not None
                        and latest_attempt.status in TERMINAL_ATTEMPT_STATUSES
                    ):
                        active_attempt = latest_attempt

        assert active_attempt is not None
        synced = _synchronize_attempt_from_authority(active_attempt)
        total_cumulative_fill = _latest_perpetual_cumulative_fill(batch_id)
        _record_incremental_risk(batch_id, total_cumulative_fill)

        if synced.status == "result_unknown":
            return _manual_intervention(
                instruction_id,
                batch_id,
                "Funding perpetual PostOnly result is unknown",
            )

        if synced.order_id is not None:
            _update_batch_leg_order(
                batch_id=batch_id,
                role=PERPETUAL_ROLE,
                order_id=synced.order_id,
                status=synced.status,
                price=synced.limit_price,
            )

        if (
            synced.status in {"declared", "acknowledged", "accepted", "partially_filled"}
            and synced.attempt_number >= perpetual_leg.max_mutations + 1
            and _quote_move_requires_new_attempt(synced, perpetual_leg)
        ):
            return _bounded_stop(
                instruction_id,
                batch_id,
                "Funding perpetual chase maxMutations exhausted",
            )

        if _has_release_side_effect_failure(batch_id):
            first = next(
                row for row in _release_rows(batch_id) if row.status in {"failed", "result_unknown"}
            )
            return _manual_intervention(
                instruction_id,
                batch_id,
                first.failure_reason or "Funding Spot release requires manual intervention",
            )

        release = _claim_spot_release(
            batch_id=batch_id,
            perpetual_leg=perpetual_leg,
            spot_leg=spot_leg,
            cumulative_perpetual_fill=total_cumulative_fill,
        )
        if release is not None and release.status == "claimed":
            _submit_spot_release(
                instruction_id=instruction_id,
                batch_id=batch_id,
                strategy_instance_id=strategy_instance_id,
                request_idempotency_key=str(instruction_row["idempotency_key"]),
                spot_leg=spot_leg,
                child_id=release.child_id,
                quantity=release.release_quantity,
            )

        if synced.status == "filled":
            return _refresh_batch_after_release(instruction_id, batch_id, perpetual_leg, spot_leg)

        if synced.status in {"canceled", "rejected"}:
            if _ttl_expired(batch_id, perpetual_leg):
                return _bounded_stop(
                    instruction_id,
                    batch_id,
                    "Funding perpetual chase TTL expired after terminal cancel",
                )
            next_number = synced.attempt_number + 1
            if next_number > perpetual_leg.max_mutations + 1:
                return _bounded_stop(
                    instruction_id,
                    batch_id,
                    "Funding perpetual chase maxMutations exhausted",
                )
            created_attempt = _create_attempt(
                batch_id=batch_id,
                strategy_instance_id=strategy_instance_id,
                request_idempotency_key=str(instruction_row["idempotency_key"]),
                leg=perpetual_leg,
                attempt_number=next_number,
            )
            update_batch_status(batch_id, "executing")
            return get_execution_batch(batch_id)

        if created_attempt:
            update_batch_status(batch_id, "executing")
            return _refresh_batch_after_release(instruction_id, batch_id, perpetual_leg, spot_leg)

        if _check_due(synced, perpetual_leg):
            if synced.cancel_requested_at is None:
                _request_cancel(synced)
                _mark_attempt_cancel_pending(synced.attempt_id)
            return get_execution_batch(batch_id)

        update_batch_status(batch_id, "executing")
        return _refresh_batch_after_release(instruction_id, batch_id, perpetual_leg, spot_leg)
    except HTTPException as exc:
        return _failed_without_side_effects(instruction_id, batch_id, str(exc.detail))


def _claim_funding_batch(
    *,
    instruction_id: str,
    batch_id: str,
    strategy_instance_id: str,
    account_ids: list[str],
    legs: list[ExecutionPlanLeg],
) -> None:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            """
            SELECT strategy_instruction_id, strategy_instance_id, status
            FROM execution_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=409, detail="Funding execution batch is unavailable")
        if str(row["strategy_instruction_id"]) != instruction_id:
            raise HTTPException(
                status_code=409,
                detail="Funding instruction batch relation is invalid",
            )
        if str(row["strategy_instance_id"]) != strategy_instance_id:
            raise HTTPException(
                status_code=409,
                detail="Funding execution batch strategy is invalid",
            )
        blocking = _find_blocking_batch_for_accounts(db, account_ids)
        if blocking is not None and str(blocking["id"]) != batch_id:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Active execution batch blocks new strategy instruction: "
                    f"{blocking['id']} ({blocking['status']})"
                ),
            )
        existing_claim = db.execute(
            """
            SELECT 1
            FROM execution_resource_claims
            WHERE owner_type = 'batch' AND owner_id = ? AND status = 'active'
            LIMIT 1
            """,
            (batch_id,),
        ).fetchone()
        if existing_claim is None:
            _claim_batch_execution_resources(
                db,
                batch_id=batch_id,
                strategy_instance_id=strategy_instance_id,
                legs=[
                    SimpleNamespace(
                        account_id=leg.account_id,
                        instrument_id=leg.instrument_id,
                        symbol=leg.external_symbol,
                        side=leg.side,
                        price=None,
                        quantity=leg.maximum_quantity,
                    )
                    for leg in legs
                ],
                default_account_id=legs[0].account_id,
            )
        if str(row["status"]) == "pending":
            claimed = db.execute(
                """
                UPDATE execution_batches
                SET status = 'executing', updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (_utc_now(), batch_id),
            )
            if claimed.rowcount != 1:
                raise HTTPException(status_code=409, detail="Funding batch claim lost")
    assert_execution_allowed(strategy_instance_id, list(dict.fromkeys(account_ids)))
    initialize_batch_risk(batch_id, strategy_instance_id)


def _refresh_batch_after_release(
    instruction_id: str,
    batch_id: str,
    perpetual_leg: ExecutionPlanLeg,
    spot_leg: ExecutionPlanLeg,
) -> ExecutionBatchResponse:
    cumulative_fill = _latest_perpetual_cumulative_fill(batch_id)
    cumulative_spot = _declared_cumulative_spot(batch_id)
    if _has_release_side_effect_failure(batch_id):
        return _manual_intervention(
            instruction_id,
            batch_id,
            "Funding Spot release requires manual intervention",
        )
    if (
        cumulative_fill == perpetual_leg.maximum_quantity
        and cumulative_spot == (spot_leg.release_cap or Decimal("0"))
    ):
        update_batch_status(batch_id, "hedged")
        complete_batch_risk(batch_id)
        _set_instruction_status(instruction_id, StrategyInstructionStatus.RECONCILING)
        return get_execution_batch(batch_id)
    if cumulative_fill <= 0 and cumulative_spot <= 0:
        update_batch_status(batch_id, "executing")
        update_leg_status(batch_id, SPOT_ROLE, "pending")
        return get_execution_batch(batch_id)
    update_batch_status(batch_id, "partially_executed")
    update_leg_status(batch_id, SPOT_ROLE, "filled" if cumulative_spot > 0 else "pending")
    return get_execution_batch(batch_id)


def _create_attempt(
    *,
    batch_id: str,
    strategy_instance_id: str,
    request_idempotency_key: str,
    leg: ExecutionPlanLeg,
    attempt_number: int,
) -> bool:
    requested_quantity = _remaining_perpetual_quantity(batch_id, leg)
    if requested_quantity <= 0:
        return False
    if requested_quantity < leg.minimum_quantity:
        return False
    quote = _authoritative_quote(account_id=leg.account_id, symbol=leg.external_symbol)
    limit_price = _aligned_limit_price(leg, bid=quote["bid"], ask=quote["ask"])
    latest_attempt = _latest_attempt(batch_id)
    if (
        latest_attempt is not None
        and latest_attempt.status in {"canceled", "rejected"}
        and limit_price == latest_attempt.limit_price
    ):
        return False
    attempt_id = str(uuid4())
    idempotency_key = _attempt_idempotency_key(
        request_idempotency_key=request_idempotency_key,
        attempt_number=attempt_number,
    )
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO funding_perpetual_attempts (
                id, batch_id, attempt_number, idempotency_key, limit_price, requested_quantity,
                trade_command_id, order_id, status, cancel_requested_at,
                cancel_terminal_at, failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 'declared', NULL, NULL, NULL, ?, ?)
            """,
            (
                attempt_id,
                batch_id,
                attempt_number,
                idempotency_key,
                _decimal_text(limit_price),
                _decimal_text(requested_quantity),
                _utc_now(),
                _utc_now(),
            ),
        )
        row = db.execute(
            """
            SELECT id, trade_command_id, order_id, status
            FROM funding_perpetual_attempts
            WHERE batch_id = ? AND attempt_number = ?
            """,
            (batch_id, attempt_number),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="Funding perpetual attempt claim is unavailable",
        )
    if row["order_id"] is not None or row["status"] != "declared":
        return False
    _assert_attempt_within_maximum(
        batch_id=batch_id,
        requested_quantity=requested_quantity,
        maximum_quantity=leg.maximum_quantity,
    )
    register_order_execution_intent(
        idempotency_key,
        reduce_only=False,
        execution_policy="post_only_single_attempt",
    )
    try:
        command = create_trade_command(
            CreateTradeCommandRequest(
                idempotencyKey=idempotency_key,
                strategyInstanceId=strategy_instance_id,
                accountId=leg.account_id,
                instrumentId=leg.instrument_id,
                symbol=leg.external_symbol,
                side=leg.side,
                orderType="limit",
                quantity=requested_quantity,
                price=limit_price,
            )
        )
        with connection() as db:
            db.execute(
                """
                UPDATE funding_perpetual_attempts
                SET trade_command_id = ?, order_id = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    command.trade_command_id,
                    command.platform_order_id,
                    command.status,
                    _utc_now(),
                    str(row["id"]),
                ),
            )
        _update_batch_leg_order(
            batch_id=batch_id,
            role=PERPETUAL_ROLE,
            order_id=command.platform_order_id,
            status=command.status,
            price=limit_price,
        )
        return True
    except HTTPException as exc:
        unknown_order_id = _result_unknown_order_for_idempotency_key(idempotency_key)
        if unknown_order_id is None:
            raise
        with connection() as db:
            db.execute(
                """
                UPDATE funding_perpetual_attempts
                SET order_id = ?, status = 'result_unknown', failure_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (unknown_order_id, str(exc.detail), _utc_now(), str(row["id"])),
            )
        _update_batch_leg_order(
            batch_id=batch_id,
            role=PERPETUAL_ROLE,
            order_id=unknown_order_id,
            status="result_unknown",
            price=limit_price,
        )
        return True


def _synchronize_attempt_from_authority(attempt: FundingAttemptRow) -> FundingAttemptRow:
    if attempt.order_id is None:
        return attempt
    external_order = _runtime_get(
        f"/venue/orders/by-platform/{attempt.order_id}",
        allow_not_found=True,
    )
    if external_order is None:
        return attempt
    external_fills = _runtime_get("/venue/fills", params={"platformOrderId": attempt.order_id})
    if not isinstance(external_order, dict) or not isinstance(external_fills, list):
        raise HTTPException(
            status_code=502,
            detail="Funding runtime authority response is malformed",
        )
    synchronize_order_with_authoritative_facts(
        str(attempt.order_id),
        external_order=dict(external_order),
        external_fills=[dict(item) for item in external_fills if isinstance(item, dict)],
    )
    local = get_order_row(str(attempt.order_id))
    normalized = _attempt_status_from_order_status(str(local["status"]))
    cancel_terminal_at = (
        _utc_now()
        if normalized in {"canceled", "rejected"}
        else attempt.cancel_terminal_at
    )
    with connection() as db:
        db.execute(
            """
            UPDATE funding_perpetual_attempts
            SET status = ?, cancel_terminal_at = COALESCE(?, cancel_terminal_at), updated_at = ?
            WHERE id = ?
            """,
            (normalized, cancel_terminal_at, _utc_now(), attempt.attempt_id),
        )
        row = db.execute(
            """
            SELECT *
            FROM funding_perpetual_attempts
            WHERE id = ?
            """,
            (attempt.attempt_id,),
        ).fetchone()
    assert row is not None
    return _attempt_from_row(row)


def _request_cancel(attempt: FundingAttemptRow) -> None:
    if attempt.order_id is None:
        return
    external_order = _runtime_get(f"/venue/orders/by-platform/{attempt.order_id}")
    if not isinstance(external_order, dict):
        raise HTTPException(status_code=502, detail="Funding cancel authority is malformed")
    external_order_id = external_order.get("externalOrderId")
    if not external_order_id:
        raise HTTPException(
            status_code=409,
            detail="Funding external order identity is unavailable",
        )
    _runtime_post(
        f"/venue/orders/{external_order_id}/cancel",
        {
            "idempotencyKey": f"{attempt.idempotency_key}:cancel",
            "reason": "funding post-only chase",
        },
    )


def _mark_attempt_cancel_pending(attempt_id: str) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE funding_perpetual_attempts
            SET status = 'cancel_pending',
                cancel_requested_at = COALESCE(cancel_requested_at, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (_utc_now(), _utc_now(), attempt_id),
        )


@dataclass(frozen=True, slots=True)
class ReleaseClaim:
    status: str
    child_id: str
    release_quantity: Decimal


def _claim_spot_release(
    *,
    batch_id: str,
    perpetual_leg: ExecutionPlanLeg,
    spot_leg: ExecutionPlanLeg,
    cumulative_perpetual_fill: Decimal,
) -> ReleaseClaim | None:
    if cumulative_perpetual_fill > perpetual_leg.maximum_quantity:
        raise HTTPException(
            status_code=502,
            detail="Perpetual cumulative fill exceeds maximumQuantity",
        )
    allowed_cumulative_spot = _allowed_cumulative_spot(
        perpetual_cumulative_fill=cumulative_perpetual_fill,
        spot_leg=spot_leg,
    )
    child_id = f"{batch_id}:spot:{_decimal_key(allowed_cumulative_spot)}"
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        authoritative_fill = _sum_decimal_rows(
            db.execute(
                """
                SELECT quantity FROM fills
                WHERE order_id IN (
                    SELECT order_id FROM funding_perpetual_attempts WHERE batch_id = ?
                )
                """,
                (batch_id,),
            ).fetchall(),
            key="quantity",
        )
        if authoritative_fill > perpetual_leg.maximum_quantity:
            raise HTTPException(
                status_code=502,
                detail="Perpetual cumulative fill exceeds maximumQuantity",
            )
        existing = db.execute(
            """
            SELECT child_id, release_quantity
            FROM funding_spot_release_commands
            WHERE child_id = ?
            """,
            (child_id,),
        ).fetchone()
        if existing is not None:
            return ReleaseClaim(
                status="existing",
                child_id=str(existing["child_id"]),
                release_quantity=Decimal(str(existing["release_quantity"])),
            )
        already_declared = _sum_decimal_rows(
            db.execute(
                """
                SELECT release_quantity FROM funding_spot_release_commands
                WHERE batch_id = ?
                """,
                (batch_id,),
            ).fetchall(),
            key="release_quantity",
        )
        delta = allowed_cumulative_spot - already_declared
        if delta <= 0:
            return None
        if spot_leg.release_cap is not None and already_declared + delta > spot_leg.release_cap:
            raise HTTPException(status_code=502, detail="Funding Spot release exceeds releaseCap")
        db.execute(
            """
            INSERT OR IGNORE INTO funding_spot_release_commands (
                child_id, batch_id, cumulative_perpetual_fill, release_quantity,
                cumulative_spot_quantity, trade_command_id, order_id, status,
                failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, NULL, NULL, 'declared', NULL, ?, ?)
            """,
            (
                child_id,
                batch_id,
                _decimal_text(authoritative_fill),
                _decimal_text(delta),
                _decimal_text(allowed_cumulative_spot),
                _utc_now(),
                _utc_now(),
            ),
        )
        claimed = db.execute(
            """
            SELECT child_id, release_quantity, trade_command_id
            FROM funding_spot_release_commands
            WHERE child_id = ?
            """,
            (child_id,),
        ).fetchone()
    if claimed is None:
        return None
    return ReleaseClaim(
        status="claimed" if claimed["trade_command_id"] is None else "existing",
        child_id=str(claimed["child_id"]),
        release_quantity=Decimal(str(claimed["release_quantity"])),
    )


def _submit_spot_release(
    *,
    instruction_id: str,
    batch_id: str,
    strategy_instance_id: str,
    request_idempotency_key: str,
    spot_leg: ExecutionPlanLeg,
    child_id: str,
    quantity: Decimal,
) -> None:
    idempotency_key = _spot_child_idempotency_key(
        request_idempotency_key=request_idempotency_key,
        child_id=child_id,
    )
    with connection() as db:
        existing = db.execute(
            """
            SELECT trade_command_id, order_id, status
            FROM funding_spot_release_commands
            WHERE child_id = ?
            """,
            (child_id,),
        ).fetchone()
        if existing is not None and existing["trade_command_id"] is not None:
            return
    register_order_execution_intent(idempotency_key, reduce_only=False)
    try:
        command = create_trade_command(
            CreateTradeCommandRequest(
                idempotencyKey=idempotency_key,
                strategyInstanceId=strategy_instance_id,
                accountId=spot_leg.account_id,
                instrumentId=spot_leg.instrument_id,
                symbol=spot_leg.external_symbol,
                side=spot_leg.side,
                orderType="market",
                quantity=quantity,
            )
        )
    except HTTPException as exc:
        unknown_order_id = _result_unknown_order_for_idempotency_key(idempotency_key)
        if unknown_order_id is not None:
            _mark_release_status(
                child_id,
                "result_unknown",
                order_id=unknown_order_id,
                failure_reason=str(exc.detail),
            )
            update_leg_status(batch_id, SPOT_ROLE, "result_unknown", order_id=unknown_order_id)
            return
        _mark_release_status(child_id, "failed", failure_reason=str(exc.detail))
        if not _has_any_external_side_effect(batch_id):
            raise
        return

    release_status = "filled" if command.status == "filled" else command.status
    if release_status not in {"filled", "result_unknown"}:
        release_status = "failed"
    _mark_release_status(
        child_id,
        release_status,
        trade_command_id=command.trade_command_id,
        order_id=command.platform_order_id,
        failure_reason=(
            None
            if release_status == "filled"
            else f"Funding Spot release stopped with status {command.status}"
        ),
    )
    update_leg_status(batch_id, SPOT_ROLE, command.status, order_id=command.platform_order_id)
    if release_status == "result_unknown":
        _manual_intervention(
            instruction_id,
            batch_id,
            "Funding Spot release result is unknown",
        )


def _manual_intervention(instruction_id: str, batch_id: str, reason: str):
    update_batch_status(
        batch_id,
        "manual_intervention",
        failure_reason=reason,
        requires_manual_intervention=True,
    )
    _set_instruction_status(
        instruction_id,
        StrategyInstructionStatus.MANUAL_INTERVENTION,
        failure_reason=reason,
    )
    return get_execution_batch(batch_id)


def _failed_without_side_effects(instruction_id: str, batch_id: str, reason: str):
    if _has_any_external_side_effect(batch_id):
        return _manual_intervention(instruction_id, batch_id, reason)
    update_batch_status(batch_id, "failed", failure_reason=reason)
    _set_instruction_status(
        instruction_id,
        StrategyInstructionStatus.FAILED,
        failure_reason=reason,
    )
    return get_execution_batch(batch_id)


def _bounded_stop(instruction_id: str, batch_id: str, reason: str) -> ExecutionBatchResponse:
    if _has_any_external_side_effect(batch_id):
        return _manual_intervention(instruction_id, batch_id, reason)
    return _failed_without_side_effects(instruction_id, batch_id, reason)


def _record_incremental_risk(batch_id: str, cumulative_fill: Decimal) -> None:
    if cumulative_fill <= 0:
        return
    record_filled_leg(batch_id)


def _strategy_trading_mode(strategy_instance_id: str) -> str:
    with connection() as db:
        row = db.execute(
            "SELECT trading_mode FROM strategy_instances WHERE id = ?",
            (strategy_instance_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy instance is not runnable")
    return str(row["trading_mode"])


def get_funding_controlled_live_readiness(
    *,
    strategy_instance_id: str,
    account_id: str,
) -> dict[str, Any]:
    settings = get_settings()
    checks: dict[str, Any] = {
        "liveTradingEnabled": settings.live_trading_enabled,
        "sharedClaims": True,
        "balanceReservations": True,
    }
    checks["killSwitchClear"] = (
        risk_repository.first_enabled_kill_switch(strategy_instance_id, [account_id]) is None
    )
    adapter: dict[str, Any] | None = None
    try:
        with httpx.Client(
            trust_env=False,
            timeout=settings.runtime_timeout_seconds,
        ) as client:
            response = client.get(f"{settings.runtime_base_url}/gateway/capabilities")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        payload = None
    if isinstance(payload, dict):
        checks["runtimeLiveWriteEnabled"] = bool(payload.get("liveWriteEnabled"))
        adapters = payload.get("adapters")
        if isinstance(adapters, list):
            for item in adapters:
                if not isinstance(item, dict):
                    continue
                account_ids = item.get("accountIds")
                if isinstance(account_ids, list) and account_id in account_ids:
                    adapter = item
                    break
    if adapter is None:
        checks.update(
            {
                "adapterConfigured": False,
                "adapterOperational": False,
                "runtimeCapabilities": [],
                "hasRequiredRuntimeCapabilities": False,
                "ready": False,
            }
        )
        return checks
    runtime_capabilities = {
        str(item)
        for item in adapter.get("capabilities", [])
        if isinstance(item, str)
    }
    checks["adapterConfigured"] = bool(adapter.get("configured"))
    checks["adapterOperational"] = bool(adapter.get("operational"))
    checks["adapterWriteEnabled"] = bool(adapter.get("writeEnabled"))
    checks["runtimeCapabilities"] = sorted(runtime_capabilities)
    checks["hasRequiredRuntimeCapabilities"] = FUNDING_RUNTIME_REQUIRED_CAPABILITIES.issubset(
        runtime_capabilities
    )
    checks["ready"] = bool(
        checks["liveTradingEnabled"]
        and checks["killSwitchClear"]
        and checks.get("runtimeLiveWriteEnabled")
        and checks["adapterConfigured"]
        and checks["adapterOperational"]
        and checks["adapterWriteEnabled"]
        and checks["hasRequiredRuntimeCapabilities"]
        and checks["sharedClaims"]
        and checks["balanceReservations"]
    )
    return checks


def _leg(plan: ExecutionPlan, role: str) -> ExecutionPlanLeg:
    for leg in plan.legs:
        if leg.role == role:
            return leg
    raise HTTPException(status_code=423, detail=f"Funding plan leg {role} is unavailable")


def _active_attempt(batch_id: str) -> FundingAttemptRow | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT *
            FROM funding_perpetual_attempts
            WHERE batch_id = ?
              AND status IN (
                  'declared',
                  'acknowledged',
                  'accepted',
                  'partially_filled',
                  'cancel_pending'
              )
            ORDER BY attempt_number DESC
            LIMIT 1
            """,
            (batch_id,),
        ).fetchone()
    return None if row is None else _attempt_from_row(row)


def _latest_attempt_number(batch_id: str) -> int | None:
    with connection() as db:
        row = db.execute(
            (
                "SELECT MAX(attempt_number) AS attempt_number "
                "FROM funding_perpetual_attempts WHERE batch_id = ?"
            ),
            (batch_id,),
        ).fetchone()
    if row is None or row["attempt_number"] is None:
        return None
    return int(row["attempt_number"])


def _latest_attempt(batch_id: str) -> FundingAttemptRow | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT *
            FROM funding_perpetual_attempts
            WHERE batch_id = ?
            ORDER BY attempt_number DESC
            LIMIT 1
            """,
            (batch_id,),
        ).fetchone()
    return None if row is None else _attempt_from_row(row)


def _attempt_from_row(row) -> FundingAttemptRow:
    return FundingAttemptRow(
        attempt_id=str(row["id"]),
        attempt_number=int(row["attempt_number"]),
        idempotency_key=str(row["idempotency_key"]),
        limit_price=Decimal(str(row["limit_price"])),
        requested_quantity=Decimal(str(row["requested_quantity"] or "0")),
        trade_command_id=row["trade_command_id"],
        order_id=row["order_id"],
        status=str(row["status"]),
        cancel_requested_at=row["cancel_requested_at"],
        cancel_terminal_at=row["cancel_terminal_at"],
        failure_reason=row["failure_reason"],
        created_at=str(row["created_at"]),
    )


def _attempt_status_from_order_status(status: str) -> str:
    return {
        "acknowledged": "acknowledged",
        "accepted": "accepted",
        "partially_filled": "partially_filled",
        "filled": "filled",
        "canceled": "canceled",
        "rejected": "rejected",
        "result_unknown": "result_unknown",
    }.get(status, "result_unknown")


def _remaining_perpetual_quantity(batch_id: str, leg: ExecutionPlanLeg) -> Decimal:
    remaining = leg.maximum_quantity - _latest_perpetual_cumulative_fill(batch_id)
    if remaining <= 0:
        return Decimal("0")
    with localcontext() as context:
        context.prec = 28
        steps = (remaining / leg.quantity_step).to_integral_value(rounding=ROUND_FLOOR)
        quantized = steps * leg.quantity_step
    return max(quantized, Decimal("0"))


def _assert_attempt_within_maximum(
    *,
    batch_id: str,
    requested_quantity: Decimal,
    maximum_quantity: Decimal,
) -> None:
    cumulative_fill = _latest_perpetual_cumulative_fill(batch_id)
    if cumulative_fill + requested_quantity > maximum_quantity:
        raise HTTPException(
            status_code=502,
            detail="Funding perpetual attempt would exceed maximumQuantity",
        )


def _batch_status(batch_id: str) -> str:
    with connection() as db:
        row = db.execute(
            "SELECT status FROM execution_batches WHERE id = ?",
            (batch_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Funding execution batch is unavailable")
    return str(row["status"])


def _complete_reconciliation(
    instruction_id: str,
    batch_id: str,
    perpetual_leg: ExecutionPlanLeg,
    spot_leg: ExecutionPlanLeg,
) -> ExecutionBatchResponse:
    cumulative_fill = _latest_perpetual_cumulative_fill(batch_id)
    cumulative_spot = _declared_cumulative_spot(batch_id)
    expected_spot = spot_leg.release_cap or Decimal("0")
    if _has_release_side_effect_failure(batch_id):
        return _manual_intervention(
            instruction_id,
            batch_id,
            "Funding Spot release requires manual intervention",
        )
    if cumulative_fill != perpetual_leg.maximum_quantity or cumulative_spot != expected_spot:
        return _manual_intervention(
            instruction_id,
            batch_id,
            "Funding reconciliation is incomplete",
        )
    reconciliation_status = _authoritative_reconciliation_status(
        batch_id,
        perpetual_leg,
        spot_leg,
    )
    if reconciliation_status == "unavailable":
        return get_execution_batch(batch_id)
    if reconciliation_status == "mismatch":
        return _manual_intervention(
            instruction_id,
            batch_id,
            "Funding authoritative position evidence mismatches plan",
        )
    update_batch_status(batch_id, "completed")
    complete_batch_risk(batch_id)
    _set_instruction_status(instruction_id, StrategyInstructionStatus.COMPLETED)
    return get_execution_batch(batch_id)


def _authoritative_reconciliation_status(
    batch_id: str,
    perpetual_leg: ExecutionPlanLeg,
    spot_leg: ExecutionPlanLeg,
) -> str:
    attempts = _attempts(batch_id)
    if not attempts or any(attempt.order_id is None for attempt in attempts):
        return "unavailable"
    try:
        for attempt in attempts:
            order_id = attempt.order_id
            assert order_id is not None
            order = _runtime_get(f"/venue/orders/by-platform/{order_id}")
            fills = _runtime_get("/venue/fills", params={"platformOrderId": order_id})
            if not isinstance(order, dict) or not isinstance(fills, list):
                return "unavailable"
        release_orders = [
            row.order_id for row in _release_rows(batch_id) if row.order_id is not None
        ]
        for order_id in release_orders:
            order = _runtime_get(f"/venue/orders/by-platform/{order_id}")
            fills = _runtime_get("/venue/fills", params={"platformOrderId": order_id})
            if not isinstance(order, dict) or not isinstance(fills, list):
                return "unavailable"
        positions = _runtime_get(
            "/venue/positions",
            params={"accountId": perpetual_leg.account_id},
        )
        if not isinstance(positions, list):
            return "unavailable"
        account_risk = _runtime_get(
            "/venue/account-risk",
            params={"accountId": perpetual_leg.account_id},
        )
        if not isinstance(account_risk, dict) or account_risk.get("dataQualityState") != "complete":
            return "unavailable"
    except HTTPException:
        return "unavailable"

    expected_positions = {
        perpetual_leg.instrument_id: _signed_fill_quantity(
            account_id=perpetual_leg.account_id,
            instrument_id=perpetual_leg.instrument_id,
            side=perpetual_leg.side,
            order_ids=[attempt.order_id for attempt in attempts if attempt.order_id is not None],
        ),
        spot_leg.instrument_id: _signed_fill_quantity(
            account_id=spot_leg.account_id,
            instrument_id=spot_leg.instrument_id,
            side=spot_leg.side,
            order_ids=release_orders,
        ),
    }
    actual_positions = {
        str(position.get("instrumentId")): Decimal(str(position.get("netQuantity", "0")))
        for position in positions
        if isinstance(position, dict)
    }
    for instrument_id, expected_quantity in expected_positions.items():
        if actual_positions.get(instrument_id, Decimal("0")) != expected_quantity:
            return "mismatch"
    return "ready"


def _signed_fill_quantity(
    *,
    account_id: str,
    instrument_id: str,
    side: str,
    order_ids: list[str],
) -> Decimal:
    if not order_ids:
        return Decimal("0")
    placeholders = ", ".join("?" for _ in order_ids)
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT quantity
            FROM fills
            WHERE account_id = ? AND instrument_id = ? AND order_id IN ({placeholders})
            """,
            (account_id, instrument_id, *order_ids),
        ).fetchall()
    quantity = _sum_decimal_rows(rows, key="quantity")
    return quantity if side == "buy" else -quantity


def _attempts(batch_id: str) -> list[FundingAttemptRow]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT *
            FROM funding_perpetual_attempts
            WHERE batch_id = ?
            ORDER BY attempt_number
            """,
            (batch_id,),
        ).fetchall()
    return [_attempt_from_row(row) for row in rows]


def _order_cumulative_fill(order_id: str) -> Decimal:
    with connection() as db:
        rows = db.execute("SELECT quantity FROM fills WHERE order_id = ?", (order_id,)).fetchall()
    return _sum_decimal_rows(rows, key="quantity")


def _latest_perpetual_cumulative_fill(batch_id: str) -> Decimal:
    with connection() as db:
        rows = db.execute(
            """
            SELECT quantity
            FROM fills
            WHERE order_id IN (
                SELECT order_id FROM funding_perpetual_attempts WHERE batch_id = ?
            )
            """,
            (batch_id,),
        ).fetchall()
    return _sum_decimal_rows(rows, key="quantity")


def _allowed_cumulative_spot(
    *,
    perpetual_cumulative_fill: Decimal,
    spot_leg: ExecutionPlanLeg,
) -> Decimal:
    assert spot_leg.release_ratio is not None
    assert spot_leg.release_cap is not None
    with localcontext() as context:
        context.prec = 28
        proportional = perpetual_cumulative_fill * spot_leg.release_ratio
        steps = (proportional / spot_leg.quantity_step).to_integral_value(rounding=ROUND_FLOOR)
        releasable = steps * spot_leg.quantity_step
    return min(releasable, spot_leg.release_cap)


def _release_rows(batch_id: str) -> list[FundingReleaseRow]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT child_id, cumulative_perpetual_fill, release_quantity, cumulative_spot_quantity,
                   status, trade_command_id, order_id, failure_reason
            FROM funding_spot_release_commands
            WHERE batch_id = ?
            ORDER BY created_at, child_id
            """,
            (batch_id,),
        ).fetchall()
    return [
        FundingReleaseRow(
            child_id=str(row["child_id"]),
            cumulative_perpetual_fill=Decimal(str(row["cumulative_perpetual_fill"])),
            release_quantity=Decimal(str(row["release_quantity"])),
            cumulative_spot_quantity=Decimal(str(row["cumulative_spot_quantity"])),
            status=str(row["status"]),
            trade_command_id=row["trade_command_id"],
            order_id=row["order_id"],
            failure_reason=row["failure_reason"],
        )
        for row in rows
    ]


def _declared_cumulative_spot(batch_id: str) -> Decimal:
    releases = _release_rows(batch_id)
    if not releases:
        return Decimal("0")
    return max((row.cumulative_spot_quantity for row in releases), default=Decimal("0"))


def _mark_release_status(
    child_id: str,
    status: str,
    *,
    trade_command_id: str | None = None,
    order_id: str | None = None,
    failure_reason: str | None = None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE funding_spot_release_commands
            SET trade_command_id = COALESCE(?, trade_command_id),
                order_id = COALESCE(?, order_id),
                status = ?, failure_reason = ?, updated_at = ?
            WHERE child_id = ?
            """,
            (trade_command_id, order_id, status, failure_reason, _utc_now(), child_id),
        )


def _update_batch_leg_order(
    *,
    batch_id: str,
    role: str,
    order_id: str | None,
    status: str,
    price: Decimal | None = None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_legs
            SET order_id = COALESCE(?, order_id),
                status = ?,
                price = COALESCE(?, price),
                updated_at = ?
            WHERE batch_id = ? AND role = ?
            """,
            (
                order_id,
                status,
                _decimal_text(price) if price is not None else None,
                _utc_now(),
                batch_id,
                role,
            ),
        )


def _set_instruction_status(
    instruction_id: str,
    status: StrategyInstructionStatus,
    failure_reason: str | None = None,
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


def _authoritative_quote(*, account_id: str, symbol: str) -> dict[str, Decimal]:
    payload = _runtime_get(f"/venue/quotes/{symbol}", params={"accountId": account_id})
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="Funding runtime quote is malformed")
    try:
        return {
            "bid": Decimal(str(payload["bid"])),
            "ask": Decimal(str(payload["ask"])),
        }
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Funding runtime quote is incomplete") from exc


def _aligned_limit_price(leg: ExecutionPlanLeg, *, bid: Decimal, ask: Decimal) -> Decimal:
    reference = bid if leg.side == "buy" else ask
    rounding = ROUND_FLOOR if leg.side == "buy" else ROUND_CEILING
    with localcontext() as context:
        context.prec = 28
        ticks = (reference / leg.price_tick).to_integral_value(rounding=rounding)
        price = ticks * leg.price_tick
    if price <= 0:
        raise HTTPException(status_code=423, detail="Funding simulation reference price is invalid")
    return price


def _check_due(attempt: FundingAttemptRow, leg: ExecutionPlanLeg) -> bool:
    created = datetime.fromisoformat(attempt.created_at)
    return datetime.now(UTC) >= created + timedelta(seconds=leg.check_interval_seconds)


def _ttl_expired(batch_id: str, leg: ExecutionPlanLeg) -> bool:
    with connection() as db:
        row = db.execute(
            """
            SELECT MAX(created_at) AS created_at
            FROM funding_perpetual_attempts
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchone()
    if row is None or row["created_at"] is None:
        return False
    started = datetime.fromisoformat(str(row["created_at"]))
    return datetime.now(UTC) >= started + timedelta(seconds=leg.ttl_seconds)


def _quote_move_requires_new_attempt(attempt: FundingAttemptRow, leg: ExecutionPlanLeg) -> bool:
    quote = _authoritative_quote(account_id=leg.account_id, symbol=leg.external_symbol)
    return _aligned_limit_price(leg, bid=quote["bid"], ask=quote["ask"]) != attempt.limit_price


def _has_release_side_effect_failure(batch_id: str) -> bool:
    return any(row.status in {"failed", "result_unknown"} for row in _release_rows(batch_id))


def _has_any_external_side_effect(batch_id: str) -> bool:
    with connection() as db:
        attempt = db.execute(
            (
                "SELECT 1 FROM funding_perpetual_attempts "
                "WHERE batch_id = ? AND order_id IS NOT NULL LIMIT 1"
            ),
            (batch_id,),
        ).fetchone()
        release = db.execute(
            """
            SELECT 1 FROM funding_spot_release_commands
            WHERE batch_id = ? AND (order_id IS NOT NULL OR trade_command_id IS NOT NULL)
            LIMIT 1
            """,
            (batch_id,),
        ).fetchone()
    return attempt is not None or release is not None


def _sum_decimal_rows(rows, *, key: str) -> Decimal:
    return sum((Decimal(str(row[key])) for row in rows), Decimal("0"))


def _attempt_idempotency_key(*, request_idempotency_key: str, attempt_number: int) -> str:
    digest = hashlib.sha256(
        f"{request_idempotency_key}|attempt|{attempt_number}".encode()
    ).hexdigest()
    prefix = request_idempotency_key[:48]
    return f"funding-perp:{prefix}:{attempt_number}:{digest[:16]}"


def _spot_child_idempotency_key(*, request_idempotency_key: str, child_id: str) -> str:
    digest = hashlib.sha256(f"{request_idempotency_key}|{child_id}".encode()).hexdigest()
    prefix = request_idempotency_key[:48]
    return f"funding-spot:{prefix}:{digest[:32]}"


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _decimal_key(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _result_unknown_order_for_idempotency_key(idempotency_key: str) -> str | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT o.id
            FROM trade_commands command
            JOIN orders o ON o.command_id = command.id
            WHERE command.idempotency_key = ? AND o.status = 'result_unknown'
            """,
            (idempotency_key,),
        ).fetchone()
    return str(row["id"]) if row is not None else None


def _runtime_get(
    path: str,
    params: dict[str, str] | None = None,
    *,
    allow_not_found: bool = False,
) -> object | None:
    settings = get_settings()
    try:
        with httpx.Client(trust_env=False, timeout=settings.runtime_timeout_seconds) as client:
            response = client.get(f"{settings.runtime_base_url}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        if allow_not_found and exc.response.status_code == 404:
            return None
        raise HTTPException(status_code=502, detail=_runtime_error_detail(exc.response)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Funding runtime query is unavailable: {path}",
        ) from exc


def _runtime_post(path: str, payload: dict[str, object]) -> object:
    settings = get_settings()
    try:
        with httpx.Client(trust_env=False, timeout=settings.runtime_timeout_seconds) as client:
            response = client.post(f"{settings.runtime_base_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=_runtime_error_detail(exc.response)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Funding runtime write is unavailable: {path}",
        ) from exc


def _runtime_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])
    text = response.text.strip()
    return text or f"HTTP {response.status_code}"
