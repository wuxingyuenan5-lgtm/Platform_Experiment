from __future__ import annotations

from datetime import datetime
from decimal import Decimal, localcontext

from app.strategies.domain import (
    ExecutionPlan,
    ExecutionPlanLeg,
    ExecutionPolicy,
    ReleaseCondition,
    SimulationCompatibilityPolicy,
    StrategyInstructionAction,
)


def build_funding_carry_plan(
    *, action: str, parameters: dict[str, object], created_at: datetime
) -> ExecutionPlan:
    compatibility_policy = parameters.get("simulationCompatibilityPolicy")
    if compatibility_policy not in (None, SimulationCompatibilityPolicy.FAKE_GATEWAY_MARKET):
        raise ValueError("Unsupported funding simulation compatibility policy")
    expected_policy = "market" if compatibility_policy else "post_only_chase"
    if parameters.get("executionPolicy") not in (None, expected_policy):
        raise ValueError(f"Funding perpetual execution policy must be {expected_policy}")
    perpetual_quantity = Decimal(str(parameters["perpetualQuantity"]))
    spot_quantity = Decimal(str(parameters["spotQuantity"]))
    if perpetual_quantity <= 0 or spot_quantity <= 0:
        raise ValueError("Funding quantities must be positive")
    perpetual_side, spot_side = ("sell", "buy") if action == "open" else ("buy", "sell")
    with localcontext() as context:
        context.prec = 28
        release_ratio = spot_quantity / perpetual_quantity
    account_id = str(parameters["accountId"])
    perp_step = Decimal(str(parameters.get("perpetualQuantityStep", "0.000001")))
    spot_step = Decimal(str(parameters.get("spotQuantityStep", "0.000001")))
    return ExecutionPlan(
        adapter_version="funding_carry.v1",
        strategy_key="funding_arbitrage",
        action=StrategyInstructionAction(action),
        created_at=created_at,
        simulation_compatibility_policy=compatibility_policy,
        account_capability_snapshot={account_id: "trade_and_read"},
        legs=(
            ExecutionPlanLeg(
                role="perpetual_leg",
                account_id=account_id,
                instrument_id=str(
                    parameters.get(
                        "perpetualInstrumentId",
                        f"instrument_{str(parameters['perpetualSymbol']).lower()}",
                    )
                ),
                external_symbol=str(parameters["perpetualSymbol"]).upper(),
                side=perpetual_side,
                maximum_quantity=perpetual_quantity,
                sequence=1,
                execution_policy=(
                    ExecutionPolicy.MARKET
                    if compatibility_policy
                    else ExecutionPolicy.POST_ONLY_CHASE
                ),
                quantity_step=perp_step,
                contract_multiplier=Decimal(
                    str(parameters.get("perpetualContractMultiplier", "1"))
                ),
                minimum_quantity=perp_step,
                max_mutations=5,
            ),
            ExecutionPlanLeg(
                role="spot_leg",
                account_id=account_id,
                instrument_id=str(
                    parameters.get(
                        "spotInstrumentId", f"instrument_{str(parameters['spotSymbol']).lower()}"
                    )
                ),
                external_symbol=str(parameters["spotSymbol"]).upper(),
                side=spot_side,
                maximum_quantity=spot_quantity,
                sequence=2,
                execution_policy=ExecutionPolicy.MARKET,
                depends_on="perpetual_leg",
                release_condition=ReleaseCondition.INCREMENTAL_CUMULATIVE_FILL,
                release_ratio=release_ratio,
                release_cap=spot_quantity,
                quantity_step=spot_step,
                contract_multiplier=Decimal(str(parameters.get("spotContractMultiplier", "1"))),
                minimum_quantity=spot_step,
            ),
        ),
    )
