from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app import eod_reconciliation as facade
from app.config import get_settings
from app.eod_reconciliation_schemas import (
    EodReconciliationReportRequest,
    EodReconciliationReportResponse,
    EodReconciliationReviewRequest,
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
    return facade.create_eod_report(request)


@router.get(
    "/ops/eod-reconciliation/reports/{report_id}",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def read_report(report_id: str) -> EodReconciliationReportResponse:
    return facade.get_eod_report(report_id)


@router.get(
    "/ops/eod-reconciliation/reports",
    response_model=list[EodReconciliationReportResponse],
    tags=["eod-reconciliation"],
)
def read_reports(
    strategy_instance_id: str | None = Query(default=None, alias="strategyInstanceId"),  # noqa: B008
    account_id: str | None = Query(default=None, alias="accountId"),  # noqa: B008
    business_date: date | None = Query(default=None, alias="businessDate"),  # noqa: B008
) -> list[EodReconciliationReportResponse]:
    return facade.list_eod_reports(strategy_instance_id, account_id, business_date)


@router.post(
    "/ops/eod-reconciliation/reports/{report_id}/review",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def review_report(
    report_id: str,
    request: EodReconciliationReviewRequest,
) -> EodReconciliationReportResponse:
    return facade.review_eod_report(report_id, request)
