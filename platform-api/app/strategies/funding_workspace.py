from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.database import connection
from app.execution_batches import get_execution_batch
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

STRATEGY_INSTANCE_ID = "strategy_funding_arbitrage_instance_default"
QUOTE_CURRENCY = "USDT"


def list_funding_pairs() -> list[dict[str, str]]:
    account = _funding_account_binding(role="primary")
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
) -> dict[str, object]:
    account = _funding_account_binding(role="primary")
    pair = _resolve_pair(perpetual_symbol=perpetual_symbol, spot_symbol=spot_symbol)
    perp_symbol = str(pair["perpetualSymbol"])
    spot_symbol = str(pair["spotSymbol"])
    perp_quote = _runtime_get(
        f"/venue/quotes/{perp_symbol}",
        params={
            "accountId": account["account_id"],
            "instrumentType": "crypto_perp",
            "category": "linear",
        },
    )
    spot_quote = _runtime_get(
        f"/venue/quotes/{spot_symbol}",
        params={
            "accountId": account["account_id"],
            "instrumentType": "crypto_spot",
            "category": "spot",
        },
    )
    perp_spec = _runtime_get(
        f"/venue/instruments/{perp_symbol}",
        params={
            "accountId": account["account_id"],
            "instrumentType": "crypto_perp",
            "category": "linear",
        },
    )
    spot_spec = _runtime_get(
        f"/venue/instruments/{spot_symbol}",
        params={
            "accountId": account["account_id"],
            "instrumentType": "crypto_spot",
            "category": "spot",
        },
    )
    funding_events = _runtime_get(
        "/venue/economic-events",
        params={"accountId": account["account_id"], "eventType": "funding"},
    )
    active_balance = _balance_snapshot(account["account_id"], QUOTE_CURRENCY)
    reservation_summary = _reservation_summary(account["account_id"], QUOTE_CURRENCY)
    readiness = get_funding_controlled_live_readiness(
        strategy_instance_id=STRATEGY_INSTANCE_ID,
        account_id=account["account_id"],
    )
    runtime_status = _runtime_status()
    quantity = _suggest_quantity(
        notional=notional,
        price=Decimal(str(perp_quote["mid"])),
        step=Decimal(str(perp_spec["quantityStep"])),
        minimum=Decimal(str(perp_spec["minQuantity"])),
    )
    funding_rate = _funding_rate_from_quote_or_events(
        quote_payload=perp_quote,
        funding_events=funding_events,
        perpetual_symbol=perp_symbol,
    )
    next_funding_time = perp_quote.get("nextFundingTime")
    basis = Decimal(str(perp_quote["mid"])) - Decimal(str(spot_quote["mid"]))
    active_available_balance = (
        Decimal(str(active_balance["availableBalance"])) if active_balance is not None else None
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
        "suggestedQuantity": _decimal_text(quantity),
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
                str(active_balance["asOf"]) if active_balance is not None else None,
                str(perp_quote.get("asOf") or ""),
                str(spot_quote.get("asOf") or ""),
            ]
        ),
    }


def list_funding_position_groups(*, scope: str = "active") -> list[dict[str, object]]:
    if scope not in {"active", "history", "all"}:
        raise HTTPException(status_code=422, detail="Unsupported Funding position scope")
    instructions = list_instructions(STRATEGY_INSTANCE_ID)
    close_summary = _close_summary_by_open_instruction(instructions)
    groups: list[dict[str, object]] = []
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
) -> dict[str, object]:
    normalized_action = StrategyInstructionAction(action)
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
    instruction = create_instruction(
        STRATEGY_INSTANCE_ID,
        CreateStrategyInstructionRequest(
            idempotencyKey=idempotency_key,
            action=normalized_action,
            parameters={
                "perpetualSymbol": perpetual_symbol,
                "perpetualQuantity": quantity,
                "spotSymbol": spot_symbol,
                "spotQuantity": quantity,
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
    batch = execute_instruction(str(instruction["instructionId"]))
    refreshed = get_instruction(str(instruction["instructionId"]))
    return {
        "instruction": refreshed,
        "executionBatch": batch.model_dump(by_alias=True),
        "workspaceState": _workspace_state_from_instruction(refreshed),
    }


def get_funding_instruction_workspace(instruction_id: str) -> dict[str, object]:
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
) -> dict[str, object]:
    instruction = get_instruction_by_idempotency(STRATEGY_INSTANCE_ID, idempotency_key)
    return get_funding_instruction_workspace(str(instruction["instructionId"]))


def _workspace_state_from_instruction(instruction: dict[str, object]) -> dict[str, object]:
    batch_id = instruction.get("executionBatchId")
    batch = get_execution_batch(str(batch_id)) if batch_id else None
    attempts: list[dict[str, object]] = []
    releases: list[dict[str, object]] = []
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
                "orderId": row["order_id"],
                "status": row["status"],
                "failureReason": row["failure_reason"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in release_rows
        ]
        if releases:
            cumulative_fill = max(
                (Decimal(str(row["cumulativePerpetualFill"])) for row in releases),
                default=Decimal("0"),
            )
    return {
        "executionState": _execution_state(instruction, batch, attempts, releases),
        "timeline": _timeline_entries(instruction, batch, attempts, releases),
        "attempts": attempts,
        "spotReleases": releases,
        "cumulativePerpetualFill": _decimal_text(cumulative_fill),
    }


def _timeline_entries(
    instruction: dict[str, object],
    batch,
    attempts: list[dict[str, object]],
    releases: list[dict[str, object]],
) -> list[dict[str, object]]:
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
        entries.append(
            {"code": "reconciling", "status": "active", "at": instruction["updatedAt"]}
        )
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


def _execution_state(instruction: dict[str, object], batch, attempts, releases) -> str:
    if instruction["status"] == "accepted":
        return "accepted"
    if instruction["status"] == "reconciling":
        return "reconciling"
    if instruction["status"] == "completed":
        return "completed"
    if instruction["status"] == "manual_intervention":
        return "manual_intervention"
    if instruction["status"] == "failed":
        return "failed"
    if batch is not None and batch.status == "hedged":
        return "partially_hedged"
    if any(row["status"] == "result_unknown" for row in attempts) or any(
        row["status"] == "result_unknown" for row in releases
    ):
        return "result_unknown"
    if attempts:
        return "executing"
    return "submitting"


def _funding_group_snapshot(
    *,
    instruction_id: str,
    batch_id: str,
    close_summary: dict[str, Decimal] | None = None,
) -> dict[str, object]:
    instruction = get_instruction(instruction_id)
    workspace = _workspace_state_from_instruction(instruction)
    plan = instruction["executionPlan"]
    perp = next(leg for leg in plan["legs"] if leg["role"] == "perpetual_leg")
    spot = next(leg for leg in plan["legs"] if leg["role"] == "spot_leg")
    releases = workspace["spotReleases"]
    cumulative_spot = max(
        (Decimal(str(row["cumulativeSpotQuantity"])) for row in releases),
        default=Decimal("0"),
    )
    cumulative_perp = Decimal(str(workspace["cumulativePerpetualFill"] or "0"))
    hedged_quantity = min(cumulative_perp, cumulative_spot)
    residual = max(Decimal("0"), cumulative_perp - cumulative_spot)
    authoritative_closed = (close_summary or {}).get(
        "authoritativeClosedQuantity", Decimal("0")
    )
    pending_close = (close_summary or {}).get("pendingCloseQuantity", Decimal("0"))
    result_unknown_reserved = (close_summary or {}).get(
        "resultUnknownReservedQuantity", Decimal("0")
    )
    reserved_or_closed = authoritative_closed + pending_close + result_unknown_reserved
    remaining_closable = max(Decimal("0"), hedged_quantity - reserved_or_closed)
    lifecycle_state = (
        "history"
        if hedged_quantity > 0
        and authoritative_closed >= hedged_quantity
        and pending_close == 0
        and result_unknown_reserved == 0
        else "active"
    )
    funding_fees, trading_fees = _funding_fees_for_batch(batch_id)
    return {
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
    instructions: list[dict[str, object]],
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
        releases = workspace.get("spotReleases") or []
        spot_fill = max(
            (
                Decimal(str(row.get("cumulativeSpotQuantity") or "0"))
                for row in releases
                if isinstance(row, dict)
            ),
            default=Decimal("0"),
        )
        authoritative = min(quantity, perpetual_fill, spot_fill)
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
        bucket["pendingCloseQuantity"] += pending
        bucket["resultUnknownReservedQuantity"] += uncertain
    return summary


def _workspace_has_confirmed_no_external_side_effects(workspace: dict[str, object]) -> bool:
    if Decimal(str(workspace.get("cumulativePerpetualFill") or "0")) > 0:
        return False
    for row in workspace.get("attempts", []):
        if not isinstance(row, dict):
            continue
        if row.get("orderId") not in (None, ""):
            return False
    for row in workspace.get("spotReleases", []):
        if not isinstance(row, dict):
            continue
        if row.get("orderId") not in (None, ""):
            return False
        if Decimal(str(row.get("cumulativeSpotQuantity") or "0")) > 0:
            return False
    return True


def _funding_fees_for_batch(batch_id: str) -> tuple[Decimal, Decimal]:
    with connection() as db:
        row = db.execute(
            """
            SELECT
                COALESCE(
                    SUM(CASE WHEN ff.fact_type = 'funding_fee' THEN ff.amount ELSE 0 END),
                    0
                ) AS funding_fees,
                COALESCE(
                    SUM(CASE WHEN ff.fact_type = 'trade_fee' THEN ff.amount ELSE 0 END),
                    0
                ) AS trade_fees
            FROM financial_facts AS ff
            WHERE ff.strategy_instance_id = ?
              AND ff.reference_type IN ('order', 'fill', 'economic_event')
              AND ff.idempotency_key LIKE ?
            """,
            (STRATEGY_INSTANCE_ID, f"%{batch_id}%"),
        ).fetchone()
    if row is None:
        return Decimal("0"), Decimal("0")
    return Decimal(str(row["funding_fees"] or "0")), Decimal(str(row["trade_fees"] or "0"))


def _funding_account_binding(*, role: str) -> dict[str, str]:
    with connection() as db:
        row = db.execute(
            """
            SELECT sab.account_id, a.venue_id, v.venue_code AS venue_code
            FROM strategy_account_bindings AS sab
            JOIN accounts AS a ON a.id = sab.account_id
            JOIN venues AS v ON v.id = a.venue_id
            WHERE sab.strategy_instance_id = ?
              AND sab.role = ?
              AND sab.status = 'active'
            LIMIT 1
            """,
            (STRATEGY_INSTANCE_ID, role),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=423, detail="Funding live account binding is unavailable")
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


def _runtime_get(
    path: str, *, params: dict[str, object] | None = None
) -> dict[str, Any] | list[Any]:
    settings = get_settings()
    try:
        with httpx.Client(trust_env=False, timeout=settings.runtime_timeout_seconds) as client:
            response = client.get(f"{settings.runtime_base_url}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Funding runtime read failed for {path}",
        ) from exc


def _runtime_status() -> dict[str, object]:
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


def _balance_snapshot(account_id: str, currency: str) -> dict[str, object] | None:
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
        "availableBalance": _decimal_text(Decimal(str(row["available_balance"]))),
        "dataQualityState": row["data_quality_state"],
        "asOf": row["as_of"],
    }


def _reservation_summary(account_id: str, currency: str) -> dict[str, object]:
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
        owner_pairs = {
            (str(row["owner_type"]), str(row["owner_id"])) for row in reservations
        }
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
    raw = (notional / price).quantize(step, rounding=ROUND_FLOOR)
    return raw if raw >= minimum else minimum


def _funding_rate_from_quote_or_events(
    *,
    quote_payload: dict[str, object] | list[Any],
    funding_events: dict[str, object] | list[Any],
    perpetual_symbol: str,
) -> str | None:
    if isinstance(quote_payload, dict):
        rate = quote_payload.get("fundingRate")
        if rate not in (None, ""):
            return _decimal_text(Decimal(str(rate)))
    if isinstance(funding_events, list):
        for item in funding_events:
            if not isinstance(item, dict):
                continue
            if str(item.get("symbol") or "").upper() != perpetual_symbol:
                continue
            payload = item.get("payload")
            if isinstance(payload, dict):
                candidate = payload.get("fundingRate")
                if candidate not in (None, ""):
                    return _decimal_text(Decimal(str(candidate)))
    return None


def _aggregate_quality(*values: str) -> str:
    return "complete" if all(value == "complete" for value in values) else "partial"


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")
