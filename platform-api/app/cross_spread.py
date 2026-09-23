from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from fastapi import HTTPException

from app import runtime_transport
from app.config import get_settings
from app.cross_spread_live_read_client import (
    CrossSpreadLiveReadError,
    LiveInstrumentSpecification,
    get_instrument_specification,
)
from app.database import connection
from app.market_data import (
    get_latest_cross_spread_market_snapshot,
    list_cross_spread_market_history,
    save_cross_spread_market_snapshot,
)
from app.order_execution_intents import register_order_execution_intent
from app.schemas import (
    CreateTradeCommandRequest,
    CrossSpreadHistoryPointResponse,
    CrossSpreadMarketCommandRequest,
    CrossSpreadPreflightRequest,
    CrossSpreadSnapshotResponse,
    CrossSpreadTradingRulesResponse,
    CrossSpreadVenueSnapshotResponse,
    CrossSpreadVenueTradingRuleResponse,
    ExecutionBatchResponse,
    TradeCommandResponse,
)
from app.strategies.domain import StrategyInstructionAction
from app.strategies.instruction_service import (
    CreateStrategyInstructionRequest,
    create_instruction,
    execute_instruction,
)
from app.trade_commands import create_trade_command

STRATEGY_INSTANCE_ID = "strategy_cross_venue_spread_instance_default"
STRATEGY_KEY = "cross_venue_spread"
BYBIT_INSTRUMENT_ID = "instrument_xau_usdt_perp"
MT5_INSTRUMENT_ID = "instrument_xau_usd"
BYBIT_SYMBOL = "XAUTUSDT"
MT5_SYMBOL = "XAUUSD.s"
BYBIT_LEG_ROLE = "bybit_leg"
MT5_LEG_ROLE = "mt5_leg"


@dataclass(frozen=True, slots=True)
class CrossSpreadLiveSizing:
    bybit_account_id: str
    mt5_account_id: str
    bybit_min: Decimal
    bybit_step: Decimal
    bybit_max: Decimal | None
    mt5_min: Decimal
    mt5_step: Decimal
    mt5_max: Decimal | None
    mt5_multiplier: Decimal


def get_cross_spread_snapshot() -> CrossSpreadSnapshotResponse:
    settings = get_settings()
    try:
        response = runtime_transport.get(
            f"{settings.runtime_base_url}/gateway/cross-spread/snapshot",
            params={"bybitAccountId": get_bybit_account_id(), "mt5AccountId": get_mt5_account_id()},
            timeout=max(settings.runtime_timeout_seconds, 20.0),
        )
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                "Platform Execution Runtime returned an error",
                request=response.request,
                response=response,
            )
    except httpx.HTTPError as exc:
        stale = get_latest_cross_spread_market_snapshot(strategy_key=STRATEGY_KEY)
        if stale is not None:
            return _mark_stale(stale)
        raise HTTPException(
            status_code=502,
            detail="Platform Execution Runtime is unavailable",
        ) from exc
    snapshot = CrossSpreadSnapshotResponse.model_validate(response.json())
    save_cross_spread_market_snapshot(
        snapshot,
        strategy_key=STRATEGY_KEY,
        strategy_instance_id=STRATEGY_INSTANCE_ID,
    )
    return snapshot


def _mark_stale(snapshot: CrossSpreadSnapshotResponse) -> CrossSpreadSnapshotResponse:
    """Mark a fallback snapshot as degraded so the UI never shows it as live."""
    return CrossSpreadSnapshotResponse(
        status="partial",
        bybit=CrossSpreadVenueSnapshotResponse(
            venue=snapshot.bybit.venue,
            symbol=snapshot.bybit.symbol,
            status="unavailable",
            quote=snapshot.bybit.quote,
            positions=snapshot.bybit.positions,
            reason=_join_stale_reason(snapshot.bybit.reason),
            openAllowed=False,
            closeAllowed=False,
            executionBlockReason="runtime_snapshot_stale",
        ),
        mt5=CrossSpreadVenueSnapshotResponse(
            venue=snapshot.mt5.venue,
            symbol=snapshot.mt5.symbol,
            status="unavailable",
            quote=snapshot.mt5.quote,
            positions=snapshot.mt5.positions,
            reason=_join_stale_reason(snapshot.mt5.reason),
            openAllowed=False,
            closeAllowed=False,
            executionBlockReason="runtime_snapshot_stale",
        ),
        longSpread=snapshot.long_spread,
        shortSpread=snapshot.short_spread,
        metrics=snapshot.metrics,
        executionState="unavailable",
        asOf=snapshot.as_of,
    )


def _join_stale_reason(reason: str | None) -> str | None:
    stale_hint = "stale fallback snapshot (runtime temporarily unavailable)"
    if reason:
        return f"{reason};{stale_hint}"
    return stale_hint


def get_cross_spread_history(limit: int = 200) -> list[CrossSpreadHistoryPointResponse]:
    return list_cross_spread_market_history(strategy_key=STRATEGY_KEY, limit=limit)


def get_cross_spread_trading_rules() -> CrossSpreadTradingRulesResponse:
    """Return native Venue specifications plus the current executable session state."""
    bybit_account_id = _bound_cross_spread_account_id(BYBIT_LEG_ROLE)
    mt5_account_id = _bound_cross_spread_account_id(MT5_LEG_ROLE)
    with ThreadPoolExecutor(max_workers=2) as executor:
        bybit_future = executor.submit(
            get_instrument_specification,
            account_id=bybit_account_id,
            symbol=BYBIT_SYMBOL,
        )
        mt5_future = executor.submit(
            get_instrument_specification,
            account_id=mt5_account_id,
            symbol=MT5_SYMBOL,
        )
        try:
            bybit_spec, mt5_spec = bybit_future.result(), mt5_future.result()
        except CrossSpreadLiveReadError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    snapshot = get_cross_spread_snapshot()

    def venue_rule(venue: str, spec, state) -> CrossSpreadVenueTradingRuleResponse:
        return CrossSpreadVenueTradingRuleResponse(
            venue=venue,
            source=spec.source,
            accountId=spec.account_id,
            symbol=spec.symbol,
            status=spec.status,
            priceTick=spec.price_tick,
            minQuantity=spec.min_quantity,
            quantityStep=spec.quantity_step,
            maxMarketQuantity=spec.max_market_quantity,
            contractSize=spec.contract_size,
            tradeMode=spec.trade_mode,
            fillingMode=spec.filling_mode,
            accessChecks=spec.access_checks,
            openAllowed=state.open_allowed,
            closeAllowed=state.close_allowed,
            executionBlockReason=state.execution_block_reason,
            marketStatus=state.market_status,
            tradingHours=state.trading_hours,
            tradingTimezone=state.trading_timezone,
            automaticExitAllowed=state.automatic_exit_allowed,
            automaticExitBlockReason=state.automatic_exit_block_reason,
            automaticExitGuardMinutes=state.automatic_exit_guard_minutes,
            quoteSourceAsOf=state.quote_source_as_of,
            asOf=spec.as_of,
        )

    return CrossSpreadTradingRulesResponse(
        bybit=venue_rule("bybit", bybit_spec, snapshot.bybit),
        mt5=venue_rule("mt5", mt5_spec, snapshot.mt5),
        executionState=snapshot.execution_state,
        asOf=datetime.now(UTC),
    )


def submit_cross_spread_market_command(
    request: CrossSpreadMarketCommandRequest,
    *,
    idempotency_key: str | None = None,
    bybit_reduce_only: bool = False,
    mt5_reduce_only: bool = False,
    mt5_position_id: str | None = None,
    allow_netting_close: bool = False,
) -> ExecutionBatchResponse:
    assert_cross_spread_live_execution_enabled()

    is_close = request.action.startswith("CLOSE_")
    strict_reduce_close = bybit_reduce_only and mt5_reduce_only and mt5_position_id is not None
    position_group_close = (
        allow_netting_close
        and not bybit_reduce_only
        and mt5_reduce_only
        and mt5_position_id is not None
    )
    if is_close and not (strict_reduce_close or position_group_close):
        raise HTTPException(
            status_code=422,
            detail="Cross-spread close intent is incomplete",
        )
    if not is_close and (bybit_reduce_only or mt5_reduce_only or mt5_position_id is not None):
        raise HTTPException(
            status_code=422,
            detail="Open cross-spread commands cannot carry close-position intent",
        )

    assert_cross_spread_market_executable(is_close=is_close)

    sizing = _load_live_cross_spread_sizing()
    _validate_leg_quantity(
        request.quantity_oz,
        minimum=sizing.bybit_min,
        step=sizing.bybit_step,
        maximum=sizing.bybit_max,
        label=BYBIT_SYMBOL,
    )
    mt5_lot = request.quantity_oz / sizing.mt5_multiplier
    _validate_leg_quantity(
        mt5_lot,
        minimum=sizing.mt5_min,
        step=sizing.mt5_step,
        maximum=sizing.mt5_max,
        label=MT5_SYMBOL,
    )
    if mt5_lot * sizing.mt5_multiplier != request.quantity_oz:
        raise HTTPException(
            status_code=422,
            detail="Requested ounces do not map exactly to the current MT5 contract size",
        )

    batch_key = idempotency_key or request.idempotency_key
    if batch_key is None:
        raise HTTPException(
            status_code=422,
            detail="Cross-spread execution requires a stable idempotencyKey",
        )
    instruction = create_instruction(
        STRATEGY_INSTANCE_ID,
        CreateStrategyInstructionRequest(
            idempotencyKey=batch_key,
            action=(
                StrategyInstructionAction.CLOSE if is_close else StrategyInstructionAction.OPEN
            ),
            parameters={
                "action": request.action,
                "quantityOz": request.quantity_oz,
                "bybitReduceOnly": bybit_reduce_only,
                "mt5ReduceOnly": mt5_reduce_only,
                "mt5PositionId": mt5_position_id,
            },
            reason="cross spread market command",
        ),
        requested_by="cross_spread_command",
    )
    return execute_instruction(str(instruction["instructionId"]))


def assert_cross_spread_live_execution_enabled() -> None:
    if not _cross_spread_live_execution_gate_allows_write(get_settings()):
        raise HTTPException(403, "Live cross-spread execution is disabled")


def assert_cross_spread_market_executable(*, is_close: bool) -> CrossSpreadSnapshotResponse:
    """Require both normal legs to be executable before creating an instruction.

    This gate intentionally does not sit in the single-leg reconciliation and
    recovery paths. Those paths own an already-unhedged exposure and retain
    their stricter ticket/idempotency checks.
    """
    snapshot = get_cross_spread_snapshot()
    capability = "close_allowed" if is_close else "open_allowed"
    blocked = [
        venue
        for venue in (snapshot.bybit, snapshot.mt5)
        if not getattr(venue, capability)
    ]
    if blocked:
        details = "; ".join(
            f"{venue.venue}: {venue.execution_block_reason or 'execution_not_allowed'}"
            for venue in blocked
        )
        action = "close" if is_close else "open"
        raise HTTPException(
            status_code=423,
            detail=(
                f"Cross-spread {action} is monitor-only because both venues are not "
                f"executable ({details})"
            ),
        )
    return snapshot


def assert_cross_spread_native_trading_rules() -> None:
    """Refresh and validate both authoritative Venue specifications."""
    _load_live_cross_spread_sizing()


def prepare_cross_spread_market_command(
    request: CrossSpreadPreflightRequest,
) -> dict[str, object]:
    """Prepare read-only admission facts before final user confirmation."""
    if request.exit_plan_id is not None:
        from app.cross_spread_close_recovery import prepare_unsubmitted_mt5_close
        from app.cross_spread_exit_repository import get_exit_plan
        from app.execution_batches import get_execution_batch

        plan = get_exit_plan(request.exit_plan_id)
        expected = "CLOSE_LONG" if plan.direction == "LONG_SPREAD" else "CLOSE_SHORT"
        if request.action != expected:
            raise HTTPException(409, "Close action does not match the selected position group")
        if plan.status == "manual_intervention" and plan.close_batch_id:
            batch = get_execution_batch(plan.close_batch_id)
            if any(leg.role == "bybit_leg" and leg.status == "filled" for leg in batch.legs):
                prepare_unsubmitted_mt5_close(plan, request.quantity_oz)
                return {"status": "ready", "preparedAt": datetime.now(UTC).isoformat()}
    assert_cross_spread_market_executable(is_close=request.action.startswith("CLOSE_"))
    sizing = _load_live_cross_spread_sizing()
    mt5_quantity = request.quantity_oz / sizing.mt5_multiplier
    _validate_leg_quantity(
        request.quantity_oz,
        minimum=sizing.bybit_min,
        step=sizing.bybit_step,
        maximum=sizing.bybit_max,
        label=BYBIT_SYMBOL,
    )
    _validate_leg_quantity(
        mt5_quantity,
        minimum=sizing.mt5_min,
        step=sizing.mt5_step,
        maximum=sizing.mt5_max,
        label=MT5_SYMBOL,
    )
    bybit_side, mt5_side = _sides_for_action(request.action)

    def prepare_leg(account_id: str, symbol: str, side: str, quantity: Decimal):
        from app.execution_batches import (
            _reservation_margin_estimate,
            _reservation_reference_price,
        )

        reference_price = _reservation_reference_price(
            account_id=account_id,
            symbol=symbol,
            side=side,
        )
        currency, margin = _reservation_margin_estimate(
            account_id=account_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            reference_price=reference_price,
        )
        return {
            "accountId": account_id,
            "symbol": symbol,
            "side": side,
            "quantity": format(quantity, "f"),
            "referencePrice": format(reference_price, "f"),
            "reservationCurrency": currency,
            "reservationAmount": format(margin, "f"),
        }

    with ThreadPoolExecutor(max_workers=2) as executor:
        bybit_future = executor.submit(
            prepare_leg,
            sizing.bybit_account_id,
            BYBIT_SYMBOL,
            bybit_side,
            request.quantity_oz,
        )
        mt5_future = executor.submit(
            prepare_leg,
            sizing.mt5_account_id,
            MT5_SYMBOL,
            mt5_side,
            mt5_quantity,
        )
        legs = [bybit_future.result(), mt5_future.result()]
    return {
        "status": "ready",
        "preparedAt": datetime.now(UTC).isoformat(),
        "legs": legs,
    }


def submit_bybit_definitive_failure_rollback(
    *,
    open_batch_id: str,
    open_action: str,
    quantity_oz: Decimal,
) -> TradeCommandResponse:
    settings = get_settings()
    if not settings.cross_spread_definitive_failure_rollback_enabled:
        raise HTTPException(
            status_code=423,
            detail="Cross-spread rollback capability is disabled",
        )
    bybit = _load_live_bybit_specification()
    _validate_leg_quantity(
        quantity_oz,
        minimum=bybit.min_quantity,
        step=bybit.quantity_step,
        maximum=bybit.max_market_quantity,
        label=BYBIT_SYMBOL,
    )
    idempotency_key = f"cross-spread-rollback:{open_batch_id}:bybit"
    register_order_execution_intent(idempotency_key, reduce_only=True)
    return create_trade_command(
        CreateTradeCommandRequest(
            idempotencyKey=idempotency_key,
            strategyInstanceId=STRATEGY_INSTANCE_ID,
            accountId=_bound_cross_spread_account_id(BYBIT_LEG_ROLE),
            instrumentId=BYBIT_INSTRUMENT_ID,
            symbol=BYBIT_SYMBOL,
            side="sell" if open_action == "OPEN_LONG" else "buy",
            orderType="market",
            quantity=quantity_oz,
            price=None,
        )
    )


def _cross_spread_live_execution_gate_allows_write(settings) -> bool:
    return bool(settings.live_trading_enabled)


def _sides_for_action(action: str) -> tuple[str, str]:
    if action in {"OPEN_LONG", "CLOSE_SHORT"}:
        return "buy", "sell"
    return "sell", "buy"


def _load_live_bybit_specification() -> LiveInstrumentSpecification:
    try:
        bybit = get_instrument_specification(
            account_id=_bound_cross_spread_account_id(BYBIT_LEG_ROLE),
            symbol=BYBIT_SYMBOL,
        )
    except CrossSpreadLiveReadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _validate_bybit_live_specification(bybit)
    return bybit


def _load_live_cross_spread_sizing() -> CrossSpreadLiveSizing:
    bybit_account_id = _bound_cross_spread_account_id(BYBIT_LEG_ROLE)
    mt5_account_id = _bound_cross_spread_account_id(MT5_LEG_ROLE)
    bybit = _load_live_bybit_specification()
    try:
        mt5 = get_instrument_specification(
            account_id=mt5_account_id,
            symbol=MT5_SYMBOL,
        )
    except CrossSpreadLiveReadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _validate_mt5_live_specification(mt5)
    return CrossSpreadLiveSizing(
        bybit_account_id=bybit_account_id,
        mt5_account_id=mt5_account_id,
        bybit_min=bybit.min_quantity,
        bybit_step=bybit.quantity_step,
        bybit_max=bybit.max_market_quantity,
        mt5_min=mt5.min_quantity,
        mt5_step=mt5.quantity_step,
        mt5_max=mt5.max_market_quantity,
        mt5_multiplier=mt5.contract_size,
    )


def _bound_cross_spread_account_id(role: str) -> str:
    settings = get_settings()
    preferred_environment = settings.cross_spread_preferred_account_environment.strip().lower()
    with connection() as db:
        row = db.execute(
            """
            SELECT sab.account_id
            FROM strategy_account_bindings sab
            LEFT JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ?
              AND sab.role = ?
              AND sab.status = 'active'
            ORDER BY
              CASE
                WHEN ? != '' AND lower(COALESCE(a.environment, '')) = ? THEN 0
                ELSE 1
              END,
              CASE
                WHEN lower(COALESCE(a.status, '')) = 'active' THEN 0
                ELSE 1
              END,
              sab.created_at DESC,
              sab.id DESC
            LIMIT 1
            """,
            (
                STRATEGY_INSTANCE_ID,
                "venue_a" if role == BYBIT_LEG_ROLE else "mt5_leg",
                preferred_environment,
                preferred_environment,
            ),
        ).fetchone()
    if row is None:
        venue_name = "Bybit" if role == BYBIT_LEG_ROLE else "MT5"
        raise HTTPException(
            status_code=503,
            detail=f"{venue_name} account binding is unavailable for cross-spread",
        )
    return str(row["account_id"])


def get_bybit_account_id() -> str:
    return _bound_cross_spread_account_id(BYBIT_LEG_ROLE)


def get_mt5_account_id() -> str:
    return _bound_cross_spread_account_id(MT5_LEG_ROLE)


def _validate_bybit_live_specification(
    specification: LiveInstrumentSpecification,
) -> None:
    checks = specification.access_checks
    if specification.status.lower() not in {"trading", "available"}:
        raise HTTPException(
            status_code=423,
            detail="Bybit instrument is not currently trading",
        )
    if specification.trade_mode == "simulation":
        # Simulation venues (deterministic FakeGateway) carry no real API-key
        # credential state; local closed-loop execution must not require a
        # bound production key. Real venues report a non-simulation mode and
        # keep the full access-check gate.
        return
    if checks.get("readOnly") is True:
        raise HTTPException(status_code=423, detail="Bybit API key is read-only")
    if checks.get("ipBound") is not True:
        raise HTTPException(
            status_code=423,
            detail="Bybit API key must be bound to a fixed IP",
        )
    if checks.get("orderPermission") is not True:
        raise HTTPException(
            status_code=423,
            detail="Bybit API key lacks Order permission",
        )
    if checks.get("positionPermission") is not True:
        raise HTTPException(
            status_code=423,
            detail="Bybit API key lacks Position permission",
        )


def _validate_mt5_live_specification(
    specification: LiveInstrumentSpecification,
) -> None:
    checks = specification.access_checks
    if specification.status not in {"available", "selected"}:
        raise HTTPException(
            status_code=423,
            detail="MT5 symbol is not available for trading",
        )
    if specification.trade_mode == "simulation":
        return
    if checks.get("accountLoginMatched") is not True:
        raise HTTPException(
            status_code=423,
            detail="MT5 connected login does not match configuration",
        )
    if checks.get("accountTradeAllowed") is not True:
        raise HTTPException(
            status_code=423,
            detail="MT5 经纪商账户不允许交易，请检查账户交易权限",
        )
    if checks.get("terminalTradeAllowed") is not True:
        raise HTTPException(
            status_code=423,
            detail="MT5 算法交易开关已关闭，请在对应 MT5 终端开启“算法交易”",
        )
    if checks.get("accountExpertTradeAllowed") is not True:
        raise HTTPException(status_code=423, detail="MT5 经纪商账户不允许自动交易，请检查账户权限")
    if checks.get("pythonTradeAllowed") is not True:
        raise HTTPException(
            status_code=423,
            detail=(
                "MT5 禁止 Python 交易，请在工具 → 选项 → 智能交易系统中"
                "取消“禁用外部 Python API 自动交易”"
            ),
        )


def _validate_leg_quantity(
    quantity: Decimal,
    *,
    minimum: Decimal,
    step: Decimal,
    maximum: Decimal | None,
    label: str,
) -> None:
    if minimum <= 0 or step <= 0:
        raise HTTPException(
            status_code=422,
            detail=f"{label} contract specification is invalid",
        )
    if quantity < minimum:
        raise HTTPException(
            status_code=422,
            detail=f"{label} quantity is below contract minimum",
        )
    if maximum is not None and maximum > 0 and quantity > maximum:
        raise HTTPException(
            status_code=422,
            detail=f"{label} quantity exceeds market maximum",
        )
    steps = (quantity - minimum) / step
    if steps != steps.to_integral_value():
        raise HTTPException(
            status_code=422,
            detail=f"{label} quantity does not match current contract step",
        )
