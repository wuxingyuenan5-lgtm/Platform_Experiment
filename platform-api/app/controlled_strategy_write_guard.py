from __future__ import annotations

from fastapi import HTTPException

from app.database import connection

CONTROLLED_STRATEGY_KEYS = ("cross_venue_spread", "funding_arbitrage")


def is_controlled_strategy_instance(strategy_instance_id: str | None) -> bool:
    if not strategy_instance_id:
        return False
    with connection() as db:
        row = db.execute(
            "SELECT sd.strategy_key FROM strategy_instances si "
            "JOIN strategy_definitions sd ON sd.id=si.strategy_definition_id WHERE si.id=?",
            (strategy_instance_id,),
        ).fetchone()
    return row is not None and row["strategy_key"] in CONTROLLED_STRATEGY_KEYS


def reject_controlled_strategy_write_bypass(
    strategy_instance_id: str | None,
    *,
    strategy_key: str | None = None,
) -> None:
    if is_controlled_strategy_instance(strategy_instance_id) or (
        not strategy_instance_id and strategy_key in CONTROLLED_STRATEGY_KEYS
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Controlled Cross/Funding strategies must use their dedicated "
                "instruction and lifecycle endpoints"
            ),
        )


def reject_controlled_account_legacy_order(account_id: str) -> None:
    """The raw order endpoint has no strategy identity, so reject controlled accounts."""

    placeholders = ", ".join("?" for _ in CONTROLLED_STRATEGY_KEYS)
    with connection() as db:
        row = db.execute(
            f"""
            SELECT 1
            FROM strategy_account_bindings sab
            JOIN strategy_instances si ON si.id=sab.strategy_instance_id
            JOIN strategy_definitions sd ON sd.id=si.strategy_definition_id
            WHERE sab.account_id = ?
              AND sab.status = 'active'
              AND sab.capability = 'trade_and_read'
              AND sd.strategy_key IN ({placeholders})
            LIMIT 1
            """,
            (account_id, *CONTROLLED_STRATEGY_KEYS),
        ).fetchone()
    if row is not None:
        raise HTTPException(
            status_code=403,
            detail=(
                "Controlled Cross/Funding accounts cannot use the deprecated raw order endpoint"
            ),
        )
