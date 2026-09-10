"""Regression for a close rejected before instruction creation, using isolated SQLite."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app import cross_spread_synthetic_service as service
from app.config import get_settings
from app.cross_spread_exit_repository import (
    create_exit_plan,
    get_exit_plan,
    mark_plan_manual_intervention,
    reclaim_manual_exit_plan,
)
from app.database import connection, initialize_database


@pytest.fixture
def plan(monkeypatch):
    initialize_database()
    monkeypatch.setattr(get_settings(), "live_trading_enabled", True)
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            "INSERT INTO execution_batches(id,idempotency_key,strategy_instance_id,account_id,"
            "strategy_key,direction,status,created_at,updated_at) "
            "VALUES ('open','open','strategy_cross_venue_spread_instance_default',"
            "'bybit-live-main','cross_venue_spread','OPEN_LONG','hedged',?,?)",
            (now, now),
        )
    return create_exit_plan(
        strategy_instance_id="strategy_cross_venue_spread_instance_default",
        open_batch_id="open",
        direction="LONG_SPREAD",
        quantity_oz=Decimal("1"),
        mt5_position_id="target-ticket",
        entry_spread=Decimal("-5.53"),
        take_profit_spread=None,
        stop_loss_spread=None,
    )


@pytest.mark.parametrize("mode", ["market", "limit"])
def test_disabled_gate_does_not_change_plan_or_create_instruction(plan, monkeypatch, mode):
    monkeypatch.setattr(get_settings(), "live_trading_enabled", False)
    with pytest.raises(HTTPException, match="execution is disabled"):
        service.close_cross_spread_market(plan.plan_id, execution_mode=mode)
    assert get_exit_plan(plan.plan_id) == plan
    with connection() as db:
        assert db.execute("SELECT count(*) FROM strategy_runs").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM trade_commands").fetchone()[0] == 0


@pytest.mark.parametrize("quantity", [Decimal("1"), Decimal("0.5")])
def test_pre_dispatch_rejection_can_close_once_with_original_quantity(plan, monkeypatch, quantity):
    mark_plan_manual_intervention(plan.plan_id, close_batch_id=None)
    calls = []
    monkeypatch.setattr(
        service, "_close_claimed_plan", lambda claimed, **kw: calls.append((claimed, kw))
    )
    service.close_cross_spread_market(
        plan.plan_id,
        execution_mode="market",
        quantity_oz=quantity,
        idempotency_key="owner-close",
    )
    claimed, kwargs = calls[0]
    assert claimed.status == "triggered"
    assert claimed.mt5_position_id == "target-ticket"
    assert kwargs["idempotency_key"] == "owner-close"
    assert kwargs["quantity_oz"] == quantity
    with pytest.raises(HTTPException, match="not active"):
        service.close_cross_spread_market(plan.plan_id, execution_mode="market")
    assert len(calls) == 1


@pytest.mark.parametrize("ticket", ["target-ticket", None])
@pytest.mark.parametrize("status", ["pending", "result_unknown", "rejected", "completed"])
def test_missing_batch_link_never_bypasses_existing_instruction(plan, ticket, status):
    mark_plan_manual_intervention(plan.plan_id, close_batch_id=None)
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            "INSERT INTO strategy_runs(id,idempotency_key,strategy_instance_id,strategy_key,"
            "direction,status,action,requested_parameters_json,created_at,updated_at) "
            "VALUES ('prior','prior',?,'cross_venue_spread','close',?,'close',?,?,?)",
            (
                plan.strategy_instance_id,
                status,
                json.dumps({"mt5PositionId": ticket, "action": "CLOSE_LONG"}),
                now,
                now,
            ),
        )
    with pytest.raises(HTTPException, match="reconcile it first"):
        reclaim_manual_exit_plan(plan.plan_id, expected_close_batch_id=None)
    assert get_exit_plan(plan.plan_id).status == "manual_intervention"
