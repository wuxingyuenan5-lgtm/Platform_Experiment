from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.strategies.adapters.cross_spread import build_cross_spread_plan
from app.strategies.adapters.funding_carry import build_funding_carry_plan
from app.strategies.domain import ExecutionPolicy, ReleaseCondition


def test_cross_spread_plan_snapshots_decimal_conversion_and_terminal_release() -> None:
    plan = build_cross_spread_plan(
        action="open",
        parameters={
            "action": "OPEN_LONG",
            "quantityOz": "2",
            "bybitAccountId": "account_crypto_test",
            "mt5AccountId": "account_mt5_demo",
            "mt5ContractMultiplier": "100",
            "bybitQuantityStep": "0.001",
            "mt5QuantityStep": "0.01",
        },
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
    )

    assert plan.schema_version == "1"
    assert plan.legs[0].maximum_quantity == Decimal("2")
    assert plan.legs[1].maximum_quantity == Decimal("0.02")
    assert plan.legs[1].release_condition is ReleaseCondition.TERMINAL_FULL_FILL
    assert plan.legs[1].release_ratio == Decimal("0.01")
    assert plan.created_at == datetime(2026, 8, 22, tzinfo=UTC)
    assert plan.model_dump(mode="json")["legs"][1]["maximum_quantity"] == "0.02"


def test_funding_plan_is_perpetual_first_post_only_with_incremental_spot_release() -> None:
    plan = build_funding_carry_plan(
        action="open",
        parameters={
            "perpetualSymbol": "BTCUSDT",
            "perpetualQuantity": "1.5",
            "spotSymbol": "BTC",
            "spotQuantity": "1.25",
            "accountId": "account_sim_usdt",
            "perpetualInstrumentId": "instrument_btcusdt",
            "spotInstrumentId": "instrument_btc",
            "perpetualQuantityStep": "0.001",
            "spotQuantityStep": "0.000001",
        },
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
    )

    perpetual, spot = plan.legs
    assert perpetual.role == "perpetual_leg"
    assert perpetual.execution_policy is ExecutionPolicy.POST_ONLY_CHASE
    assert spot.depends_on == "perpetual_leg"
    assert spot.release_condition is ReleaseCondition.INCREMENTAL_CUMULATIVE_FILL
    assert spot.release_ratio == Decimal("0.8333333333333333333333333333")
    assert spot.release_cap == Decimal("1.25")


def test_funding_plan_rejects_market_policy_override() -> None:
    with pytest.raises(ValueError, match="post_only_chase"):
        build_funding_carry_plan(
            action="open",
            parameters={
                "perpetualSymbol": "BTCUSDT",
                "perpetualQuantity": "1",
                "spotSymbol": "BTC",
                "spotQuantity": "1",
                "accountId": "account_sim_usdt",
                "executionPolicy": "market",
            },
            created_at=datetime(2026, 8, 22, tzinfo=UTC),
        )


def test_funding_plan_freezes_price_ticks_for_phase_2_postonly_open() -> None:
    plan = build_funding_carry_plan(
        action="open",
        parameters={
            "perpetualSymbol": "BTCUSDT",
            "perpetualQuantity": "1",
            "spotSymbol": "BTC",
            "spotQuantity": "1",
            "accountId": "account_sim_usdt",
            "perpetualPriceTick": "0.10",
            "spotPriceTick": "0.01",
        },
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
    )

    assert plan.simulation_compatibility_policy is None
    assert plan.legs[0].execution_policy is ExecutionPolicy.POST_ONLY_CHASE
    assert plan.legs[0].price_tick == Decimal("0.10")
    assert plan.legs[1].price_tick == Decimal("0.01")
