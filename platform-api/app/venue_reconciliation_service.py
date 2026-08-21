from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from app import venue_reconciliation_repository as repository
from app import venue_reconciliation_runtime_client as runtime_client
from app.database import connection
from app.financial_facts import CreateFinancialFactRequest, record_financial_fact
from app.trading import (
    apply_execution_events,
    get_order_row,
    reconcile_order,
    request_from_order_row,
    synchronize_trade_command_status,
)
from app.venue_reconciliation_policy import (
    DifferenceDraft,
    balance_difference_drafts,
    external_order_update_status,
    order_difference_draft,
    order_difference_drafts,
    position_difference_drafts,
)
from app.venue_reconciliation_schemas import (
    DifferenceType,
    OrderVenueReconciliationResponse,
    ReconciliationDifferenceResponse,
    ResolveDifferenceRequest,
    VenueReconciliationRunRequest,
    VenueReconciliationRunResponse,
)


class ReconciliationServiceError(RuntimeError):
    """Base class for explicit reconciliation domain failures."""


class MissingAuthoritativeStrategyError(ReconciliationServiceError):
    pass


class ReconciliationIdempotencyConflictError(ReconciliationServiceError):
    pass


class StrategyAccountNotBoundError(ReconciliationServiceError):
    pass


class ReconciliationRunNotFoundError(ReconciliationServiceError):
    pass


class ReconciliationDifferenceNotFoundError(ReconciliationServiceError):
    pass


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def runtime_get(path: str, params: dict[str, str] | None = None):
    return runtime_client.get(path, params=params)


def strategy_for_order(order_row) -> str:
    strategy_instance_id = repository.load_strategy_instance_id_for_command(order_row["command_id"])
    if strategy_instance_id is None:
        raise MissingAuthoritativeStrategyError(
            "Order has no authoritative StrategyInstance and cannot enter formal reconciliation"
        )
    return strategy_instance_id


def reconcile_order_with_venue(order_id: str) -> OrderVenueReconciliationResponse:
    repository.ensure_schema()
    initial = get_order_row(order_id)
    status_before = initial["status"]
    if status_before == "result_unknown":
        reconcile_order(order_id)
    row = get_order_row(order_id)
    strategy_instance_id = strategy_for_order(row)

    response = runtime_get(f"/venue/orders/by-platform/{order_id}")
    if response.status_code == 404:
        difference_id = standalone_order_difference(
            order_id,
            "missing_external",
            {"status": row["status"]},
            {},
        )
        return OrderVenueReconciliationResponse(
            orderId=order_id,
            commandId=row["command_id"],
            source="runtime",
            externalOrderId=None,
            statusBefore=status_before,
            statusAfter=row["status"],
            recovered=False,
            importedFactIds=[],
            differenceIds=[difference_id],
            reconciledAt=datetime.now(UTC),
        )
    response.raise_for_status()
    external_order = response.json()
    source = str(external_order["source"])

    imported_fact_ids: list[str] = []
    order_fact = record_financial_fact(
        CreateFinancialFactRequest(
            idempotencyKey=(
                f"venue-order:{source}:{external_order['externalOrderId']}:{external_order['asOf']}"
            ),
            factType="external_order",
            source=source,
            externalId=f"{external_order['externalOrderId']}:{external_order['asOf']}",
            strategyInstanceId=strategy_instance_id,
            accountId=row["account_id"],
            instrumentId=row["instrument_id"],
            occurredAt=external_order["asOf"],
            payload=external_order,
        )
    )
    imported_fact_ids.append(order_fact.fact_id)

    fill_response = runtime_get(
        "/venue/fills",
        params={"platformOrderId": order_id},
    )
    fill_response.raise_for_status()
    fills = fill_response.json()
    request = request_from_order_row(row)
    events: list[dict[str, object]] = []
    for fill in fills:
        fact = record_financial_fact(
            CreateFinancialFactRequest(
                idempotencyKey=f"venue-fill:{source}:{fill['externalFillId']}",
                factType="trade_fill",
                source=source,
                externalId=str(fill["externalFillId"]),
                strategyInstanceId=strategy_instance_id,
                accountId=row["account_id"],
                instrumentId=row["instrument_id"],
                side=fill["side"],
                quantity=fill["quantity"],
                price=fill["price"],
                currency=fill["currency"],
                occurredAt=fill["occurredAt"],
                payload=fill,
            )
        )
        imported_fact_ids.append(fact.fact_id)
        events.append(
            {
                "event_id": fill["externalFillId"],
                "command_id": row["command_id"],
                "platform_order_id": order_id,
                "event_type": "order_filled",
                "external_order_id": fill["externalOrderId"],
                "fill_price": fill["price"],
                "fill_quantity": fill["quantity"],
                "occurred_at": fill["occurredAt"],
                "reason": None,
            }
        )

    if events:
        apply_execution_events(
            order_id,
            request,
            events,
            expected_command_id=row["command_id"],
        )
        synchronize_trade_command_status(row["command_id"], order_id)
    elif external_order["status"] in {"accepted", "filled", "rejected", "canceled"}:
        update_order_from_external(row, external_order)

    final = get_order_row(order_id)
    differences = compare_order(order_id, final, external_order, fills)
    repository.audit(
        "venue_order_reconciled",
        "order",
        order_id,
        {
            "source": source,
            "externalOrderId": external_order["externalOrderId"],
            "statusBefore": status_before,
            "statusAfter": final["status"],
            "factIds": imported_fact_ids,
            "differenceIds": differences,
        },
    )
    return OrderVenueReconciliationResponse(
        orderId=order_id,
        commandId=row["command_id"],
        source=source,
        externalOrderId=external_order["externalOrderId"],
        statusBefore=status_before,
        statusAfter=final["status"],
        recovered=status_before == "result_unknown" and final["status"] != "result_unknown",
        importedFactIds=imported_fact_ids,
        differenceIds=differences,
        reconciledAt=datetime.now(UTC),
    )


def resolve_owner_accepted_missing_external_order(
    order_id: str,
) -> OrderVenueReconciliationResponse:
    """Close one result-unknown order only after formal absent-order evidence.

    This is deliberately narrower than a generic override: the Runtime must
    again return 404 for the exact platform-order lookup, and a reconciliation
    reviewer must already have accepted that missing-external difference.
    """
    repository.ensure_schema()
    initial = get_order_row(order_id)
    if initial["status"] != "result_unknown":
        raise ReconciliationDifferenceNotFoundError("Order is not result-unknown")
    response = runtime_get(f"/venue/orders/by-platform/{order_id}")
    if response.status_code != 404:
        raise ReconciliationDifferenceNotFoundError(
            "Venue still has an order record or could not prove it absent"
        )
    with connection() as db:
        proof = db.execute(
            """
            SELECT 1 FROM reconciliation_differences
            WHERE entity_type = 'order' AND difference_type = 'missing_external'
              AND local_reference = ? AND status = 'accepted'
            LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        if proof is None:
            raise ReconciliationDifferenceNotFoundError(
                "Accepted missing-external reconciliation evidence is required"
            )
        leg = db.execute(
            "SELECT batch_id FROM execution_batch_legs WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        batch_id = str(leg["batch_id"]) if leg is not None else None
        if batch_id is not None:
            unsafe = db.execute(
                """
                SELECT 1 FROM execution_batch_legs
                WHERE batch_id = ? AND status IN ('filled', 'partially_filled', 'acknowledged')
                LIMIT 1
                """,
                (batch_id,),
            ).fetchone()
            if unsafe is not None:
                raise ReconciliationDifferenceNotFoundError(
                    "Batch contains external execution evidence and cannot be closed as absent"
                )
        reason = "Owner-accepted reconciliation confirmed no external venue order"
        db.execute(
            "UPDATE orders SET status = 'rejected', updated_at = ? WHERE id = ?",
            (now_iso(), order_id),
        )
        if batch_id is not None:
            db.execute(
                """
                UPDATE execution_batch_legs
                SET status = 'rejected', failure_reason = ?, updated_at = ?
                WHERE order_id = ?
                """,
                (reason, now_iso(), order_id),
            )
            db.execute(
                """
                UPDATE execution_batches
                SET status = 'failed', requires_manual_intervention = 0,
                    failure_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (reason, now_iso(), batch_id),
            )
    repository.audit(
        "result_unknown_absent_order_resolved", "order", order_id, {"batchId": batch_id}
    )
    return reconcile_order_with_venue(order_id)


def update_order_from_external(row, external_order: dict[str, object]) -> None:
    local_status = external_order_update_status(external_order["status"])
    if local_status is None:
        return
    repository.update_order_from_external(
        row["id"],
        local_status,
        external_order["externalOrderId"],
        external_order["asOf"],
    )


def compare_order(
    order_id: str,
    local_row,
    external_order: dict[str, object],
    fills: list[dict[str, object]],
) -> list[str]:
    drafts = order_difference_drafts(
        order_id=order_id,
        local_status=local_row["status"],
        local_fill_quantities=repository.list_fill_quantities(order_id),
        external_order=external_order,
        fills=fills,
    )
    return [persist_standalone_order_difference(order_id, draft) for draft in drafts]


def standalone_order_difference(
    order_id: str,
    difference_type: DifferenceType,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    return persist_standalone_order_difference(
        order_id,
        order_difference_draft(order_id, difference_type, local_value, external_value),
    )


def persist_standalone_order_difference(order_id: str, draft: DifferenceDraft) -> str:
    repository.ensure_schema()
    run_id = f"order-reconcile:{order_id}"
    at = now_iso()
    repository.ensure_standalone_order_run(
        order_id=order_id,
        run_id=run_id,
        payload_hash=canonical_hash({"orderId": order_id}),
        started_at=at,
        completed_at=at,
    )
    return persist_difference_draft(run_id, draft)


def run_account_reconciliation(
    request: VenueReconciliationRunRequest,
) -> VenueReconciliationRunResponse:
    repository.ensure_schema()
    validate_strategy_account(request.strategy_instance_id, request.account_id)
    payload = request.model_dump(by_alias=True, mode="json")
    payload_hash = canonical_hash(payload)
    existing = repository.load_run_by_idempotency_key(request.idempotency_key)
    if existing is not None:
        if existing["payload_hash"] != payload_hash:
            raise ReconciliationIdempotencyConflictError(
                "Reconciliation idempotency key was reused with a different payload"
            )
        return repository.run_from_row(existing)

    positions_response = runtime_get(
        "/venue/positions",
        params={"accountId": request.account_id},
    )
    balances_response = runtime_get(
        "/venue/balances",
        params={"accountId": request.account_id},
    )
    positions_response.raise_for_status()
    balances_response.raise_for_status()
    positions = positions_response.json()
    balances = balances_response.json()
    source = str((positions or balances or [{"source": "runtime"}])[0]["source"])

    run_id = str(uuid4())
    started_at = now_iso()
    repository.create_account_snapshot_run(
        run_id=run_id,
        idempotency_key=request.idempotency_key,
        payload_hash=payload_hash,
        strategy_instance_id=request.strategy_instance_id,
        account_id=request.account_id,
        source=source,
        position_count=len(positions),
        balance_count=len(balances),
        started_at=started_at,
    )

    fact_count = 0
    difference_ids: list[str] = []
    for position in positions:
        fact = record_financial_fact(
            CreateFinancialFactRequest(
                idempotencyKey=(
                    f"venue-position:{source}:{position['externalPositionId']}:{position['asOf']}"
                ),
                factType="position",
                source=source,
                externalId=f"{position['externalPositionId']}:{position['asOf']}",
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                instrumentId=position["instrumentId"],
                occurredAt=position["asOf"],
                payload=position,
            )
        )
        fact_count += 1
        difference_ids.extend(compare_position(run_id, request, position, fact.fact_id))

    for balance in balances:
        record_financial_fact(
            CreateFinancialFactRequest(
                idempotencyKey=f"venue-balance:{source}:{balance['externalBalanceId']}",
                factType="balance",
                source=source,
                externalId=balance["externalBalanceId"],
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                amount=balance["equity"],
                availableBalance=balance["availableBalance"],
                currency=balance["currency"],
                occurredAt=balance["asOf"],
                payload=balance,
            )
        )
        fact_count += 1
        difference_ids.extend(compare_balance(run_id, request, balance))

    completed_at = now_iso()
    status = "completed" if not difference_ids else "completed_with_differences"
    row = repository.complete_account_snapshot_run(
        run_id=run_id,
        status=status,
        fact_count=fact_count,
        difference_count=len(difference_ids),
        completed_at=completed_at,
    )
    repository.audit(
        "venue_reconciliation_completed",
        "venue_reconciliation_run",
        run_id,
        {
            "strategyInstanceId": request.strategy_instance_id,
            "accountId": request.account_id,
            "source": source,
            "factCount": fact_count,
            "differenceIds": difference_ids,
            "actor": request.actor,
        },
    )
    return repository.run_from_row(row)


def validate_strategy_account(strategy_instance_id: str, account_id: str) -> None:
    if not repository.has_active_strategy_account(strategy_instance_id, account_id):
        raise StrategyAccountNotBoundError("Account is not actively bound to strategy")


def compare_position(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
    fact_id: str,
) -> list[str]:
    local = repository.load_comparison_position(
        request.strategy_instance_id,
        request.account_id,
        external["instrumentId"],
    )
    drafts = position_difference_drafts(
        account_id=request.account_id,
        local=local,
        external=external,
        fact_id=fact_id,
    )
    return [persist_difference_draft(run_id, draft) for draft in drafts]


def compare_balance(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
) -> list[str]:
    local = repository.load_latest_balance(request.account_id)
    drafts = balance_difference_drafts(
        account_id=request.account_id,
        local=local,
        external=external,
    )
    return [persist_difference_draft(run_id, draft) for draft in drafts]


def persist_difference_draft(run_id: str, draft: DifferenceDraft) -> str:
    return repository.store_difference(
        run_id,
        draft.difference_key,
        draft.difference_type,
        draft.entity_type,
        draft.local_reference,
        draft.external_reference,
        draft.local_value,
        draft.external_value,
    )


def get_run(run_id: str) -> VenueReconciliationRunResponse:
    repository.ensure_schema()
    row = repository.load_run(run_id)
    if row is None:
        raise ReconciliationRunNotFoundError("Reconciliation run not found")
    return repository.run_from_row(row)


def list_differences(run_id: str) -> list[ReconciliationDifferenceResponse]:
    repository.ensure_schema()
    get_run(run_id)
    return [repository.difference_from_row(row) for row in repository.list_difference_rows(run_id)]


def resolve_difference(
    difference_id: str,
    request: ResolveDifferenceRequest,
) -> ReconciliationDifferenceResponse:
    repository.ensure_schema()
    row, changed = repository.resolve_difference_row(
        difference_id=difference_id,
        status=request.status,
        actor=request.actor,
        reason=request.reason,
        resolved_at=now_iso(),
    )
    if row is None:
        raise ReconciliationDifferenceNotFoundError("Reconciliation difference not found")
    if not changed:
        return repository.difference_from_row(row)
    repository.audit(
        "reconciliation_difference_resolved",
        "reconciliation_difference",
        difference_id,
        {
            "status": request.status,
            "actor": request.actor,
            "reason": request.reason,
        },
    )
    return repository.difference_from_row(row)
