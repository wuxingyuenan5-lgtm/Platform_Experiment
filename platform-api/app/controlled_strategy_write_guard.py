from __future__ import annotations

from fastapi import HTTPException

from app.auth import CEO_TRADE_STRATEGY_INSTANCE_IDS
from app.database import connection


def reject_controlled_strategy_write_bypass(
    strategy_instance_id: str | None,
) -> None:
    if strategy_instance_id in CEO_TRADE_STRATEGY_INSTANCE_IDS:
        raise HTTPException(
            status_code=403,
            detail=(
                "Controlled Cross/Funding strategies must use their dedicated "
                "instruction and lifecycle endpoints"
            ),
        )


def reject_controlled_account_legacy_order(account_id: str) -> None:
    """The raw order endpoint has no strategy identity, so reject controlled accounts."""

    placeholders = ", ".join("?" for _ in CEO_TRADE_STRATEGY_INSTANCE_IDS)
    with connection() as db:
        row = db.execute(
            f"""
            SELECT 1
            FROM strategy_account_bindings
            WHERE account_id = ?
              AND status = 'active'
              AND capability = 'trade_and_read'
              AND strategy_instance_id IN ({placeholders})
            LIMIT 1
            """,
            (account_id, *sorted(CEO_TRADE_STRATEGY_INSTANCE_IDS)),
        ).fetchone()
    if row is not None:
        raise HTTPException(
            status_code=403,
            detail=(
                "Controlled Cross/Funding accounts cannot use the deprecated raw order endpoint"
            ),
        )
