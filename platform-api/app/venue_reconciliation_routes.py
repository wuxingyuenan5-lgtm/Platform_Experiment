from __future__ import annotations

from fastapi import APIRouter

from app import venue_reconciliation as facade
from app.config import get_settings
from app.venue_reconciliation_schemas import (
    OrderVenueReconciliationResponse,
    ReconciliationDifferenceResponse,
    ResolveDifferenceRequest,
    VenueReconciliationRunRequest,
    VenueReconciliationRunResponse,
)

router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/trading/orders/{order_id}/venue-reconcile",
    response_model=OrderVenueReconciliationResponse,
    tags=["venue-reconciliation"],
)
def reconcile_platform_order(order_id: str) -> OrderVenueReconciliationResponse:
    return facade.reconcile_order_with_venue(order_id)


@router.post(
    "/trading/orders/{order_id}/resolve-missing-external",
    response_model=OrderVenueReconciliationResponse,
    tags=["venue-reconciliation"],
)
def resolve_missing_external_platform_order(order_id: str) -> OrderVenueReconciliationResponse:
    return facade.resolve_owner_accepted_missing_external_order(order_id)


@router.post(
    "/ops/venue-reconciliation/runs",
    response_model=VenueReconciliationRunResponse,
    tags=["venue-reconciliation"],
)
def create_reconciliation_run(
    request: VenueReconciliationRunRequest,
) -> VenueReconciliationRunResponse:
    return facade.run_account_reconciliation(request)


@router.get(
    "/ops/venue-reconciliation/runs/{run_id}",
    response_model=VenueReconciliationRunResponse,
    tags=["venue-reconciliation"],
)
def read_reconciliation_run(run_id: str) -> VenueReconciliationRunResponse:
    return facade.get_run(run_id)


@router.get(
    "/ops/venue-reconciliation/runs/{run_id}/differences",
    response_model=list[ReconciliationDifferenceResponse],
    tags=["venue-reconciliation"],
)
def read_reconciliation_differences(run_id: str) -> list[ReconciliationDifferenceResponse]:
    return facade.list_differences(run_id)


@router.post(
    "/ops/venue-reconciliation/differences/{difference_id}/resolve",
    response_model=ReconciliationDifferenceResponse,
    tags=["venue-reconciliation"],
)
def resolve_reconciliation_difference(
    difference_id: str,
    request: ResolveDifferenceRequest,
) -> ReconciliationDifferenceResponse:
    return facade.resolve_difference(difference_id, request)
