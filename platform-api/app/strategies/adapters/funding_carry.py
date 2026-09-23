from __future__ import annotations

from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_DOWN, Decimal, localcontext

from app.strategies.domain import (
    ExecutionPlan,
    ExecutionPlanLeg,
    ExecutionPolicy,
    ReleaseCondition,
    StrategyInstructionAction,
)

SPOT_BASE_FEE_RATE = Decimal("0.001")


def funding_spot_quantity_for_perpetual(
    perpetual_quantity: Decimal,
    *,
    fee_rate: Decimal,
    spot_step: Decimal,
    spot_minimum: Decimal | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    """Return gross spot, net spot and rounding residual for a perp target.

    The perpetual leg is the hedge authority. Spot is rounded to the nearest
    executable step so the post-fee residual is minimal.
    """
    if not all(value.is_finite() for value in (perpetual_quantity, fee_rate, spot_step)):
        raise ValueError("Invalid Funding sizing inputs")
    if perpetual_quantity <= 0 or spot_step <= 0 or not 0 <= fee_rate < 1:
        raise ValueError("Invalid Funding sizing inputs")
    minimum = spot_minimum if spot_minimum is not None else spot_step
    if not minimum.is_finite() or minimum <= 0:
        raise ValueError("Invalid Funding minimum quantity")
    with localcontext() as context:
        context.prec = 50
        required_gross = perpetual_quantity / (1 - fee_rate)
        floor = (required_gross / spot_step).to_integral_value(rounding=ROUND_FLOOR) * spot_step
        ceil = (required_gross / spot_step).to_integral_value(rounding=ROUND_CEILING) * spot_step
        candidates = [candidate for candidate in {floor, ceil} if candidate >= minimum]
        if not candidates:
            raise ValueError("Funding spot quantity is below the venue minimum")
        gross_spot = min(
            candidates,
            key=lambda candidate: abs(candidate * (1 - fee_rate) - perpetual_quantity),
        )
        net_spot = gross_spot * (1 - fee_rate)
        return gross_spot, net_spot, net_spot - perpetual_quantity


def funding_open_quantities(
    spot_quantity: Decimal,
    *,
    fee_rate: Decimal,
    perpetual_step: Decimal,
    perpetual_minimum: Decimal | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    """Hedge the acquired coin inventory; quote-currency fees do not change delta."""
    if (
        not all(value.is_finite() for value in (spot_quantity, fee_rate, perpetual_step))
        or spot_quantity <= 0
        or perpetual_step <= 0
        or not 0 <= fee_rate < 1
    ):
        raise ValueError("Invalid Funding sizing inputs")
    with localcontext() as context:
        context.prec = 50
        net_spot = spot_quantity * (1 - fee_rate)
        perpetual_quantity = (net_spot / perpetual_step).to_integral_value(
            rounding=ROUND_HALF_DOWN
        ) * perpetual_step
        minimum = perpetual_minimum if perpetual_minimum is not None else perpetual_step
        if not minimum.is_finite() or minimum <= 0:
            raise ValueError("Invalid Funding minimum quantity")
        minimum = (minimum / perpetual_step).to_integral_value(
            rounding=ROUND_CEILING
        ) * perpetual_step
        if perpetual_quantity < minimum:
            perpetual_quantity = minimum if abs(minimum - net_spot) < net_spot else Decimal(0)
        return net_spot, perpetual_quantity, net_spot - perpetual_quantity


def build_funding_carry_plan(
    *, action: str, parameters: dict[str, object], created_at: datetime
) -> ExecutionPlan:
    policy = ExecutionPolicy(str(parameters.get("executionPolicy") or "post_only_chase"))
    raw_price = parameters.get("perpetualLimitPrice")
    limit_price = Decimal(str(raw_price)) if raw_price is not None else None
    if (policy == ExecutionPolicy.FOK) != (limit_price is not None):
        raise ValueError("Only FOK execution requires a perpetual limit price")
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
                execution_policy=policy,
                limit_price=limit_price,
                reduce_only=action == "close",
                quantity_step=perp_step,
                price_tick=Decimal(str(parameters.get("perpetualPriceTick", "0.01"))),
                contract_multiplier=Decimal(
                    str(parameters.get("perpetualContractMultiplier", "1"))
                ),
                minimum_quantity=Decimal(
                    str(parameters.get("perpetualMinimumQuantity", perp_step))
                ),
                max_mutations=5 if policy == ExecutionPolicy.POST_ONLY_CHASE else 0,
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
                price_tick=Decimal(str(parameters.get("spotPriceTick", "0.01"))),
                contract_multiplier=Decimal(str(parameters.get("spotContractMultiplier", "1"))),
                minimum_quantity=Decimal(str(parameters.get("spotMinimumQuantity", spot_step))),
            ),
        ),
    )
