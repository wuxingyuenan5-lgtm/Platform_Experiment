import pytest

from app.eod_reconciliation_policy import (
    EodReviewConflictError,
    EodReviewNotEligibleError,
    historical_difference_disposition,
    report_disposition,
    review_disposition,
)


def disposition(**overrides):
    values = {
        "errors": [],
        "account_reconciliation_run_id": "account-run",
        "economic_event_import_id": "economic-import",
        "nav_snapshot_id": "nav-snapshot",
        "order_reconciliation_count": 1,
        "open_difference_count": 0,
        "skipped_external_ids": [],
        "missing_account_ids": [],
        "formal_pnl_incomplete_count": 0,
    }
    values.update(overrides)
    return report_disposition(**values)


def test_clean_report_is_complete_and_eligible_for_review() -> None:
    result = disposition()
    assert result.status == "complete"
    assert result.scale_gate_status == "eligible_for_review"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("open_difference_count", 1),
        ("skipped_external_ids", ["external-1"]),
        ("missing_account_ids", ["account-2"]),
        ("formal_pnl_incomplete_count", 1),
    ],
)
def test_any_quality_gap_completes_with_differences(field: str, value: object) -> None:
    result = disposition(**{field: value})
    assert result.status == "completed_with_differences"
    assert result.scale_gate_status == "blocked"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("account_reconciliation_run_id", "account-run"),
        ("economic_event_import_id", "economic-import"),
        ("nav_snapshot_id", "nav-snapshot"),
        ("order_reconciliation_count", 1),
    ],
)
def test_errors_with_any_result_are_partial(field: str, value: object) -> None:
    result = disposition(
        errors=["failure"],
        account_reconciliation_run_id=None,
        economic_event_import_id=None,
        nav_snapshot_id=None,
        order_reconciliation_count=0,
        **{field: value},
    )
    assert result.status == "partial"
    assert result.scale_gate_status == "blocked"


def test_errors_without_any_result_fail_report() -> None:
    result = disposition(
        errors=["failure"],
        account_reconciliation_run_id=None,
        economic_event_import_id=None,
        nav_snapshot_id=None,
        order_reconciliation_count=0,
    )
    assert result.status == "failed"
    assert result.scale_gate_status == "blocked"


@pytest.mark.parametrize("difference_field", ["open_difference_count", "accepted_difference_count"])
def test_historical_open_or_accepted_difference_blocks_clean_report(
    difference_field: str,
) -> None:
    values = {
        "status": "complete",
        "open_difference_count": 0,
        "accepted_difference_count": 0,
    }
    values[difference_field] = 1
    result = historical_difference_disposition(**values)
    assert result.status == "completed_with_differences"
    assert result.scale_gate_status == "blocked"


def test_historical_resolved_only_keeps_clean_report_eligible() -> None:
    result = historical_difference_disposition(
        status="complete",
        open_difference_count=0,
        accepted_difference_count=0,
    )
    assert result.status == "complete"
    assert result.scale_gate_status == "eligible_for_review"


@pytest.mark.parametrize("status", ["completed_with_differences", "partial", "failed"])
def test_historical_gate_preserves_nonclean_status(status: str) -> None:
    result = historical_difference_disposition(
        status=status,
        open_difference_count=1,
        accepted_difference_count=1,
    )
    assert result.status == status
    assert result.scale_gate_status == "blocked"


@pytest.mark.parametrize("decision", ["approved_same_limits", "needs_remediation", "rejected"])
def test_new_review_uses_decision_as_scale_gate(decision: str) -> None:
    result = review_disposition(
        existing_payload_hash=None,
        requested_payload_hash="review-hash",
        decision=decision,
        current_scale_gate_status="eligible_for_review",
    )
    assert result.changed is True
    assert result.scale_gate_status == decision


def test_matching_review_replay_is_unchanged() -> None:
    result = review_disposition(
        existing_payload_hash="review-hash",
        requested_payload_hash="review-hash",
        decision="needs_remediation",
        current_scale_gate_status="needs_remediation",
    )
    assert result.changed is False
    assert result.scale_gate_status == "needs_remediation"


def test_different_review_payload_conflicts() -> None:
    with pytest.raises(EodReviewConflictError):
        review_disposition(
            existing_payload_hash="first-hash",
            requested_payload_hash="different-hash",
            decision="rejected",
            current_scale_gate_status="needs_remediation",
        )


def test_approval_requires_clean_eligible_report() -> None:
    with pytest.raises(EodReviewNotEligibleError):
        review_disposition(
            existing_payload_hash=None,
            requested_payload_hash="approval-hash",
            decision="approved_same_limits",
            current_scale_gate_status="blocked",
        )
