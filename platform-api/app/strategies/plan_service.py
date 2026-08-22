from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException

from app.database import connection
from app.strategies.adapters.cross_spread import build_cross_spread_plan
from app.strategies.adapters.funding_carry import build_funding_carry_plan
from app.strategies.domain import ExecutionPlan, StrategyInstructionAction


def build_plan(
    strategy_instance_id: str,
    action: StrategyInstructionAction,
    parameters: dict[str, object],
) -> ExecutionPlan:
    with connection() as db:
        instance = db.execute(
            """
            SELECT sd.strategy_key FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ? AND si.status = 'active'
            """,
            (strategy_instance_id,),
        ).fetchone()
        bindings = db.execute(
            """
            SELECT account_id, role, capability FROM strategy_account_bindings
            WHERE strategy_instance_id = ? AND status = 'active'
            """,
            (strategy_instance_id,),
        ).fetchall()
    if instance is None:
        raise HTTPException(status_code=422, detail="Strategy instance is not runnable")
    if not bindings or any(row["capability"] != "trade_and_read" for row in bindings):
        raise HTTPException(
            status_code=422, detail="Strategy account binding is read_only or unavailable"
        )
    now = datetime.now(UTC)
    key = instance["strategy_key"]
    if key == "funding_arbitrage":
        primary = next((row for row in bindings if row["role"] == "primary"), bindings[0])
        return build_funding_carry_plan(
            action=action.value,
            parameters={
                **parameters,
                "accountId": primary["account_id"],
                "perpetualInstrumentId": "instrument_btc_usdt_perp",
                "spotInstrumentId": "instrument_btc_usdt",
            },
            created_at=now,
        )
    if key == "cross_venue_spread":
        roles = {row["role"]: row["account_id"] for row in bindings}
        return build_cross_spread_plan(
            action=action.value,
            parameters={
                **parameters,
                "bybitAccountId": roles.get("venue_a", roles.get("primary")),
                "mt5AccountId": roles.get("mt5_leg"),
                "mt5ContractMultiplier": "100",
                "bybitQuantityStep": "0.001",
                "mt5QuantityStep": "0.01",
            },
            created_at=now,
        )
    raise HTTPException(status_code=422, detail="Strategy has no registered instruction adapter")
