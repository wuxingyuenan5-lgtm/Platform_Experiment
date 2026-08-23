from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.config import get_settings
from app.database import connection, initialize_database
from app.strategies.adapters.cross_spread import build_cross_spread_plan
from app.strategies.adapters.funding_carry import build_funding_carry_plan
from app.strategies.domain import ExecutionPolicy, ReleaseCondition, StrategyInstructionAction
from app.strategies.plan_service import build_plan


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


def test_live_funding_and_cross_spread_can_bind_the_same_logical_bybit_account(tmp_path) -> None:
    get_settings().database_path = str(tmp_path / "shared-bybit-binding.db")
    initialize_database()
    with connection() as db:
        db.execute(
            "UPDATE accounts SET status = 'active' WHERE id IN (?, ?)",
            ("account_crypto_test", "account_mt5_demo"),
        )
        db.execute(
            """
            UPDATE strategy_instances
            SET trading_mode = 'live', status = 'active'
            WHERE id = 'strategy_funding_arbitrage_instance_default'
            """
        )
        db.execute(
            """
            UPDATE strategy_account_bindings
            SET account_id = ?
            WHERE id = 'binding_funding_bybit'
            """,
            ("account_crypto_test",),
        )

    funding_plan = build_plan(
        "strategy_funding_arbitrage_instance_default",
        StrategyInstructionAction.OPEN,
        {
            "perpetualSymbol": "BTCUSDT",
            "perpetualQuantity": "1",
            "spotSymbol": "BTCUSDT",
            "spotQuantity": "1",
        },
    )
    with connection() as db:
        cross_binding = db.execute(
            """
            SELECT account_id
            FROM strategy_account_bindings
            WHERE strategy_instance_id = ?
              AND role = 'venue_a'
              AND status = 'active'
            """,
            ("strategy_cross_venue_spread_instance_default",),
        ).fetchone()

    assert funding_plan.legs[0].account_id == "account_crypto_test"
    assert cross_binding is not None
    assert cross_binding["account_id"] == "account_crypto_test"
