"""Executable closing-spread exits reuse the persisted Funding close workflow."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from fastapi import HTTPException

from app import monitor_health
from app.config import get_settings
from app.strategies import funding_exit_repository as repository
from app.strategies.funding_schemas import FundingExitPlanRequest, FundingExitPlanResponse
from app.strategies.funding_workspace import (
    STRATEGY_INSTANCE_ID,
    get_funding_execution_context,
    list_funding_position_groups,
    submit_funding_instruction,
)
from app.strategies.instruction_service import get_instruction, get_instruction_by_idempotency

LOGGER = logging.getLogger(__name__)
QUOTE_MAX_AGE_SECONDS = 10


def _open_account(open_id: str) -> str:
    instruction = get_instruction(open_id)
    if instruction["strategyInstanceId"] != STRATEGY_INSTANCE_ID or instruction["action"] != "open":
        raise HTTPException(409, "自动平仓只能关联原 Funding 开仓指令")
    execution_plan = cast(dict[str, Any], instruction["executionPlan"])
    accounts = {leg["accountId"] for leg in execution_plan["legs"]}
    if len(accounts) != 1:
        raise HTTPException(409, "Funding 开仓账户证据不一致")
    return str(next(iter(accounts)))


def _eligible(group: dict[str, Any]) -> bool:
    return (
        not group.get("isAbnormal", True)
        and group.get("lifecycleState") == "active"
        and Decimal(str(group.get("remainingClosableQuantity", "0"))) > 0
        and Decimal(str(group.get("pendingCloseQuantity", "0"))) == 0
        and Decimal(str(group.get("resultUnknownReservedQuantity", "0"))) == 0
    )


def configure_exit(
    open_id: str, request: FundingExitPlanRequest, *, actor: str
) -> FundingExitPlanResponse:
    account_id = _open_account(open_id)
    if request.enabled:
        group = next(
            (g for g in list_funding_position_groups() if g["openInstructionId"] == open_id), None
        )
        if group is None or not _eligible(group):
            raise HTTPException(409, "仅正常、无待平预约的 Funding 剩余持仓可启用自动平仓")
    try:
        return repository.save_plan(open_id, account_id, request, actor=actor)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


def closing_spread(context: dict[str, Any], account_id: str, *, now: datetime) -> Decimal:
    if context.get("accountId") != account_id or context.get("dataQualityState") != "complete":
        raise ValueError("自动平仓账户或行情不可用")
    values = {}
    for leg, category in (("spot", "spot"), ("perpetual", "linear")):
        quote = context[f"{leg}Quote"]
        if (
            quote.get("accountId") != account_id
            or quote.get("category") != category
            or quote.get("symbol") != context[f"{leg}Symbol"]
            or quote.get("dataQualityState") != "complete"
        ):
            raise ValueError("自动平仓双腿行情身份不一致")
        source_time = datetime.fromisoformat(
            str(quote.get("sourceAsOf", "")).replace("Z", "+00:00")
        )
        if (
            source_time.tzinfo is None
            or not -2 <= (now - source_time).total_seconds() <= QUOTE_MAX_AGE_SECONDS
        ):
            raise ValueError("自动平仓报价已过期或来源时间无效")
        bid, ask = Decimal(str(quote["bid"])), Decimal(str(quote["ask"]))
        if not bid.is_finite() or not ask.is_finite() or not 0 < bid <= ask:
            raise ValueError("自动平仓买卖盘口无效")
        values[leg] = (bid, ask)
    return values["spot"][0] - values["perpetual"][1]


def _trigger_reason(plan: dict[str, Any], spread: Decimal) -> str | None:
    if plan["take_profit_spread"] is not None and spread >= Decimal(plan["take_profit_spread"]):
        return "take_profit"
    if plan["stop_loss_spread"] is not None and spread <= Decimal(plan["stop_loss_spread"]):
        return "stop_loss"
    return None


def _verify_symbols(context: dict[str, Any], source: dict[str, Any]) -> None:
    if any(context.get(key) != source[key] for key in ("spotSymbol", "perpetualSymbol")):
        raise ValueError("自动平仓报价与原持仓标的不一致")


def _submit_original_trigger(plan: dict[str, Any]) -> None:
    # Restart or a lost response must find the original instruction first.
    try:
        existing = get_instruction_by_idempotency(STRATEGY_INSTANCE_ID, plan["close_key"])
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        existing = None
    if existing is not None:
        repository.attach_close(plan["open_instruction_id"], str(existing["instructionId"]))
        return  # The existing Funding runner owns further execution/reconciliation.
    trigger = json.loads(plan["trigger_json"])
    group = next(
        (
            g
            for g in list_funding_position_groups()
            if g["openInstructionId"] == plan["open_instruction_id"]
        ),
        None,
    )
    if (
        group is None
        or not _eligible(group)
        or Decimal(str(group["remainingClosableQuantity"])) != Decimal(trigger["quantity"])
        or _open_account(plan["open_instruction_id"]) != plan["account_id"]
    ):
        raise ValueError("自动平仓原持仓已变化，须核对原触发记录")
    context = get_funding_execution_context(
        perpetual_symbol=trigger["perpetualSymbol"],
        spot_symbol=trigger["spotSymbol"],
        notional=None,
    )
    if context["accountId"] != plan["account_id"] or not context["controlledLiveReadiness"].get(
        "ready"
    ):
        raise ValueError("自动平仓账户或交易权限未就绪")
    _verify_symbols(context, trigger)
    spread = closing_spread(context, plan["account_id"], now=datetime.now(UTC))
    if _trigger_reason(plan, spread) is None:
        raise ValueError("最新可成交价差未达到阈值，等待原触发恢复")
    result = submit_funding_instruction(
        action="close",
        idempotency_key=plan["close_key"],
        perpetual_symbol=trigger["perpetualSymbol"],
        spot_symbol=trigger["spotSymbol"],
        quantity=Decimal(trigger["quantity"]),
        requested_by=plan["configured_by"],
        target_open_instruction_id=plan["open_instruction_id"],
        execution_policy="market",
    )
    repository.attach_close(
        plan["open_instruction_id"], str(result["instruction"]["instructionId"])
    )


def evaluate_exit_plans() -> bool:
    """Return whether all configured evaluations completed without an error."""
    if not get_settings().live_trading_enabled:
        return True
    plans = repository.list_plans(pending_only=True)
    if not plans:
        return True
    groups = {g["openInstructionId"]: g for g in list_funding_position_groups()}
    healthy = True
    for plan in plans:
        open_id = plan["open_instruction_id"]
        try:
            if plan["close_key"]:
                _submit_original_trigger(plan)
                continue
            group = groups.get(open_id)
            if group is None or not _eligible(group):
                continue
            if _open_account(open_id) != plan["account_id"]:
                raise ValueError("原开仓账户已变化，停止自动平仓")
            context = get_funding_execution_context(
                perpetual_symbol=group["perpetualSymbol"],
                spot_symbol=group["spotSymbol"],
                notional=None,
            )
            if not context["controlledLiveReadiness"].get("ready"):
                raise ValueError("自动平仓交易权限未就绪")
            now = datetime.now(UTC)
            _verify_symbols(context, group)
            spread = closing_spread(context, plan["account_id"], now=now)
            reason = _trigger_reason(plan, spread)
            repository.set_error(open_id, None)
            if reason is None:
                continue
            claimed = repository.claim_trigger(
                plan,
                {
                    "reason": reason,
                    "spread": str(spread),
                    "triggeredAt": now.isoformat(),
                    "quantity": str(group["remainingClosableQuantity"]),
                    "perpetualSymbol": group["perpetualSymbol"],
                    "spotSymbol": group["spotSymbol"],
                    "spotSourceAsOf": context["spotQuote"]["sourceAsOf"],
                    "perpetualSourceAsOf": context["perpetualQuote"]["sourceAsOf"],
                },
            )
            if claimed:
                _submit_original_trigger(claimed)
        except Exception as exc:
            healthy = False
            error = str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
            repository.set_error(open_id, error[:300] or type(exc).__name__)
            LOGGER.warning("Funding spread exit %s paused: %s", open_id, type(exc).__name__)
    return healthy


async def run_funding_exit_monitor(stop: asyncio.Event) -> None:
    while not stop.is_set():
        monitor_health.begin("funding_exit")
        try:
            healthy = await asyncio.to_thread(evaluate_exit_plans)
            monitor_health.finish("funding_exit", None if healthy else "exit_plan_paused")
        except Exception as exc:
            monitor_health.finish("funding_exit", type(exc).__name__)
            LOGGER.warning("Funding exit monitor paused: %s", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=2)
        except TimeoutError:
            pass
