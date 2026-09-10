from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import ROUND_FLOOR, Decimal
from typing import Any

import httpx
from fastapi import HTTPException

from app import runtime_transport
from app.config import get_settings
from app.database import connection
from app.execution_batches import get_execution_batch
from app.execution_risk_repository import batch_has_verified_flattening
from app.strategies.adapters.funding_carry import SPOT_BASE_FEE_RATE, funding_open_quantities
from app.strategies.domain import StrategyInstructionAction
from app.strategies.funding_orchestration import get_funding_controlled_live_readiness
from app.strategies.instruction_service import (
    CreateStrategyInstructionRequest,
    create_instruction,
    execute_instruction,
    get_instruction,
    get_instruction_by_idempotency,
    list_instructions,
)
from app.strategies.plan_service import funding_account_binding, funding_market_access_ready
from app.strategy_financial_readmodel import canonical_fills

STRATEGY_INSTANCE_ID = "strategy_funding_arbitrage_instance_default"
QUOTE_CURRENCY = "USDT"


def list_funding_pairs() -> list[dict[str, str]]:
    account = _funding_account_binding()
    with connection() as db:
        rows = db.execute(
            """
            SELECT
                perp.id AS perpetual_instrument_id,
                perp_map.external_symbol AS perpetual_symbol,
                perp.base_currency AS base_currency,
                perp.quote_currency AS quote_currency,
                spot.id AS spot_instrument_id,
                spot_map.external_symbol AS spot_symbol
            FROM instrument_mappings AS perp_map
            JOIN instruments AS perp ON perp.id = perp_map.instrument_id
            JOIN contract_specifications AS perp_spec ON perp_spec.instrument_id = perp.id
            JOIN instrument_mappings AS spot_map
              ON spot_map.venue_id = perp_map.venue_id
             AND upper(spot_map.external_symbol) = upper(perp.base_currency || perp.quote_currency)
             AND spot_map.status = 'active'
            JOIN instruments AS spot ON spot.id = spot_map.instrument_id
            JOIN contract_specifications AS spot_spec ON spot_spec.instrument_id = spot.id
            WHERE perp_map.venue_id = ?
              AND perp_map.status = 'active'
              AND perp.instrument_type = 'crypto_perp'
              AND spot.instrument_type = 'crypto_spot'
              AND perp_spec.data_quality_state = 'complete'
              AND spot_spec.data_quality_state = 'complete'
            ORDER BY perp.base_currency, perp_map.external_symbol
            """,
            (account["venue_id"],),
        ).fetchall()
    pairs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["perpetual_symbol"]).upper(), str(row["spot_symbol"]).upper())
        if key in seen:
            continue
        seen.add(key)
        pairs.append(
            {
                "baseAsset": str(row["base_currency"]).upper(),
                "quoteCurrency": str(row["quote_currency"]).upper(),
                "perpetualSymbol": str(row["perpetual_symbol"]).upper(),
                "spotSymbol": str(row["spot_symbol"]).upper(),
                "perpetualInstrumentId": str(row["perpetual_instrument_id"]),
                "spotInstrumentId": str(row["spot_instrument_id"]),
            }
        )
    return pairs


def get_funding_execution_context(
    *,
    perpetual_symbol: str | None,
    spot_symbol: str | None,
    notional: Decimal | None,
    quantity: Decimal | None = None,
) -> dict[str, Any]:
    account = _funding_account_binding()
    pair = _resolve_pair(perpetual_symbol=perpetual_symbol, spot_symbol=spot_symbol)
    perp_symbol = str(pair["perpetualSymbol"])
    spot_symbol = str(pair["spotSymbol"])
    requests = [
        (f"/venue/quotes/{perp_symbol}", "crypto_perp", "linear"),
        (f"/venue/quotes/{spot_symbol}", "crypto_spot", "spot"),
        (f"/venue/instruments/{perp_symbol}", "crypto_perp", "linear"),
        (f"/venue/instruments/{spot_symbol}", "crypto_spot", "spot"),
    ]
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="funding-context") as pool:
        futures = [
            pool.submit(
                _runtime_get,
                path,
                params={
                    "accountId": account["account_id"],
                    "instrumentType": instrument_type,
                    "category": category,
                },
            )
            for path, instrument_type, category in requests
        ]
        values: list[dict[str, Any]] = []
        for future in futures:
            payload = future.result()
            if not isinstance(payload, dict):
                raise HTTPException(status_code=502, detail="Funding market response is malformed")
            values.append(payload)
        perp_quote, spot_quote, perp_spec, spot_spec = values
    active_balance = _balance_snapshot(account["account_id"], QUOTE_CURRENCY)
    reservation_summary = _reservation_summary(account["account_id"], QUOTE_CURRENCY)
    readiness = get_funding_controlled_live_readiness(
        strategy_instance_id=STRATEGY_INSTANCE_ID,
        account_id=account["account_id"],
    )
    with connection() as db:
        live_account = db.execute(
            "SELECT environment FROM accounts WHERE id=?", (account["account_id"],)
        ).fetchone()
    if live_account is not None and live_account["environment"] == "live":
        readiness["bothMarketsTradeAllowed"] = funding_market_access_ready(
            perp_spec, "crypto_perp"
        ) and funding_market_access_ready(spot_spec, "crypto_spot")
        readiness["ready"] = readiness["ready"] and readiness["bothMarketsTradeAllowed"]
    runtime_status = _runtime_status()
    suggested_quantity = _suggest_quantity(
        notional=notional,
        price=Decimal(str(spot_quote["mid"])),
        step=Decimal(str(spot_spec["quantityStep"])),
        minimum=Decimal(str(spot_spec["minQuantity"])),
    )
    fee_rate = (
        SPOT_BASE_FEE_RATE
        if live_account is not None and live_account["environment"] == "live"
        else Decimal("0")
    )
    sizing = _open_sizing(
        quantity if quantity is not None else suggested_quantity,
        fee_rate=fee_rate,
        perp_spec=perp_spec,
        spot_spec=spot_spec,
        perp_quote=perp_quote,
        spot_quote=spot_quote,
    )
    funding_rate = (
        _decimal_text(Decimal(str(perp_quote["fundingRate"])))
        if perp_quote.get("fundingRate") not in (None, "")
        else None
    )
    next_funding_time = perp_quote.get("nextFundingTime")
    basis = Decimal(str(perp_quote["mid"])) - Decimal(str(spot_quote["mid"]))
    active_available_balance = (
        Decimal(str(active_balance["availableBalance"]))
        if active_balance is not None and active_balance["availableBalance"] is not None
        else None
    )
    funding_available = (
        active_available_balance - reservation_summary["activeReserved"]
        if active_available_balance is not None
        else None
    )
    return {
        "accountId": account["account_id"],
        "venue": account["venue_code"],
        "spotSymbol": spot_symbol,
        "perpetualSymbol": perp_symbol,
        "symbolOptions": list_funding_pairs(),
        "spotQuote": spot_quote,
        "perpetualQuote": perp_quote,
        "fundingRate": funding_rate,
        "nextFundingTime": next_funding_time,
        "basis": _decimal_text(basis),
        "tickSize": {
            "spot": spot_spec["priceTick"],
            "perpetual": perp_spec["priceTick"],
        },
        "quantityStep": {
            "spot": spot_spec["quantityStep"],
            "perpetual": perp_spec["quantityStep"],
        },
        "minimumQuantity": {
            "spot": spot_spec["minQuantity"],
            "perpetual": perp_spec["minQuantity"],
        },
        "contractMultiplier": {
            "spot": spot_spec["contractMultiplier"],
            "perpetual": perp_spec["contractMultiplier"],
        },
        "suggestedQuantity": _decimal_text(suggested_quantity),
        "openSizing": sizing,
        "requestedNotional": _decimal_text(notional),
        "availableBalance": active_balance,
        "activeReservation": {
            "currency": QUOTE_CURRENCY,
            "activeReserved": _decimal_text(reservation_summary["activeReserved"]),
            "fundingReserved": _decimal_text(reservation_summary["fundingReserved"]),
            "crossReserved": _decimal_text(reservation_summary["crossReserved"]),
            "fundingAvailable": _decimal_text(funding_available),
        },
        "sharedResourceClaims": reservation_summary["claims"],
        "controlledLiveReadiness": readiness,
        "runtime": runtime_status,
        "dataQualityState": _aggregate_quality(
            active_balance["dataQualityState"] if active_balance is not None else "partial",
            str(perp_quote.get("dataQualityState") or "partial"),
            str(spot_quote.get("dataQualityState") or "partial"),
        ),
        "asOf": max(
            [
                str(active_balance["asOf"]) if active_balance is not None else "",
                str(perp_quote.get("asOf") or ""),
                str(spot_quote.get("asOf") or ""),
            ]
        ),
    }


def list_funding_position_groups(*, scope: str = "active") -> list[dict[str, Any]]:
    if scope not in {"active", "history", "all"}:
        raise HTTPException(status_code=422, detail="Unsupported Funding position scope")
    instructions = list_instructions(STRATEGY_INSTANCE_ID)
    close_summary = _close_summary_by_open_instruction(instructions)
    groups: list[dict[str, Any]] = []
    for instruction in instructions:
        if instruction["action"] != StrategyInstructionAction.OPEN.value:
            continue
        batch_id = instruction.get("executionBatchId")
        if not batch_id:
            continue
        group = _funding_group_snapshot(
            instruction_id=str(instruction["instructionId"]),
            batch_id=str(batch_id),
            close_summary=close_summary.get(str(instruction["instructionId"])),
        )
        lifecycle_state = str(group["lifecycleState"])
        if scope == "active" and lifecycle_state != "active":
            continue
        if scope == "history" and lifecycle_state == "active":
            continue
        groups.append(group)
    return groups


def submit_funding_instruction(
    *,
    action: str,
    idempotency_key: str,
    perpetual_symbol: str,
    spot_symbol: str,
    quantity: Decimal,
    requested_by: str,
    target_open_instruction_id: str | None = None,
    execution_policy: str = "post_only_chase",
    perpetual_limit_price: Decimal | None = None,
    expected_perpetual_quantity: Decimal | None = None,
) -> dict[str, Any]:
    normalized_action = StrategyInstructionAction(action)
    try:
        existing = get_instruction_by_idempotency(STRATEGY_INSTANCE_ID, idempotency_key)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
    else:
        parameters = existing["requestedParameters"]
        if (
            existing["action"] != action
            or not isinstance(parameters, dict)
            or Decimal(
                str(parameters.get("spotQuantity" if action == "open" else "perpetualQuantity"))
            )
            != quantity
            or (
                expected_perpetual_quantity is not None
                and Decimal(str(parameters.get("perpetualQuantity"))) != expected_perpetual_quantity
            )
            or parameters.get("perpetualSymbol") != perpetual_symbol
            or parameters.get("spotSymbol") != spot_symbol
            or (parameters.get("targetOpenInstructionId") or None) != target_open_instruction_id
            or parameters.get("executionPolicy", "post_only_chase") != execution_policy
            or (
                Decimal(str(parameters["perpetualLimitPrice"]))
                if parameters.get("perpetualLimitPrice") is not None
                else None
            )
            != perpetual_limit_price
        ):
            raise HTTPException(
                status_code=409,
                detail="Funding idempotency key conflicts with original instruction",
            )
        return _execute_funding_instruction(existing)
    spot_quantity = quantity
    perpetual_quantity = quantity
    spot_fee_rate: str | None = None
    if normalized_action is StrategyInstructionAction.OPEN:
        context = get_funding_execution_context(
            perpetual_symbol=perpetual_symbol,
            spot_symbol=spot_symbol,
            notional=None,
            quantity=quantity,
        )
        sizing = context["openSizing"]
        if not sizing["valid"]:
            raise HTTPException(status_code=422, detail=sizing["reason"])
        perpetual_quantity = Decimal(str(sizing["perpetualQuantity"]))
        spot_fee_rate = str(sizing["spotBaseFeeRate"])
        if (
            expected_perpetual_quantity is not None
            and perpetual_quantity != expected_perpetual_quantity
        ):
            raise HTTPException(status_code=409, detail="配平数量已变化，请刷新后重新确认")
    if normalized_action is StrategyInstructionAction.CLOSE:
        if not target_open_instruction_id:
            raise HTTPException(
                status_code=409,
                detail="Funding close requires a target open instruction",
            )
        open_instruction = get_instruction(target_open_instruction_id)
        batch_id = open_instruction.get("executionBatchId")
        if not batch_id:
            raise HTTPException(status_code=409, detail="Funding close target is unavailable")
        target_group = _funding_group_snapshot(
            instruction_id=target_open_instruction_id,
            batch_id=str(batch_id),
            close_summary=_close_summary_by_open_instruction(
                list_instructions(STRATEGY_INSTANCE_ID)
            ).get(target_open_instruction_id),
        )
        remaining = Decimal(str(target_group["remainingClosableQuantity"] or "0"))
        if remaining <= 0:
            raise HTTPException(
                status_code=409,
                detail="Funding close target has no remaining hedged quantity",
            )
        if quantity > remaining:
            raise HTTPException(
                status_code=409,
                detail="Funding close quantity exceeds remaining hedged quantity",
            )
        perpetual_symbol = str(target_group["perpetualSymbol"])
        spot_symbol = str(target_group["spotSymbol"])
        if target_group.get("spotFeeAdjusted"):
            net_spot = target_group.get("remainingSpotQuantity")
            if net_spot is None:
                raise HTTPException(
                    status_code=409, detail="现货实际到账和手续费尚未核实，请同步成交后平仓"
                )
            step = Decimal(str(target_group["spotQuantityStep"]))
            spot_quantity = (
                quantity / remaining * Decimal(str(net_spot)) / step
            ).to_integral_value(rounding=ROUND_FLOOR) * step
            if spot_quantity <= 0:
                raise HTTPException(status_code=409, detail="本次平仓对应的现货数量小于交易步长")
    instruction = create_instruction(
        STRATEGY_INSTANCE_ID,
        CreateStrategyInstructionRequest(
            idempotencyKey=idempotency_key,
            action=normalized_action,
            parameters={
                "perpetualSymbol": perpetual_symbol,
                "perpetualQuantity": perpetual_quantity,
                "spotSymbol": spot_symbol,
                "spotQuantity": spot_quantity,
                "executionPolicy": execution_policy,
                "perpetualLimitPrice": perpetual_limit_price,
                **({"spotBaseFeeRate": spot_fee_rate} if spot_fee_rate is not None else {}),
                **(
                    {"targetOpenInstructionId": target_open_instruction_id}
                    if target_open_instruction_id
                    else {}
                ),
            },
            reason="funding workspace submit",
        ),
        requested_by=requested_by,
    )
    return _execute_funding_instruction(instruction)


def _execute_funding_instruction(instruction: dict[str, Any]) -> dict[str, Any]:
    batch = execute_instruction(str(instruction["instructionId"]))
    refreshed = get_instruction(str(instruction["instructionId"]))
    return {
        "instruction": refreshed,
        "executionBatch": batch.model_dump(by_alias=True),
        "workspaceState": _workspace_state_from_instruction(refreshed),
    }


def get_funding_instruction_workspace(instruction_id: str) -> dict[str, Any]:
    instruction = get_instruction(instruction_id)
    batch_id = instruction.get("executionBatchId")
    batch = get_execution_batch(str(batch_id)).model_dump(by_alias=True) if batch_id else None
    return {
        "instruction": instruction,
        "executionBatch": batch,
        "workspaceState": _workspace_state_from_instruction(instruction),
    }


def get_funding_instruction_workspace_by_idempotency(
    idempotency_key: str,
) -> dict[str, Any]:
    instruction = get_instruction_by_idempotency(STRATEGY_INSTANCE_ID, idempotency_key)
    return get_funding_instruction_workspace(str(instruction["instructionId"]))


def _workspace_state_from_instruction(instruction: dict[str, Any]) -> dict[str, Any]:
    batch_id = instruction.get("executionBatchId")
    batch = get_execution_batch(str(batch_id)) if batch_id else None
    attempts: list[dict[str, Any]] = []
    releases: list[dict[str, Any]] = []
    cumulative_fill = Decimal("0")
    if batch_id:
        with connection() as db:
            attempt_rows = db.execute(
                """
                SELECT attempt_number, idempotency_key, order_id, status, requested_quantity,
                       limit_price, failure_reason, created_at, updated_at
                FROM funding_perpetual_attempts
                WHERE batch_id = ?
                ORDER BY attempt_number
                """,
                (batch_id,),
            ).fetchall()
            release_rows = db.execute(
                """
                SELECT child_id, cumulative_perpetual_fill, release_quantity,
                       cumulative_spot_quantity, order_id, status, failure_reason,
                       created_at, updated_at
                FROM funding_spot_release_commands
                WHERE batch_id = ?
                ORDER BY created_at
                """,
                (batch_id,),
            ).fetchall()
            order_ids = {
                row["order_id"] for row in [*attempt_rows, *release_rows] if row["order_id"]
            }
            placeholders = ",".join("?" for _ in order_ids) or "NULL"
            fill_rows = db.execute(
                "SELECT f.*, f.id AS fill_id, o.quantity AS requested_quantity "
                "FROM fills f JOIN orders o ON o.id=f.order_id "
                f"WHERE o.id IN ({placeholders}) ORDER BY f.occurred_at,f.id",
                list(order_ids),
            ).fetchall()
            filled_by_order: dict[str, Decimal] = {}
            for fill in canonical_fills(fill_rows):
                order_id = str(fill["order_id"])
                filled_by_order[order_id] = filled_by_order.get(order_id, Decimal("0")) + Decimal(
                    str(fill["quantity"])
                )
        attempts = [
            {
                "attemptNumber": int(row["attempt_number"]),
                "idempotencyKey": row["idempotency_key"],
                "orderId": row["order_id"],
                "status": row["status"],
                "requestedQuantity": row["requested_quantity"],
                "limitPrice": row["limit_price"],
                "failureReason": row["failure_reason"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in attempt_rows
        ]
        releases = [
            {
                "childId": row["child_id"],
                "cumulativePerpetualFill": row["cumulative_perpetual_fill"],
                "releaseQuantity": row["release_quantity"],
                "cumulativeSpotQuantity": row["cumulative_spot_quantity"],
                "filledQuantity": str(filled_by_order.get(row["order_id"], Decimal("0"))),
                "orderId": row["order_id"],
                "status": row["status"],
                "failureReason": row["failure_reason"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in release_rows
        ]
        cumulative_fill = sum(
            (filled_by_order.get(row["order_id"], Decimal("0")) for row in attempt_rows),
            Decimal("0"),
        )
    return {
        "executionState": _execution_state(instruction, batch, attempts, releases),
        "timeline": _timeline_entries(instruction, batch, attempts, releases),
        "attempts": attempts,
        "spotReleases": releases,
        "cumulativePerpetualFill": _decimal_text(cumulative_fill),
        "cumulativeSpotFill": str(
            sum((Decimal(row["filledQuantity"]) for row in releases), Decimal("0"))
        ),
    }


def _timeline_entries(
    instruction: dict[str, Any],
    batch,
    attempts: list[dict[str, Any]],
    releases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    entries = [
        {"code": "instruction_accepted", "status": "completed", "at": instruction["createdAt"]},
        {"code": "plan_resolved", "status": "completed", "at": instruction["createdAt"]},
    ]
    if batch is not None:
        entries.append(
            {
                "code": "claim_reservation_acquired",
                "status": "completed" if batch.status != "pending" else "active",
                "at": batch.created_at.isoformat(),
            }
        )
    if attempts:
        latest = attempts[-1]
        entries.append(
            {
                "code": "perpetual_attempt_submitted",
                "status": latest["status"],
                "at": latest["createdAt"],
                "detail": latest["idempotencyKey"],
            }
        )
        if latest.get("orderId"):
            entries.append(
                {
                    "code": "ack_external_order_identity",
                    "status": latest["status"],
                    "at": latest["updatedAt"],
                    "detail": latest["orderId"],
                }
            )
    if releases:
        latest_release = releases[-1]
        entries.append(
            {
                "code": "spot_release",
                "status": latest_release["status"],
                "at": latest_release["updatedAt"],
                "detail": latest_release["releaseQuantity"],
            }
        )
    if instruction["status"] == "reconciling":
        entries.append({"code": "reconciling", "status": "active", "at": instruction["updatedAt"]})
    if batch is not None and batch.status == "hedged":
        entries.append(
            {"code": "hedged", "status": "completed", "at": batch.updated_at.isoformat()}
        )
    if instruction["status"] == "completed":
        entries.append({"code": "completed", "status": "completed", "at": instruction["updatedAt"]})
    if instruction["status"] in {"failed", "manual_intervention"}:
        entries.append(
            {
                "code": instruction["status"],
                "status": "terminal",
                "at": instruction["updatedAt"],
                "detail": instruction.get("failureReason"),
            }
        )
    return entries


def _execution_state(instruction: dict[str, Any], batch, attempts, releases) -> str:
    if instruction["status"] == "accepted":
        return "accepted"
    if instruction["status"] == "reconciling":
        return "reconciling"
    if instruction["status"] == "completed":
        return "completed"
    if instruction["status"] == "manual_intervention":
        return "manual_intervention"
    if instruction["status"] in {"failed", "rejected"}:
        return "failed"
    if any(row["status"] == "result_unknown" for row in attempts) or any(
        row["status"] == "result_unknown" for row in releases
    ):
        return "result_unknown"
    if batch is not None and batch.status == "hedged":
        return "partially_hedged"
    if attempts:
        return "executing"
    return "submitting"


def _funding_group_snapshot(
    *,
    instruction_id: str,
    batch_id: str,
    close_summary: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    instruction = get_instruction(instruction_id)
    workspace = _workspace_state_from_instruction(instruction)
    plan = instruction["executionPlan"]
    if not isinstance(plan, dict) or not isinstance(plan.get("legs"), list):
        raise HTTPException(status_code=409, detail="Funding execution plan is unavailable")
    perp = next(leg for leg in plan["legs"] if leg["role"] == "perpetual_leg")
    spot = next(leg for leg in plan["legs"] if leg["role"] == "spot_leg")
    cumulative_spot = Decimal(str(workspace["cumulativeSpotFill"]))
    cumulative_perp = Decimal(str(workspace["cumulativePerpetualFill"] or "0"))
    requested_perp = Decimal(str(perp["maximumQuantity"]))
    requested_spot = Decimal(str(spot["maximumQuantity"]))
    hedged_quantity = min(cumulative_perp, cumulative_spot * requested_perp / requested_spot)
    residual = max(Decimal("0"), cumulative_perp - hedged_quantity)
    flattened = batch_has_verified_flattening(batch_id)
    authoritative_closed = (close_summary or {}).get("authoritativeClosedQuantity", Decimal("0"))
    if flattened:
        authoritative_closed = cumulative_perp
        residual = Decimal("0")
    pending_close = (close_summary or {}).get("pendingCloseQuantity", Decimal("0"))
    result_unknown_reserved = (close_summary or {}).get(
        "resultUnknownReservedQuantity", Decimal("0")
    )
    reserved_or_closed = authoritative_closed + pending_close + result_unknown_reserved
    remaining_closable = max(Decimal("0"), hedged_quantity - reserved_or_closed)
    lifecycle_state = (
        "history"
        if flattened
        or (
            hedged_quantity > 0
            and authoritative_closed >= hedged_quantity
            and pending_close == 0
            and result_unknown_reserved == 0
        )
        or (
            instruction["status"] in {"failed", "rejected"}
            and _workspace_has_confirmed_no_external_side_effects(workspace)
        )
        else "active"
    )
    funding_fees, trading_fees = _funding_fees_for_batch(batch_id)
    net_spot = None
    fee_adjusted = False
    if spot.get("accountId"):
        with connection() as db:
            account = db.execute(
                "SELECT environment FROM accounts WHERE id=?", (spot["accountId"],)
            ).fetchone()
        fee_adjusted = account is not None and str(account["environment"]).lower() == "live"
        if fee_adjusted:
            from app.strategy_financial_readmodel import funding_spot_cash

            net_spot = funding_spot_cash(batch_id, cumulative_spot)
    remaining_spot = (
        max(Decimal("0"), net_spot - (close_summary or {}).get("spotSoldOrReserved", Decimal("0")))
        if net_spot is not None
        else None
    )
    if flattened:
        remaining_spot = Decimal("0")
    remaining_perp = max(
        Decimal("0"),
        cumulative_perp
        - (close_summary or {}).get("perpetualClosedQuantity", authoritative_closed),
    )
    spot_holding = (
        max(Decimal("0"), net_spot - (close_summary or {}).get("spotSoldQuantity", Decimal("0")))
        if net_spot is not None
        else None
    )
    if flattened:
        remaining_perp = Decimal("0")
        spot_holding = Decimal("0")
    net_delta = spot_holding - remaining_perp if spot_holding is not None else None
    step = Decimal(str(perp.get("quantityStep") or "0"))
    fee_mismatch = (
        workspace["executionState"] == "completed"
        and lifecycle_state == "active"
        and net_delta is not None
        and remaining_perp > 0
        and pending_close == 0
        and result_unknown_reserved == 0
        and (net_delta < 0 or (step > 0 and net_delta >= step))
    )
    is_abnormal = lifecycle_state == "active" and (
        workspace["executionState"] in {"manual_intervention", "result_unknown", "failed"}
        or result_unknown_reserved > 0
        or (workspace["executionState"] == "completed" and residual != 0)
        or fee_mismatch
    )
    abnormal_action = "reconcile"
    if (
        is_abnormal
        and reserved_or_closed == 0
        and instruction["status"] in {"failed", "manual_intervention"}
    ):
        from app.execution_risk_repository import (
            ExecutionRiskRepositoryError,
            flattening_positions,
        )

        try:
            with connection() as db:
                residual_positions, _ = flattening_positions(db, batch_id)
            if any(position["quantity"] > 0 for position in residual_positions):
                abnormal_action = "flatten_open"
        except (ExecutionRiskRepositoryError, ValueError, ArithmeticError):
            pass  # Unconfirmed executions cannot offer a new reduction order.
    elif is_abnormal and remaining_closable > 0 and result_unknown_reserved == 0 and residual == 0:
        abnormal_action = "close_group"
    return {
        "isAbnormal": is_abnormal,
        "abnormalAction": abnormal_action,
        "abnormalReason": (
            f"手续费未配平：现货净持币与永续空仓相差 {_decimal_text(net_delta)}，保留仓位待手动平仓"
            if fee_mismatch
            else str(instruction.get("failureReason") or "开平仓执行异常，需核对两腿成交")
            if is_abnormal
            else None
        ),
        "openInstructionId": instruction_id,
        "instructionId": instruction_id,
        "batchId": batch_id,
        "status": workspace["executionState"],
        "perpetualSymbol": perp["externalSymbol"],
        "spotSymbol": spot["externalSymbol"],
        "perpetualSide": perp["side"],
        "spotSide": spot["side"],
        "perpetualRequestedQuantity": perp["maximumQuantity"],
        "spotRequestedQuantity": spot["maximumQuantity"],
        "cumulativePerpetualFill": _decimal_text(cumulative_perp),
        "cumulativeSpotFill": _decimal_text(cumulative_spot),
        "hedgedQuantity": _decimal_text(hedged_quantity),
        "spotFeeAdjusted": fee_adjusted,
        "netSpotAcquired": _decimal_text(net_spot),
        "spotFeeResidualQuantity": _decimal_text(cumulative_spot - net_spot)
        if net_spot is not None
        else None,
        "remainingSpotQuantity": _decimal_text(remaining_spot),
        "remainingPerpetualQuantity": _decimal_text(remaining_perp),
        "remainingSpotHolding": _decimal_text(spot_holding),
        "netDeltaQuantity": _decimal_text(net_delta),
        "spotQuantityStep": spot.get("quantityStep"),
        "residualQuantity": _decimal_text(residual),
        "alreadyClosedQuantity": _decimal_text(authoritative_closed),
        "authoritativeClosedQuantity": _decimal_text(authoritative_closed),
        "pendingCloseQuantity": _decimal_text(pending_close),
        "resultUnknownReservedQuantity": _decimal_text(result_unknown_reserved),
        "remainingClosableQuantity": _decimal_text(remaining_closable),
        "lifecycleState": lifecycle_state,
        "fundingFees": _decimal_text(funding_fees),
        "fees": _decimal_text(trading_fees),
        "pnl": None,
        "asOf": instruction["updatedAt"],
        "workspaceState": workspace,
    }


def _close_summary_by_open_instruction(
    instructions: list[dict[str, Any]],
) -> dict[str, dict[str, Decimal]]:
    summary: dict[str, dict[str, Decimal]] = {}
    pending_states = {"accepted", "submitting", "executing", "partially_hedged", "reconciling"}
    uncertain_states = {"manual_intervention", "result_unknown"}
    for instruction in instructions:
        if instruction["action"] != StrategyInstructionAction.CLOSE.value:
            continue
        parameters = instruction.get("requestedParameters") or {}
        if not isinstance(parameters, dict):
            continue
        target_id = str(parameters.get("targetOpenInstructionId") or "").strip()
        if not target_id:
            continue
        quantity = Decimal(
            str(parameters.get("perpetualQuantity") or parameters.get("spotQuantity") or "0")
        )
        workspace = _workspace_state_from_instruction(instruction)
        perpetual_fill = Decimal(str(workspace.get("cumulativePerpetualFill") or "0"))
        spot_fill = Decimal(str(workspace["cumulativeSpotFill"]))
        requested_spot = Decimal(str(parameters.get("spotQuantity") or quantity))
        spot_in_perpetual_units = (
            spot_fill * quantity / requested_spot if requested_spot > 0 else Decimal("0")
        )
        authoritative = min(quantity, perpetual_fill, spot_in_perpetual_units)
        unresolved = max(Decimal("0"), quantity - authoritative)
        execution_state = str(workspace.get("executionState") or instruction["status"])
        pending = unresolved if execution_state in pending_states else Decimal("0")
        uncertain = unresolved if execution_state in uncertain_states else Decimal("0")
        if execution_state == "failed" and unresolved > 0:
            if _workspace_has_confirmed_no_external_side_effects(workspace):
                pending = Decimal("0")
                uncertain = Decimal("0")
            else:
                uncertain = unresolved
        if execution_state == "completed" and unresolved > 0:
            # A completed close without matching authoritative fills is internally
            # inconsistent. Preserve the unresolved amount instead of allowing a
            # second close to enlarge exposure.
            uncertain = unresolved
        bucket = summary.setdefault(
            target_id,
            {
                "authoritativeClosedQuantity": Decimal("0"),
                "pendingCloseQuantity": Decimal("0"),
                "resultUnknownReservedQuantity": Decimal("0"),
            },
        )
        bucket["authoritativeClosedQuantity"] += authoritative
        bucket["perpetualClosedQuantity"] = (
            bucket.get("perpetualClosedQuantity", Decimal("0")) + perpetual_fill
        )
        bucket["spotSoldQuantity"] = bucket.get("spotSoldQuantity", Decimal("0")) + spot_fill
        bucket["spotSoldOrReserved"] = (
            bucket.get("spotSoldOrReserved", Decimal("0"))
            + spot_fill
            + (pending + uncertain) * requested_spot / quantity
        )
        bucket["pendingCloseQuantity"] += pending
        bucket["resultUnknownReservedQuantity"] += uncertain
    return summary


def _workspace_has_confirmed_no_external_side_effects(workspace: dict[str, Any]) -> bool:
    if Decimal(str(workspace.get("cumulativePerpetualFill") or "0")) > 0:
        return False
    for row in workspace.get("attempts", []):
        if not isinstance(row, dict):
            continue
        if row.get("orderId") not in (None, "") and row.get("status") not in {
            "canceled",
            "rejected",
        }:
            return False
    for row in workspace.get("spotReleases", []):
        if not isinstance(row, dict):
            continue
        if row.get("orderId") not in (None, ""):
            return False
        if Decimal(str(row.get("cumulativeSpotQuantity") or "0")) > 0:
            return False
    return True


def _funding_fees_for_batch(batch_id: str) -> tuple[Decimal | None, Decimal | None]:
    from app.strategy_financial_readmodel import batch_fee_totals

    return batch_fee_totals(batch_id)


def _funding_account_binding() -> dict[str, str]:
    with connection() as db:
        row = funding_account_binding(db, STRATEGY_INSTANCE_ID)
    return {
        "account_id": str(row["account_id"]),
        "venue_id": str(row["venue_id"]),
        "venue_code": str(row["venue_code"]),
    }


def _resolve_pair(*, perpetual_symbol: str | None, spot_symbol: str | None) -> dict[str, str]:
    pairs = list_funding_pairs()
    if not pairs:
        raise HTTPException(status_code=503, detail="Funding instrument mapping is unavailable")
    if perpetual_symbol is None and spot_symbol is None:
        return pairs[0]
    for pair in pairs:
        if perpetual_symbol and pair["perpetualSymbol"] != perpetual_symbol.upper():
            continue
        if spot_symbol and pair["spotSymbol"] != spot_symbol.upper():
            continue
        return pair
    raise HTTPException(status_code=404, detail="Funding symbol pair is unavailable")


def _runtime_get(path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
    settings = get_settings()
    try:
        response = runtime_transport.get(
            f"{settings.runtime_base_url}{path}",
            params=params,
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Funding runtime read failed for {path}",
        ) from exc


def _runtime_status() -> dict[str, Any]:
    payload = _runtime_get("/status")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="Funding runtime status is malformed")
    return {
        "status": payload.get("status"),
        "liveWriteEnabled": bool(
            isinstance(payload.get("capabilities"), dict)
            and payload["capabilities"].get("liveWriteEnabled")
        ),
        "adapters": payload.get("capabilities", {}).get("adapters", [])
        if isinstance(payload.get("capabilities"), dict)
        else [],
    }


def _balance_snapshot(account_id: str, currency: str) -> dict[str, Any] | None:
    with connection() as db:
        latest = db.execute(
            """
            SELECT as_of
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()
        if latest is None:
            return None
        row = db.execute(
            """
            SELECT currency, equity, available_balance, data_quality_state, as_of
            FROM balance_snapshots
            WHERE account_id = ? AND as_of = ? AND upper(currency) = upper(?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (account_id, latest["as_of"], currency),
        ).fetchone()
    if row is None:
        return None
    return {
        "currency": str(row["currency"]).upper(),
        "equity": _decimal_text(Decimal(str(row["equity"]))),
        "availableBalance": (
            _decimal_text(Decimal(str(row["available_balance"])))
            if row["available_balance"] is not None
            else None
        ),
        "dataQualityState": row["data_quality_state"],
        "asOf": row["as_of"],
    }


def _reservation_summary(account_id: str, currency: str) -> dict[str, Any]:
    with connection() as db:
        reservations = db.execute(
            """
            SELECT owner_type, owner_id, reserved_amount
            FROM execution_balance_reservations
            WHERE account_id = ? AND upper(currency) = upper(?) AND status = 'active'
            """,
            (account_id, currency),
        ).fetchall()
        claims = db.execute(
            """
            SELECT resource_key, resource_category, symbol, owner_type, owner_id
            FROM execution_resource_claims
            WHERE account_id = ? AND status = 'active'
            ORDER BY created_at
            """,
            (account_id,),
        ).fetchall()
        owner_strategy: dict[tuple[str, str], str | None] = {}
        owner_pairs = {(str(row["owner_type"]), str(row["owner_id"])) for row in reservations}
        for owner_type, owner_id in owner_pairs:
            strategy_key = None
            if owner_type == "batch":
                batch_row = db.execute(
                    "SELECT strategy_key FROM execution_batches WHERE id = ?",
                    (owner_id,),
                ).fetchone()
                strategy_key = str(batch_row["strategy_key"]) if batch_row is not None else None
            owner_strategy[(owner_type, owner_id)] = strategy_key
    total = Decimal("0")
    funding_reserved = Decimal("0")
    cross_reserved = Decimal("0")
    for row in reservations:
        amount = Decimal(str(row["reserved_amount"]))
        total += amount
        owner_key = (str(row["owner_type"]), str(row["owner_id"]))
        if owner_strategy.get(owner_key) == "funding_arbitrage":
            funding_reserved += amount
        if owner_strategy.get(owner_key) == "cross_venue_spread":
            cross_reserved += amount
    return {
        "activeReserved": total,
        "fundingReserved": funding_reserved,
        "crossReserved": cross_reserved,
        "claims": [
            {
                "resourceKey": row["resource_key"],
                "resourceCategory": row["resource_category"],
                "symbol": row["symbol"],
                "ownerType": row["owner_type"],
                "ownerId": row["owner_id"],
            }
            for row in claims
        ],
    }


def _suggest_quantity(
    *, notional: Decimal | None, price: Decimal, step: Decimal, minimum: Decimal
) -> Decimal | None:
    if notional is None or notional <= 0 or price <= 0:
        return None
    if not all(value.is_finite() for value in (notional, price, step, minimum)) or step <= 0:
        return None
    raw = (notional / price / step).to_integral_value(rounding=ROUND_FLOOR) * step
    return raw if raw >= minimum else None


def _open_sizing(
    quantity: Decimal | None,
    *,
    fee_rate: Decimal,
    perp_spec: dict,
    spot_spec: dict,
    perp_quote: dict,
    spot_quote: dict,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "spotQuantity": _decimal_text(quantity),
        "spotBaseFeeRate": _decimal_text(fee_rate),
        "expectedSpotNetQuantity": None,
        "perpetualQuantity": None,
        "roundingResidualQuantity": None,
        "valid": False,
        "reason": "请输入有效的现货买入数量",
    }
    if quantity is None or quantity <= 0:
        return result
    if any(Decimal(str(spec["contractMultiplier"])) != 1 for spec in (perp_spec, spot_spec)):
        result["reason"] = "当前资费配平只支持币数量乘数为 1 的现货与永续"
        return result
    net, perpetual, residual = funding_open_quantities(
        quantity, fee_rate=fee_rate, perpetual_step=Decimal(str(perp_spec["quantityStep"]))
    )
    result.update(
        expectedSpotNetQuantity=_decimal_text(net),
        perpetualQuantity=_decimal_text(perpetual),
        roundingResidualQuantity=_decimal_text(residual),
    )
    for label, amount, spec, quote in (
        ("现货", quantity, spot_spec, spot_quote),
        ("永续", perpetual, perp_spec, perp_quote),
    ):
        step = Decimal(str(spec["quantityStep"]))
        if amount <= 0 or amount < Decimal(str(spec["minQuantity"])) or amount % step:
            result["reason"] = f"{label}数量不符合最小下单量或步长；永续按现货扣费净额向下取整"
            return result
        minimum_notional = spec.get("minNotional") or spec.get("minNotionalValue")
        if minimum_notional is not None and amount * Decimal(str(quote["mid"])) < Decimal(
            str(minimum_notional)
        ):
            result["reason"] = f"{label}金额低于交易所最低要求，请增加开仓本金"
            return result
    result.update(valid=True, reason=None)
    return result


def _aggregate_quality(*values: str) -> str:
    return "complete" if all(value == "complete" for value in values) else "partial"


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")
