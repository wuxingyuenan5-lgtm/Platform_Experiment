from __future__ import annotations

from datetime import UTC, datetime

from app import eod_reconciliation_repository as repository

TERMINAL_ORDER_STATUSES = ("filled", "rejected", "canceled")


def list_strategy_orders_for_eod(
    strategy_instance_id: str,
    account_id: str,
    valuation_time: datetime,
) -> list[str]:
    """Select the business-day orders plus older orders that still need finality."""
    local_start = valuation_time.replace(hour=0, minute=0, second=0, microsecond=0)
    return repository.list_strategy_order_ids(
        strategy_instance_id=strategy_instance_id,
        account_id=account_id,
        start_utc=local_start.astimezone(UTC).isoformat(),
        end_utc=valuation_time.astimezone(UTC).isoformat(),
        terminal_statuses=TERMINAL_ORDER_STATUSES,
    )


def apply_outstanding_difference_gate(
    report_id: str,
    strategy_instance_id: str,
    account_id: str,
) -> None:
    """Block live scaling when any historical open or accepted difference remains."""
    counts = repository.historical_difference_counts(strategy_instance_id, account_id)
    open_count = counts.get("open", 0)
    resolved_count = counts.get("resolved", 0)
    accepted_count = counts.get("accepted", 0)
    status = repository.load_report_status(report_id)
    if status is None:
        raise LookupError("EOD report not found while applying scale gate")

    scale_gate_status = "eligible_for_review" if status == "complete" else "blocked"
    if open_count or accepted_count:
        if status == "complete":
            status = "completed_with_differences"
        scale_gate_status = "blocked"

    repository.update_report_gate(
        report_id=report_id,
        status=status,
        scale_gate_status=scale_gate_status,
        open_difference_count=open_count,
        resolved_difference_count=resolved_count,
        accepted_difference_count=accepted_count,
    )
