from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.cross_spread_exit_schemas import (
    CrossSpreadMarketCloseRequest,
    CrossSpreadMarketOpenRequest,
)
from app.runtime_contracts import RuntimeSubmitOrderCommandV1
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations

NOW = datetime(2026, 7, 26, tzinfo=UTC)


def test_existing_limit_requests_default_to_fok() -> None:
    open_request = CrossSpreadMarketOpenRequest(
        direction="LONG_SPREAD",
        quantityOz="1",
        takeProfitSpread="0",
        stopLossSpread="-3",
        executionMode="limit",
        limitSpread="-1",
    )
    close_request = CrossSpreadMarketCloseRequest(
        executionMode="limit",
        limitSpread="-1",
    )

    assert open_request.limit_strategy == "fok"
    assert open_request.take_profit_limit_strategy == "fok"
    assert open_request.stop_loss_limit_strategy == "fok"
    assert close_request.limit_strategy == "fok"


def test_postonly_strategy_is_additive_to_limit_execution() -> None:
    request = CrossSpreadMarketOpenRequest(
        direction="SHORT_SPREAD",
        quantityOz="1",
        takeProfitSpread="-3",
        stopLossSpread="0",
        executionMode="limit",
        limitSpread="-1",
        limitStrategy="post_only_chase",
        takeProfitExecutionMode="limit",
        takeProfitLimitStrategy="post_only_chase",
    )

    assert request.execution_mode == "limit"
    assert request.limit_strategy == "post_only_chase"
    assert request.take_profit_limit_strategy == "post_only_chase"


def test_runtime_rejects_nondefault_policy_for_market_order() -> None:
    with pytest.raises(ValidationError, match="require a limit order"):
        RuntimeSubmitOrderCommandV1(
            command_id="command-1",
            platform_order_id="order-1",
            strategy_instance_id="strategy-1",
            account_id="account-1",
            instrument_id="instrument-1",
            symbol="XAUTUSDT",
            side="buy",
            order_type="market",
            execution_policy="post_only_chase",
            quantity="1",
        )


def test_migration_defaults_existing_execution_and_exit_rows() -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    apply_migrations(db, PLATFORM_MIGRATIONS[:3])
    db.execute(
        """
        INSERT INTO order_execution_intents (
            idempotency_key, reduce_only, position_id
        ) VALUES ('intent-existing', 0, NULL)
        """
    )
    db.execute(
        """
        INSERT INTO cross_spread_exit_plans (
            id, strategy_instance_id, open_batch_id, close_batch_id, direction,
            quantity_oz, mt5_position_id, entry_spread, take_profit_spread,
            stop_loss_spread, take_profit_execution_mode,
            stop_loss_execution_mode, status, trigger_reason, trigger_spread,
            created_at, updated_at, triggered_at, closed_at
        ) VALUES (
            'plan-existing', 'strategy-existing', 'batch-existing', NULL,
            'LONG_SPREAD', '1', '12345', '-2', '0', '-3', 'limit', 'market',
            'active', NULL, NULL, ?, ?, NULL, NULL
        )
        """,
        (NOW.isoformat(), NOW.isoformat()),
    )

    apply_migrations(db, PLATFORM_MIGRATIONS[:4])

    intent = db.execute(
        """
        SELECT execution_policy
        FROM order_execution_intents
        WHERE idempotency_key = 'intent-existing'
        """
    ).fetchone()
    plan = db.execute(
        """
        SELECT take_profit_limit_strategy, stop_loss_limit_strategy
        FROM cross_spread_exit_plans
        WHERE id = 'plan-existing'
        """
    ).fetchone()
    assert intent["execution_policy"] == "default"
    assert plan["take_profit_limit_strategy"] == "fok"
    assert plan["stop_loss_limit_strategy"] == "fok"
