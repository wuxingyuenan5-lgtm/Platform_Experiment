from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app import eod_reconciliation_repository as repository
from app.config import get_settings
from app.eod_policy import apply_outstanding_difference_gate, list_strategy_orders_for_eod
from app.eod_reconciliation_policy import report_disposition
from app.eod_reconciliation_schemas import (
    EodReconciliationReportRequest,
    EodReconciliationReportResponse,
    EodReconciliationReviewRequest,
    ReportStatus,
    ReviewDecision,
    ScaleGateStatus,
)
from app.financial_facts import rebuild_strategy_financials, run_formal_nav_snapshot
from app.live_venue_accounting import (
    LiveEconomicEventImportRequest,
    import_live_economic_events,
)
from app.venue_reconciliation import (
    VenueReconciliationRunRequest,
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


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def natural_key(request: EodReconciliationReportRequest) -> str:
    return ":".join(
        [
            request.business_date.isoformat(),
            request.strategy_instance_id,
            request.account_id,
        ]
    )


def create_eod_report(
    request: EodReconciliationReportRequest,
) -> EodReconciliationReportResponse:
    ensure_schema()
    validate_strategy_account(request.strategy_instance_id, request.account_id)
    payload = request.model_dump(by_alias=True, mode="json")
    payload_hash = canonical_hash(payload)
    report_natural_key = natural_key(request)

    existing = repository.load_report_by_identity(request.idempotency_key, report_natural_key)
    if existing is not None:
        if existing["payload_hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="EOD report identity was reused with a different payload",
            )
        return report_from_row(existing)

    report_id = str(uuid4())
    created_at = now_iso()
    repository.insert_initial_report(
        report_id=report_id,
        idempotency_key=request.idempotency_key,
        natural_key=report_natural_key,
        payload_hash=payload_hash,
        business_date=request.business_date.isoformat(),
        timezone=request.timezone,
        valuation_time=request.valuation_time.astimezone(UTC).isoformat(),
        strategy_instance_id=request.strategy_instance_id,
        account_id=request.account_id,
        actor=request.actor,
        owner=request.owner,
        due_at=request.due_at.astimezone(UTC).isoformat(),
        created_at=created_at,
    )

    order_count = 0
    account_run_id: str | None = None
    economic_import_id: str | None = None
    nav_snapshot_id: str | None = None
    skipped_external_ids: list[str] = []
    missing_account_ids: list[str] = []
    errors: list[str] = []
    difference_ids: set[str] = set()

    for order_id in list_strategy_orders(
        request.strategy_instance_id,
        request.account_id,
        request.valuation_time,
    ):
        try:
            result = reconcile_order_with_venue(order_id)
            order_count += 1
            difference_ids.update(result.difference_ids)
        except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
            errors.append(f"order:{order_id}:{type(exc).__name__}:{exc}")

    try:
        account_run = run_account_reconciliation(
            VenueReconciliationRunRequest(
                idempotencyKey=f"{request.idempotency_key}:account",
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                actor=request.actor,
            )
        )
        account_run_id = account_run.run_id
        difference_ids.update(repository.list_difference_ids_for_run(account_run_id))
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"account-reconciliation:{type(exc).__name__}:{exc}")

    try:
        economic_import = import_live_economic_events(
            LiveEconomicEventImportRequest(
                idempotencyKey=f"{request.idempotency_key}:economic-events",
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                actor=request.actor,
            )
        )
        economic_import_id = economic_import.import_id
        skipped_external_ids = list(economic_import.skipped_external_ids)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"economic-events:{type(exc).__name__}:{exc}")

    try:
        rebuild_strategy_financials(request.strategy_instance_id)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"formal-rebuild:{type(exc).__name__}:{exc}")

    try:
        nav = run_formal_nav_snapshot(
            request.strategy_instance_id,
            request.valuation_time,
        )
        nav_snapshot_id = nav.snapshot_id
        missing_account_ids = list(nav.missing_account_ids)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"formal-nav:{type(exc).__name__}:{exc}")

    formal_pnl_count, formal_pnl_incomplete_count = formal_pnl_counts(
        request.strategy_instance_id,
        request.account_id,
    )
    open_count, resolved_count, accepted_count = difference_status_counts(difference_ids)

    disposition = report_disposition(
        errors=errors,
        account_reconciliation_run_id=account_run_id,
        economic_event_import_id=economic_import_id,
        nav_snapshot_id=nav_snapshot_id,
        order_reconciliation_count=order_count,
        open_difference_count=open_count,
        skipped_external_ids=skipped_external_ids,
        missing_account_ids=missing_account_ids,
        formal_pnl_incomplete_count=formal_pnl_incomplete_count,
    )
    status = disposition.status
    scale_gate_status = disposition.scale_gate_status
    completed_at = now_iso()
    repository.complete_report(
        report_id=report_id,
        status=status,
        scale_gate_status=scale_gate_status,
        order_reconciliation_count=order_count,
        account_reconciliation_run_id=account_run_id,
        economic_event_import_id=economic_import_id,
        nav_snapshot_id=nav_snapshot_id,
        formal_pnl_count=formal_pnl_count,
        formal_pnl_incomplete_count=formal_pnl_incomplete_count,
        open_difference_count=open_count,
        resolved_difference_count=resolved_count,
        accepted_difference_count=accepted_count,
        skipped_external_ids=skipped_external_ids,
        missing_account_ids=missing_account_ids,
        errors=errors,
        completed_at=completed_at,
    )

    audit(
        "eod_reconciliation_completed",
        "eod_reconciliation_report",
        report_id,
        {
            "businessDate": request.business_date.isoformat(),
            "timezone": request.timezone,
            "valuationTime": request.valuation_time,
            "strategyInstanceId": request.strategy_instance_id,
            "accountId": request.account_id,
            "status": status,
            "scaleGateStatus": scale_gate_status,
            "orderReconciliationCount": order_count,
            "openDifferenceCount": open_count,
            "skippedExternalIds": skipped_external_ids,
            "missingAccountIds": missing_account_ids,
            "errors": errors,
            "actor": request.actor,
            "owner": request.owner,
        },
    )
    apply_outstanding_difference_gate(
        report_id,
        request.strategy_instance_id,
        request.account_id,
    )
    return get_eod_report(report_id)


def get_eod_report(report_id: str) -> EodReconciliationReportResponse:
    ensure_schema()
    row = repository.load_report(report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="EOD reconciliation report not found")
    return report_from_row(row)


def list_eod_reports(
    strategy_instance_id: str | None = None,
    account_id: str | None = None,
    business_date: date | None = None,
) -> list[EodReconciliationReportResponse]:
    ensure_schema()
    return [
        report_from_row(row)
        for row in repository.list_report_rows(
            strategy_instance_id=strategy_instance_id,
            account_id=account_id,
            business_date=business_date,
        )
    ]


def review_eod_report(
    report_id: str,
    request: EodReconciliationReviewRequest,
) -> EodReconciliationReportResponse:
    ensure_schema()
    payload_hash = canonical_hash(request.model_dump(mode="json"))
    try:
        result = repository.review_report(
            report_id=report_id,
            payload_hash=payload_hash,
            decision=request.decision,
            reviewer=request.reviewer,
            reason=request.reason,
            reviewed_at=now_iso(),
        )
    except repository.EodReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail="EOD reconciliation report not found") from exc
    except repository.EodReviewConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="EOD report review is immutable and already has a different decision",
        ) from exc
    except repository.EodReviewNotEligibleError as exc:
        raise HTTPException(
            status_code=422,
            detail="Only a clean EOD report can be approved for the existing live limits",
        ) from exc

    if result.changed:
        audit(
            "eod_reconciliation_reviewed",
            "eod_reconciliation_report",
            report_id,
            {
                "decision": request.decision,
                "reviewer": request.reviewer,
                "reason": request.reason,
            },
        )
    return report_from_row(result.row)


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
