from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.strategies.domain import (
    ExecutionPlan,
    ExecutionPlanLeg,
    ExecutionPolicy,
    ReleaseCondition,
    StrategyInstructionAction,
)


def build_cross_spread_plan(
    *, action: str, parameters: dict[str, object], created_at: datetime
) -> ExecutionPlan:
    quantity_oz = Decimal(str(parameters["quantityOz"]))
    multiplier = Decimal(str(parameters["mt5ContractMultiplier"]))
    if quantity_oz <= 0 or multiplier <= 0:
        raise ValueError("quantityOz and mt5ContractMultiplier must be positive")
    mt5_quantity = quantity_oz / multiplier
    bybit_side, mt5_side = (
        ("buy", "sell") if parameters["action"] == "OPEN_LONG" else ("sell", "buy")
    )
    return ExecutionPlan(
        adapter_version="cross_spread.v1",
        strategy_key="cross_venue_spread",
        action=StrategyInstructionAction(action),
        created_at=created_at,
        account_capability_snapshot={
            str(parameters["bybitAccountId"]): "trade_and_read",
            str(parameters["mt5AccountId"]): "trade_and_read",
        },
        legs=(
            ExecutionPlanLeg(
                role="bybit_leg",
                account_id=str(parameters["bybitAccountId"]),
                instrument_id=str(parameters.get("bybitInstrumentId", "instrument_xautusdt")),
                external_symbol=str(parameters.get("bybitSymbol", "XAUTUSDT")),
                side=bybit_side,
                maximum_quantity=quantity_oz,
                sequence=1,
                execution_policy=ExecutionPolicy.MARKET,
                quantity_step=Decimal(str(parameters["bybitQuantityStep"])),
                price_tick=Decimal(str(parameters.get("bybitPriceTick", "0.01"))),
                contract_multiplier=Decimal(str(parameters.get("bybitContractMultiplier", "1"))),
                minimum_quantity=Decimal(str(parameters["bybitQuantityStep"])),
            ),
            ExecutionPlanLeg(
                role="mt5_leg",
                account_id=str(parameters["mt5AccountId"]),
                instrument_id=str(parameters.get("mt5InstrumentId", "instrument_xauusd_s")),
                external_symbol=str(parameters.get("mt5Symbol", "XAUUSD.s")),
                side=mt5_side,
                maximum_quantity=mt5_quantity,
                sequence=2,
                execution_policy=ExecutionPolicy.MARKET,
                depends_on="bybit_leg",
                release_condition=ReleaseCondition.TERMINAL_FULL_FILL,
                release_ratio=Decimal("1") / multiplier,
                release_cap=mt5_quantity,
                quantity_step=Decimal(str(parameters["mt5QuantityStep"])),
                price_tick=Decimal(str(parameters.get("mt5PriceTick", "0.01"))),
                contract_multiplier=multiplier,
                minimum_quantity=Decimal(str(parameters["mt5QuantityStep"])),
            ),
        ),
    )
