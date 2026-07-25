from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from app import eod_reconciliation_policy as policy
from app import eod_reconciliation_repository as repository
from app.eod_reconciliation_schemas import (
    EodReconciliationReportRequest,
    EodReconciliationReportResponse,
    EodReconciliationReviewRequest,
)
from app.live_venue_accounting import LiveEconomicEventImportRequest
from app.venue_reconciliation_schemas import VenueReconciliationRunRequest

EodReviewConflictError = policy.EodReviewConflictError
EodReviewNotEligibleError = policy.EodReviewNotEligibleError


class EodReportIdentityConflictError(RuntimeError):
    pass


class EodReportNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class EodServiceDependencies:
    validate_strategy_account: Callable[[str, str], None]
    list_strategy_orders: Callable[[str, str, datetime], list[str]]
    reconcile_order_with_venue: Callable[[str], Any]
    run_account_reconciliation: Callable[[VenueReconciliationRunRequest], Any]
    import_live_economic_events: Callable[[LiveEconomicEventImportRequest], Any]
    rebuild_strategy_financials: Callable[[str], Any]
    run_formal_nav_snapshot: Callable[[str, datetime], Any]
    audit: Callable[[str, str, str, dict[str, object]], None]
    apply_outstanding_difference_gate: Callable[[str, str, str], None]


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
    dependencies: EodServiceDependencies,
) -> EodReconciliationReportResponse:
    repository.ensure_schema()
    dependencies.validate_strategy_account(
        request.strategy_instance_id,
        request.account_id,
    )
    payload = request.model_dump(by_alias=True, mode="json")
    payload_hash = canonical_hash(payload)
    report_natural_key = natural_key(request)

    existing = repository.load_report_by_identity(request.idempotency_key, report_natural_key)
    if existing is not None:
        if existing["payload_hash"] != payload_hash:
            raise EodReportIdentityConflictError(
                "EOD report identity was reused with a different payload"
            )
        return repository.report_from_row(existing)

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

    for order_id in dependencies.list_strategy_orders(
        request.strategy_instance_id,
        request.account_id,
        request.valuation_time,
    ):
        try:
            result = dependencies.reconcile_order_with_venue(order_id)
            order_count += 1
            difference_ids.update(result.difference_ids)
        except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
            errors.append(f"order:{order_id}:{type(exc).__name__}:{exc}")

    try:
        account_run = dependencies.run_account_reconciliation(
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
        economic_import = dependencies.import_live_economic_events(
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
        dependencies.rebuild_strategy_financials(request.strategy_instance_id)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"formal-rebuild:{type(exc).__name__}:{exc}")

    try:
        nav = dependencies.run_formal_nav_snapshot(
            request.strategy_instance_id,
            request.valuation_time,
        )
        nav_snapshot_id = nav.snapshot_id
        missing_account_ids = list(nav.missing_account_ids)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"formal-nav:{type(exc).__name__}:{exc}")

    formal_pnl_count, formal_pnl_incomplete_count = repository.formal_pnl_counts(
        request.strategy_instance_id,
        request.account_id,
    )
    open_count, resolved_count, accepted_count = repository.difference_status_counts(
        difference_ids
    )

    disposition = policy.report_disposition(
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
    completed_at = now_iso()
    repository.complete_report(
        report_id=report_id,
        status=disposition.status,
        scale_gate_status=disposition.scale_gate_status,
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

    dependencies.audit(
        "eod_reconciliation_completed",
        "eod_reconciliation_report",
        report_id,
        {
            "businessDate": request.business_date.isoformat(),
            "timezone": request.timezone,
            "valuationTime": request.valuation_time,
            "strategyInstanceId": request.strategy_instance_id,
            "accountId": request.account_id,
            "status": disposition.status,
            "scaleGateStatus": disposition.scale_gate_status,
            "orderReconciliationCount": order_count,
            "openDifferenceCount": open_count,
            "skippedExternalIds": skipped_external_ids,
            "missingAccountIds": missing_account_ids,
            "errors": errors,
            "actor": request.actor,
            "owner": request.owner,
        },
    )
    dependencies.apply_outstanding_difference_gate(
        report_id,
        request.strategy_instance_id,
        request.account_id,
    )
    return get_eod_report(report_id)


def get_eod_report(report_id: str) -> EodReconciliationReportResponse:
    repository.ensure_schema()
    row = repository.load_report(report_id)
    if row is None:
        raise EodReportNotFoundError("EOD reconciliation report not found")
    return repository.report_from_row(row)


def list_eod_reports(
    strategy_instance_id: str | None = None,
    account_id: str | None = None,
    business_date: date | None = None,
) -> list[EodReconciliationReportResponse]:
    repository.ensure_schema()
    return [
        repository.report_from_row(row)
        for row in repository.list_report_rows(
            strategy_instance_id=strategy_instance_id,
            account_id=account_id,
            business_date=business_date,
        )
    ]


def review_eod_report(
    report_id: str,
    request: EodReconciliationReviewRequest,
    dependencies: EodServiceDependencies,
) -> EodReconciliationReportResponse:
    repository.ensure_schema()
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
        raise EodReportNotFoundError("EOD reconciliation report not found") from exc

    if result.changed:
        dependencies.audit(
            "eod_reconciliation_reviewed",
            "eod_reconciliation_report",
            report_id,
            {
                "decision": request.decision,
                "reviewer": request.reviewer,
                "reason": request.reason,
            },
        )
    return repository.report_from_row(result.row)
