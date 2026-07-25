from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from app.eod_reconciliation_schemas import ReportStatus, ReviewDecision, ScaleGateStatus


class EodReviewConflictError(RuntimeError):
    pass


class EodReviewNotEligibleError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportDisposition:
    status: ReportStatus
    scale_gate_status: ScaleGateStatus


@dataclass(frozen=True)
class ReviewDisposition:
    changed: bool
    scale_gate_status: ScaleGateStatus


def report_disposition(
    *,
    errors: Collection[str],
    account_reconciliation_run_id: str | None,
    economic_event_import_id: str | None,
    nav_snapshot_id: str | None,
    order_reconciliation_count: int,
    open_difference_count: int,
    skipped_external_ids: Collection[str],
    missing_account_ids: Collection[str],
    formal_pnl_incomplete_count: int,
) -> ReportDisposition:
    has_any_result = any(
        [
            account_reconciliation_run_id,
            economic_event_import_id,
            nav_snapshot_id,
            order_reconciliation_count,
        ]
    )
    if errors and not has_any_result:
        status: ReportStatus = "failed"
    elif errors:
        status = "partial"
    elif (
        open_difference_count
        or skipped_external_ids
        or missing_account_ids
        or formal_pnl_incomplete_count
    ):
        status = "completed_with_differences"
    else:
        status = "complete"
    return ReportDisposition(
        status=status,
        scale_gate_status="eligible_for_review" if status == "complete" else "blocked",
    )


def historical_difference_disposition(
    *,
    status: ReportStatus,
    open_difference_count: int,
    accepted_difference_count: int,
) -> ReportDisposition:
    scale_gate_status: ScaleGateStatus = (
        "eligible_for_review" if status == "complete" else "blocked"
    )
    if open_difference_count or accepted_difference_count:
        if status == "complete":
            status = "completed_with_differences"
        scale_gate_status = "blocked"
    return ReportDisposition(status=status, scale_gate_status=scale_gate_status)


def review_disposition(
    *,
    existing_payload_hash: str | None,
    requested_payload_hash: str,
    decision: ReviewDecision,
    current_scale_gate_status: ScaleGateStatus,
) -> ReviewDisposition:
    if existing_payload_hash is not None:
        if existing_payload_hash != requested_payload_hash:
            raise EodReviewConflictError(
                "EOD report review is immutable and already has a different decision"
            )
        return ReviewDisposition(changed=False, scale_gate_status=current_scale_gate_status)
    if decision == "approved_same_limits" and current_scale_gate_status != "eligible_for_review":
        raise EodReviewNotEligibleError(
            "Only a clean EOD report can be approved for the existing live limits"
        )
    scale_gate_status: ScaleGateStatus = decision
    return ReviewDisposition(changed=True, scale_gate_status=scale_gate_status)
