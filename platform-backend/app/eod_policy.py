from __future__ import annotations

from datetime import UTC, datetime

from app.database import connection

TERMINAL_ORDER_STATUSES = ("filled", "rejected", "canceled")


def list_strategy_orders_for_eod(
    strategy_instance_id: str,
    account_id: str,
    valuation_time: datetime,
) -> list[str]:
    """Select the business-day orders plus older orders that still need finality."""
    local_start = valuation_time.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = local_start.astimezone(UTC).isoformat()
    end_utc = valuation_time.astimezone(UTC).isoformat()
    placeholders = ",".join("?" for _ in TERMINAL_ORDER_STATUSES)
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT o.id
            FROM orders o
            JOIN trade_commands tc ON tc.id = o.command_id
            WHERE tc.strategy_instance_id = ?
              AND o.account_id = ?
              AND o.created_at <= ?
              AND (
                    o.created_at >= ?
                    OR o.status NOT IN ({placeholders})
              )
            ORDER BY o.created_at, o.id
            """,
            (
                strategy_instance_id,
                account_id,
                end_utc,
                start_utc,
                *TERMINAL_ORDER_STATUSES,
            ),
        ).fetchall()
    return [row["id"] for row in rows]


def apply_outstanding_difference_gate(
    report_id: str,
    strategy_instance_id: str,
    account_id: str,
) -> None:
    """Block live scaling when any historical open or accepted difference remains."""
    with connection() as db:
        rows = db.execute(
            """
            SELECT rd.status, COUNT(*) AS count
            FROM reconciliation_differences rd
            JOIN venue_reconciliation_runs vr ON vr.id = rd.run_id
            WHERE vr.strategy_instance_id = ?
              AND vr.account_id = ?
            GROUP BY rd.status
            """,
            (strategy_instance_id, account_id),
        ).fetchall()
        counts = {row["status"]: int(row["count"]) for row in rows}
        open_count = counts.get("open", 0)
        resolved_count = counts.get("resolved", 0)
        accepted_count = counts.get("accepted", 0)
        report = db.execute(
            "SELECT status FROM eod_reconciliation_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        if report is None:
            raise LookupError("EOD report not found while applying scale gate")

        status = report["status"]
        scale_gate_status = "eligible_for_review" if status == "complete" else "blocked"
        if open_count or accepted_count:
            if status == "complete":
                status = "completed_with_differences"
            scale_gate_status = "blocked"

        db.execute(
            """
            UPDATE eod_reconciliation_reports
            SET status = ?, scale_gate_status = ?, open_difference_count = ?,
                resolved_difference_count = ?, accepted_difference_count = ?
            WHERE id = ?
            """,
            (
                status,
                scale_gate_status,
                open_count,
                resolved_count,
                accepted_count,
                report_id,
            ),
        )
