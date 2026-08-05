from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app import execution_risk_repository as repository
from app.config import get_settings
from app.execution_exposure import calculate_residual_exposure
from app.execution_risk_models import (
    DEFAULT_FAILURE_ACTION,
    DEFAULT_MAX_LEG_DELAY_SECONDS,
    DEFAULT_MAX_RESIDUAL_NOTIONAL,
    BatchRiskResponse,
    ExecutionRiskPolicyResponse,
    ExecutionRiskPolicyUpdateRequest,
    KillSwitchResponse,
    KillSwitchScope,
    KillSwitchUpdateRequest,
    RiskActionRequest,
    RiskActionResponse,
    RiskStatus,
    TradeCommandResult,
)
from app.execution_risk_policy import (
    evaluate_batch_completion,
    evaluate_leg_deadline,
    evaluate_residual_exposure,
    opposite_side,
    select_failure_disposition,
)
from app.schemas import CreateTradeCommandRequest

TradeCommandPort = Callable[[CreateTradeCommandRequest], TradeCommandResult]
_trade_command_port: TradeCommandPort | None = None


def configure_trade_command_port(port: TradeCommandPort) -> None:
    global _trade_command_port
    _trade_command_port = port


def _create_trade_command(request: CreateTradeCommandRequest) -> TradeCommandResult:
    if _trade_command_port is None:
        raise RuntimeError("Execution-risk trade-command port is not configured")
    return _trade_command_port(request)


def ensure_schema() -> None:
    repository.ensure_schema()


def _repository_error(exc: repository.ExecutionRiskRepositoryError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


def validate_scope(scope_type: str, scope_id: str) -> KillSwitchScope:
    if scope_type not in {"global", "strategy", "account"}:
        raise HTTPException(status_code=422, detail="Unsupported kill-switch scope")
    if scope_type == "global" and scope_id != "*":
        raise HTTPException(
            status_code=422,
            detail="Global kill switch must use scopeId '*' ",
        )
    if scope_type == "strategy" and not repository.strategy_exists(scope_id):
        raise HTTPException(status_code=404, detail="Strategy instance not found")
    if scope_type == "account" and not repository.account_exists(scope_id):
        raise HTTPException(status_code=404, detail="Account not found")
    return scope_type


def get_kill_switch(scope_type: str, scope_id: str) -> KillSwitchResponse:
    validated_scope = validate_scope(scope_type, scope_id)
    result = repository.get_kill_switch(validated_scope, scope_id)
    if result is not None:
        return result
    return KillSwitchResponse(
        scopeType=validated_scope,
        scopeId=scope_id,
        enabled=False,
        reason=None,
        actor="system-default",
        version=0,
        updatedAt=datetime.now(UTC),
    )


def set_kill_switch(
    scope_type: str,
    scope_id: str,
    request: KillSwitchUpdateRequest,
) -> KillSwitchResponse:
    validated_scope = validate_scope(scope_type, scope_id)
    try:
        return repository.set_kill_switch(validated_scope, scope_id, request)
    except repository.ExecutionRiskRepositoryError as exc:
        raise _repository_error(exc) from exc


def assert_execution_allowed(strategy_instance_id: str, account_ids: list[str]) -> None:
    blocked = repository.first_enabled_kill_switch(strategy_instance_id, account_ids)
    if blocked is None:
        return
    scope_type, scope_id, reason = blocked
    raise HTTPException(
        status_code=423,
        detail=f"Execution blocked by {scope_type} kill switch {scope_id}: {reason}",
    )


def get_execution_risk_policy(
    strategy_instance_id: str,
) -> ExecutionRiskPolicyResponse:
    if not repository.strategy_exists(strategy_instance_id):
        raise HTTPException(status_code=404, detail="Strategy instance not found")
    configured = repository.get_configured_policy(strategy_instance_id)
    if configured is not None:
        return configured
    return ExecutionRiskPolicyResponse(
        strategyInstanceId=strategy_instance_id,
        maxLegDelaySeconds=DEFAULT_MAX_LEG_DELAY_SECONDS,
        maxResidualNotional=DEFAULT_MAX_RESIDUAL_NOTIONAL,
        failureAction=DEFAULT_FAILURE_ACTION,
        source="default",
        actor="system-default",
        updatedAt=datetime.now(UTC),
    )


def set_execution_risk_policy(
    strategy_instance_id: str,
    request: ExecutionRiskPolicyUpdateRequest,
) -> ExecutionRiskPolicyResponse:
    get_execution_risk_policy(strategy_instance_id)
    try:
        return repository.set_execution_risk_policy(strategy_instance_id, request)
    except repository.ExecutionRiskRepositoryError as exc:
        raise _repository_error(exc) from exc


def initialize_batch_risk(batch_id: str, strategy_instance_id: str) -> BatchRiskResponse:
    policy = get_execution_risk_policy(strategy_instance_id)
    repository.initialize_batch_risk(batch_id, strategy_instance_id, policy)
    return get_batch_risk(batch_id)


def get_batch_risk(batch_id: str) -> BatchRiskResponse:
    risk = repository.get_batch_risk(batch_id)
    if risk is not None:
        return risk
    strategy_instance_id = repository.get_batch_strategy_instance_id(batch_id)
    if strategy_instance_id is None:
        raise HTTPException(status_code=404, detail="Execution batch not found")
    return initialize_batch_risk(batch_id, strategy_instance_id)


def check_leg_deadline(
    batch_id: str, at: datetime | None = None
) -> tuple[bool, str | None]:
    risk = get_batch_risk(batch_id)
    result = evaluate_leg_deadline(
        risk.first_fill_at,
        at or datetime.now(UTC),
        risk.max_leg_delay_seconds,
    )
    if result.exceeded:
        set_batch_risk_state(batch_id, result.status, reason=result.reason)
    return not result.exceeded, result.reason


def record_filled_leg(batch_id: str) -> tuple[bool, str | None]:
    risk = get_batch_risk(batch_id)
    residual, currency, quality = calculate_residual_exposure(batch_id)
    result = evaluate_residual_exposure(
        residual,
        currency,
        quality,
        risk.max_residual_notional,
    )
    repository.record_filled_leg(
        batch_id,
        result.status,
        residual,
        currency,
        quality,
        result.reason,
    )
    return not result.exceeded, result.reason


def complete_batch_risk(batch_id: str) -> BatchRiskResponse:
    residual, currency, quality = calculate_residual_exposure(batch_id)
    result = evaluate_batch_completion(residual, quality)
    repository.complete_batch_risk(
        batch_id,
        result.status,
        residual,
        currency,
        quality,
        result.reason,
    )
    return get_batch_risk(batch_id)


def handle_batch_failure(batch_id: str, reason: str) -> RiskActionResponse | None:
    risk = get_batch_risk(batch_id)
    residual, currency, quality = calculate_residual_exposure(batch_id)
    disposition = select_failure_disposition(
        residual,
        quality,
        risk.failure_action,
    )
    if disposition == "resolved":
        set_batch_risk_state(
            batch_id,
            "resolved",
            residual=residual,
            currency=currency,
            quality=quality,
            reason=reason,
        )
        return None
    set_batch_risk_state(
        batch_id,
        "residual_exposure",
        residual=residual,
        currency=currency,
        quality=quality,
        reason=reason,
    )
    if disposition == "auto_flatten":
        return execute_risk_action(
            batch_id,
            RiskActionRequest(
                idempotencyKey=f"auto-flatten:{batch_id}",
                action="flatten_filled_legs",
                actor="system-risk-engine",
                reason=reason,
            ),
        )
    set_batch_risk_state(batch_id, "escalated", reason=reason)
    return None


def set_batch_risk_state(
    batch_id: str,
    status: RiskStatus,
    *,
    residual: Decimal | None = None,
    currency: str | None = None,
    quality: str | None = None,
    reason: str | None = None,
) -> None:
    get_batch_risk(batch_id)
    repository.set_batch_risk_state(
        batch_id,
        status,
        residual=residual,
        currency=currency,
        quality=quality,
        reason=reason,
    )


def execute_risk_action(
    batch_id: str,
    request: RiskActionRequest,
) -> RiskActionResponse:
    risk = get_batch_risk(batch_id)
    try:
        action, created = repository.claim_risk_action(batch_id, request)
    except repository.ExecutionRiskRepositoryError as exc:
        raise _repository_error(exc) from exc
    if not created:
        return action
    set_batch_risk_state(
        batch_id,
        "disposition_in_progress",
        reason=request.reason,
    )
    try:
        status, order_ids, failure_reason = perform_risk_action(
            batch_id,
            request,
            risk,
        )
    except Exception as exc:
        status = "failed"
        order_ids = []
        failure_reason = str(exc)
        set_batch_risk_state(batch_id, "escalated", reason=failure_reason)
    return repository.finish_risk_action(
        action.risk_action_id,
        batch_id,
        request,
        status,
        order_ids,
        failure_reason,
    )


def perform_risk_action(
    batch_id: str,
    request: RiskActionRequest,
    risk: BatchRiskResponse,
) -> tuple[str, list[str], str | None]:
    if request.action == "hold_and_escalate":
        reason = request.reason or "Risk held for manual intervention"
        repository.mark_batch_manual_intervention(batch_id, reason)
        set_batch_risk_state(batch_id, "escalated", reason=request.reason)
        return "completed", [], None

    if request.action == "cancel_open_legs":
        unresolved = repository.cancel_pending_legs(
            batch_id,
            request.reason or "Canceled by risk action",
        )
        if unresolved:
            reason = "Open external orders require Venue cancellation support"
            set_batch_risk_state(batch_id, "escalated", reason=reason)
            return "action_required", [], reason
        set_batch_risk_state(
            batch_id,
            "resolved",
            residual=Decimal("0"),
            reason=request.reason,
        )
        return "completed", [], None

    if request.action == "substitute_hedge":
        command = _create_trade_command(
            CreateTradeCommandRequest(
                idempotencyKey=f"{request.idempotency_key}:replacement",
                strategyInstanceId=risk.strategy_instance_id,
                accountId=request.replacement_account_id,
                instrumentId=request.replacement_instrument_id,
                symbol=request.replacement_symbol,
                side=request.replacement_side,
                orderType="limit" if request.replacement_price is not None else "market",
                quantity=request.replacement_quantity,
                price=request.replacement_price,
            )
        )
        order_ids = [command.platform_order_id] if command.platform_order_id else []
        if command.status != "filled":
            reason = f"Replacement hedge completed with status {command.status}"
            set_batch_risk_state(batch_id, "escalated", reason=reason)
            return "action_required", order_ids, reason
        repository.mark_batch_hedged(batch_id)
        set_batch_risk_state(
            batch_id,
            "resolved",
            residual=Decimal("0"),
            currency="UNKNOWN",
            quality="complete",
            reason="Replacement hedge filled",
        )
        return "completed", order_ids, None

    legs = repository.filled_legs(batch_id)
    if not legs:
        set_batch_risk_state(
            batch_id,
            "resolved",
            residual=Decimal("0"),
            currency="UNKNOWN",
            quality="complete",
            reason="No filled legs required flattening",
        )
        return "completed", [], None

    order_ids: list[str] = []
    failures: list[str] = []
    for leg in legs:
        quantity = repository.filled_quantity(
            leg["order_id"],
            Decimal(leg["quantity"]),
        )
        command = _create_trade_command(
            CreateTradeCommandRequest(
                idempotencyKey=f"{request.idempotency_key}:{leg['role']}",
                strategyInstanceId=risk.strategy_instance_id,
                accountId=leg["account_id"],
                instrumentId=leg["instrument_id"],
                symbol=leg["symbol"],
                side=opposite_side(leg["side"]),
                orderType="market",
                quantity=quantity,
                price=None,
            )
        )
        if command.platform_order_id:
            order_ids.append(command.platform_order_id)
        if command.status != "filled":
            failures.append(f"{leg['role']} flatten status {command.status}")

    if failures:
        failure_reason = "; ".join(failures)
        set_batch_risk_state(batch_id, "escalated", reason=failure_reason)
        repository.mark_batch_manual_intervention(batch_id, failure_reason)
        return "action_required", order_ids, failure_reason

    repository.mark_batch_failed_flattened(batch_id)
    set_batch_risk_state(
        batch_id,
        "resolved",
        residual=Decimal("0"),
        currency="UNKNOWN",
        quality="complete",
        reason="All filled legs flattened",
    )
    return "completed", order_ids, None


def list_risk_actions(batch_id: str) -> list[RiskActionResponse]:
    get_batch_risk(batch_id)
    return repository.list_risk_actions(batch_id)


router = APIRouter(prefix=get_settings().api_prefix)


@router.get(
    "/risk/kill-switches/{scope_type}/{scope_id}",
    response_model=KillSwitchResponse,
    tags=["execution-risk"],
)
def read_kill_switch(scope_type: str, scope_id: str) -> KillSwitchResponse:
    return get_kill_switch(scope_type, scope_id)


@router.put(
    "/risk/kill-switches/{scope_type}/{scope_id}",
    response_model=KillSwitchResponse,
    tags=["execution-risk"],
)
def change_kill_switch(
    scope_type: str,
    scope_id: str,
    request: KillSwitchUpdateRequest,
) -> KillSwitchResponse:
    return set_kill_switch(scope_type, scope_id, request)


@router.get(
    "/strategies/instances/{strategy_instance_id}/execution-risk-policy",
    response_model=ExecutionRiskPolicyResponse,
    tags=["execution-risk"],
)
def read_execution_risk_policy(
    strategy_instance_id: str,
) -> ExecutionRiskPolicyResponse:
    return get_execution_risk_policy(strategy_instance_id)


@router.put(
    "/strategies/instances/{strategy_instance_id}/execution-risk-policy",
    response_model=ExecutionRiskPolicyResponse,
    tags=["execution-risk"],
)
def change_execution_risk_policy(
    strategy_instance_id: str,
    request: ExecutionRiskPolicyUpdateRequest,
) -> ExecutionRiskPolicyResponse:
    return set_execution_risk_policy(strategy_instance_id, request)


@router.get(
    "/trading/execution-batches/{batch_id}/risk",
    response_model=BatchRiskResponse,
    tags=["execution-risk"],
)
def read_batch_risk(batch_id: str) -> BatchRiskResponse:
    return get_batch_risk(batch_id)


@router.get(
    "/trading/execution-batches/{batch_id}/risk-actions",
    response_model=list[RiskActionResponse],
    tags=["execution-risk"],
)
def read_risk_actions(batch_id: str) -> list[RiskActionResponse]:
    return list_risk_actions(batch_id)


@router.post(
    "/trading/execution-batches/{batch_id}/risk-actions",
    response_model=RiskActionResponse,
    tags=["execution-risk"],
)
def create_risk_action(
    batch_id: str,
    request: RiskActionRequest,
) -> RiskActionResponse:
    return execute_risk_action(batch_id, request)
