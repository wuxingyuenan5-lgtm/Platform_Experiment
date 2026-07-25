from __future__ import annotations

from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app import eod_reconciliation_repository as repository
from app import eod_reconciliation_service as service
from app.config import get_settings
from app.eod_policy import apply_outstanding_difference_gate, list_strategy_orders_for_eod
from app.eod_reconciliation_schemas import (
    EodReconciliationReportRequest,
    EodReconciliationReportResponse,
    EodReconciliationReviewRequest,
    ReportStatus,
    ReviewDecision,
    ScaleGateStatus,
)
from app.financial_facts import rebuild_strategy_financials, run_formal_nav_snapshot
from app.live_venue_accounting import import_live_economic_events
from app.venue_reconciliation import (
    audit,
    reconcile_order_with_venue,
    run_account_reconciliation,
    validate_strategy_account,
)

# Stable compatibility ports backed by the authoritative owners.
list_strategy_orders = list_strategy_orders_for_eod
SCHEMA_SQL = repository.SCHEMA_SQL
ensure_schema = repository.ensure_schema
formal_pnl_counts = repository.formal_pnl_counts
difference_status_counts = repository.difference_status_counts
sla_status = repository.sla_status
report_from_row = repository.report_from_row
now_iso = service.now_iso
canonical_hash = service.canonical_hash
natural_key = service.natural_key


def _service_dependencies() -> service.EodServiceDependencies:
    return service.EodServiceDependencies(
        validate_strategy_account=validate_strategy_account,
        list_strategy_orders=list_strategy_orders,
        reconcile_order_with_venue=reconcile_order_with_venue,
        run_account_reconciliation=run_account_reconciliation,
        import_live_economic_events=import_live_economic_events,
        rebuild_strategy_financials=rebuild_strategy_financials,
        run_formal_nav_snapshot=run_formal_nav_snapshot,
        audit=audit,
        apply_outstanding_difference_gate=apply_outstanding_difference_gate,
    )


def _call_service[**P, R](
    operation: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    try:
        return operation(*args, **kwargs)
    except service.EodReportIdentityConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="EOD report identity was reused with a different payload",
        ) from exc
    except service.EodReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail="EOD reconciliation report not found") from exc
    except service.EodReviewConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="EOD report review is immutable and already has a different decision",
        ) from exc
    except service.EodReviewNotEligibleError as exc:
        raise HTTPException(
            status_code=422,
            detail="Only a clean EOD report can be approved for the existing live limits",
        ) from exc


def create_eod_report(
    request: EodReconciliationReportRequest,
) -> EodReconciliationReportResponse:
    return _call_service(service.create_eod_report, request, _service_dependencies())


def get_eod_report(report_id: str) -> EodReconciliationReportResponse:
    return _call_service(service.get_eod_report, report_id)


def list_eod_reports(
    strategy_instance_id: str | None = None,
    account_id: str | None = None,
    business_date: date | None = None,
) -> list[EodReconciliationReportResponse]:
    return _call_service(
        service.list_eod_reports,
        strategy_instance_id,
        account_id,
        business_date,
    )


def review_eod_report(
    report_id: str,
    request: EodReconciliationReviewRequest,
) -> EodReconciliationReportResponse:
    return _call_service(
        service.review_eod_report,
        report_id,
        request,
        _service_dependencies(),
    )


router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/ops/eod-reconciliation/reports",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def create_report(
    request: EodReconciliationReportRequest,
) -> EodReconciliationReportResponse:
    return create_eod_report(request)


@router.get(
    "/ops/eod-reconciliation/reports/{report_id}",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def read_report(report_id: str) -> EodReconciliationReportResponse:
    return get_eod_report(report_id)


@router.get(
    "/ops/eod-reconciliation/reports",
    response_model=list[EodReconciliationReportResponse],
    tags=["eod-reconciliation"],
)
def read_reports(
    strategy_instance_id: str | None = Query(default=None, alias="strategyInstanceId"),
    account_id: str | None = Query(default=None, alias="accountId"),
    business_date: date | None = Query(default=None, alias="businessDate"),
) -> list[EodReconciliationReportResponse]:
    return list_eod_reports(strategy_instance_id, account_id, business_date)


@router.post(
    "/ops/eod-reconciliation/reports/{report_id}/review",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def review_report(
    report_id: str,
    request: EodReconciliationReviewRequest,
) -> EodReconciliationReportResponse:
    return review_eod_report(report_id, request)
