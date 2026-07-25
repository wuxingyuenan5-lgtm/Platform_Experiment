from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from fastapi import APIRouter, HTTPException

from app import venue_reconciliation_repository as repository
from app import venue_reconciliation_runtime_client as runtime_client
from app import venue_reconciliation_service as service
from app.config import get_settings
from app.trading import get_order_response
from app.venue_reconciliation_policy import DifferenceDraft
from app.venue_reconciliation_schemas import (
    DifferenceStatus,
    DifferenceType,
    OrderVenueReconciliationResponse,
    ReconciliationDifferenceResponse,
    ResolveDifferenceRequest,
    VenueReconciliationRunRequest,
    VenueReconciliationRunResponse,
)

__all__ = [
    "DifferenceStatus",
    "DifferenceType",
    "OrderVenueReconciliationResponse",
    "ReconciliationDifferenceResponse",
    "ResolveDifferenceRequest",
    "VenueReconciliationRunRequest",
    "VenueReconciliationRunResponse",
]

SCHEMA_SQL = repository.SCHEMA_SQL
ensure_schema = repository.ensure_schema
audit = repository.audit
create_difference = repository.store_difference
run_from_row = repository.run_from_row
difference_from_row = repository.difference_from_row
now_iso = service.now_iso
canonical_hash = service.canonical_hash

P = ParamSpec("P")
R = TypeVar("R")


def _call_service(operation: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    try:
        return operation(*args, **kwargs)
    except runtime_client.RuntimeQueryError as exc:
        raise HTTPException(status_code=503, detail="Execution Runtime query failed") from exc
    except service.MissingAuthoritativeStrategyError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "Order has no authoritative StrategyInstance and cannot enter formal "
                "reconciliation"
            ),
        ) from exc
    except service.ReconciliationIdempotencyConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Reconciliation idempotency key was reused with a different payload",
        ) from exc
    except service.StrategyAccountNotBoundError as exc:
        raise HTTPException(
            status_code=403,
            detail="Account is not actively bound to strategy",
        ) from exc
    except service.ReconciliationRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Reconciliation run not found") from exc
    except service.ReconciliationDifferenceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Reconciliation difference not found",
        ) from exc


def runtime_get(path: str, params: dict[str, str] | None = None):
    return _call_service(service.runtime_get, path, params=params)


def strategy_for_order(order_row) -> str:
    return _call_service(service.strategy_for_order, order_row)


def reconcile_order_with_venue(order_id: str) -> OrderVenueReconciliationResponse:
    return _call_service(service.reconcile_order_with_venue, order_id)


def update_order_from_external(row, external_order: dict[str, object]) -> None:
    return _call_service(service.update_order_from_external, row, external_order)


def compare_order(
    order_id: str,
    local_row,
    external_order: dict[str, object],
    fills: list[dict[str, object]],
) -> list[str]:
    return _call_service(
        service.compare_order,
        order_id,
        local_row,
        external_order,
        fills,
    )


def standalone_order_difference(
    order_id: str,
    difference_type: DifferenceType,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    return _call_service(
        service.standalone_order_difference,
        order_id,
        difference_type,
        local_value,
        external_value,
    )


def persist_standalone_order_difference(order_id: str, draft: DifferenceDraft) -> str:
    return _call_service(service.persist_standalone_order_difference, order_id, draft)


def run_account_reconciliation(
    request: VenueReconciliationRunRequest,
) -> VenueReconciliationRunResponse:
    return _call_service(service.run_account_reconciliation, request)


def validate_strategy_account(strategy_instance_id: str, account_id: str) -> None:
    return _call_service(
        service.validate_strategy_account,
        strategy_instance_id,
        account_id,
    )


def compare_position(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
    fact_id: str,
) -> list[str]:
    return _call_service(
        service.compare_position,
        run_id,
        request,
        external,
        fact_id,
    )


def compare_balance(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
) -> list[str]:
    return _call_service(service.compare_balance, run_id, request, external)


def persist_difference_draft(run_id: str, draft: DifferenceDraft) -> str:
    return _call_service(service.persist_difference_draft, run_id, draft)


def get_run(run_id: str) -> VenueReconciliationRunResponse:
    return _call_service(service.get_run, run_id)


def list_differences(run_id: str) -> list[ReconciliationDifferenceResponse]:
    return _call_service(service.list_differences, run_id)


def resolve_difference(
    difference_id: str,
    request: ResolveDifferenceRequest,
) -> ReconciliationDifferenceResponse:
    return _call_service(service.resolve_difference, difference_id, request)


router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/trading/orders/{order_id}/venue-reconcile",
    response_model=OrderVenueReconciliationResponse,
    tags=["venue-reconciliation"],
)
def reconcile_platform_order(order_id: str) -> OrderVenueReconciliationResponse:
    return reconcile_order_with_venue(order_id)


@router.post(
    "/ops/venue-reconciliation/runs",
    response_model=VenueReconciliationRunResponse,
    tags=["venue-reconciliation"],
)
def create_reconciliation_run(
    request: VenueReconciliationRunRequest,
) -> VenueReconciliationRunResponse:
    return run_account_reconciliation(request)


@router.get(
    "/ops/venue-reconciliation/runs/{run_id}",
    response_model=VenueReconciliationRunResponse,
    tags=["venue-reconciliation"],
)
def read_reconciliation_run(run_id: str) -> VenueReconciliationRunResponse:
    return get_run(run_id)


@router.get(
    "/ops/venue-reconciliation/runs/{run_id}/differences",
    response_model=list[ReconciliationDifferenceResponse],
    tags=["venue-reconciliation"],
)
def read_reconciliation_differences(run_id: str) -> list[ReconciliationDifferenceResponse]:
    return list_differences(run_id)


@router.post(
    "/ops/venue-reconciliation/differences/{difference_id}/resolve",
    response_model=ReconciliationDifferenceResponse,
    tags=["venue-reconciliation"],
)
def resolve_reconciliation_difference(
    difference_id: str,
    request: ResolveDifferenceRequest,
) -> ReconciliationDifferenceResponse:
    return resolve_difference(difference_id, request)
