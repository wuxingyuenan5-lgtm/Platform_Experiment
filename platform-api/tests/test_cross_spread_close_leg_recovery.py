"""Original close identity, exact remaining Ticket, and no duplicate first leg."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from test_cross_spread_position_pnl import add_group, market, mt5_position, overview

from app import cross_spread_close_recovery as recovery
from app import trade_commands
from app.config import get_settings
from app.cross_spread_exit_repository import get_exit_plan
from app.cross_spread_live_read_client import LivePosition
from app.cross_spread_synthetic_service import close_cross_spread_market
from app.database import connection, initialize_database
from app.execution_risk import initialize_batch_risk
from app.order_execution_intents import register_order_execution_intent


@pytest.fixture
def failed_close(monkeypatch):
    initialize_database()
    monkeypatch.setattr(get_settings(), "live_trading_enabled", True)
    add_group("target")
    add_group("close")
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        frozen = json.loads(
            db.execute("SELECT execution_plan_json FROM strategy_runs WHERE id='close'").fetchone()[
                0
            ]
        )
        frozen["action"] = "close"
        for leg in frozen["legs"]:
            leg["side"] = "sell" if leg["role"] == "bybit_leg" else "buy"
            if leg["role"] == "mt5_leg":
                leg["reduce_only"] = True
                leg["position_id"] = "ticket:target"
        db.execute("DELETE FROM cross_spread_exit_plans WHERE id='close'")
        db.execute(
            "UPDATE cross_spread_exit_plans SET status='manual_intervention',"
            "close_batch_id='close' WHERE id='target'"
        )
        db.execute(
            "UPDATE execution_batches SET status='manual_intervention',direction='close',"
            "strategy_instruction_id='close' WHERE id='close'"
        )
        db.execute(
            "UPDATE strategy_runs SET action='close',status='manual_intervention',"
            "execution_plan_json=?,requested_parameters_json=? WHERE id='close'",
            (json.dumps(frozen), json.dumps({"mt5PositionId": "ticket:target"})),
        )
        for role, side in [("bybit_leg", "sell"), ("mt5_leg", "buy")]:
            oid = f"close:{role}"
            db.execute("UPDATE execution_batch_legs SET side=? WHERE id=?", (side, oid))
            db.execute("UPDATE orders SET side=? WHERE id=?", (side, oid))
            db.execute("UPDATE fills SET side=? WHERE order_id=?", (side, oid))
            db.execute(
                "UPDATE trade_commands SET side=?,idempotency_key=? WHERE id=?",
                (side, f"instruction:close:{role}", oid),
            )
        db.execute("DELETE FROM fills WHERE order_id='close:mt5_leg'")
        db.execute(
            "UPDATE execution_batch_legs SET status='failed',order_id=NULL WHERE id='close:mt5_leg'"
        )
        db.execute("DELETE FROM orders WHERE id='close:mt5_leg'")
        db.execute("UPDATE trade_commands SET status='rejected' WHERE id='close:mt5_leg'")
    register_order_execution_intent(
        "instruction:close:mt5_leg", reduce_only=True, position_id="ticket:target"
    )
    initialize_batch_risk("close", get_exit_plan("target").strategy_instance_id)
    monkeypatch.setattr(recovery, "assert_live_account_execution_allowed", lambda *a: None)
    monkeypatch.setattr(trade_commands, "validate_trade_command_catalog", lambda *a: None)
    calls = []

    def native_positions(account_id):
        with connection() as db:
            closed = db.execute("SELECT 1 FROM fills WHERE order_id='recovered-order'").fetchone()
        return (
            []
            if closed
            else [
                LivePosition(
                    "mt5_live",
                    "ticket:target",
                    account_id,
                    "instrument_xau_usd",
                    "XAUUSD.s",
                    Decimal("-0.01"),
                )
            ]
        )

    def submit(request, **kwargs):
        calls.append((request, kwargs))
        assert request.account_id == "mt5-live-main"
        assert kwargs["position_id"] == "ticket:target" and kwargs["reduce_only"] is True
        assert kwargs["command_id"] == "close:mt5_leg"
        with connection() as db:
            db.execute(
                "INSERT INTO orders(id,command_id,account_id,instrument_id,symbol,side,"
                "order_type,quantity,status,created_at,updated_at) "
                "VALUES ('recovered-order',?,?,?,?,?,'market',?,'filled',?,?)",
                (
                    kwargs["command_id"],
                    request.account_id,
                    request.instrument_id,
                    request.symbol,
                    request.side,
                    str(request.quantity),
                    now,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO fills(id,order_id,account_id,instrument_id,side,quantity,"
                "price,occurred_at,origin,source) VALUES ('recovered-fill','recovered-order',"
                "?,?,?,?, '102',?,'runtime_confirmation','runtime_v1')",
                (
                    request.account_id,
                    request.instrument_id,
                    request.side,
                    str(request.quantity),
                    now,
                ),
            )
        return SimpleNamespace(status="filled")

    monkeypatch.setattr(recovery, "list_positions", native_positions)
    monkeypatch.setattr(trade_commands, "submit_trade_command_order", submit)
    return calls


def test_finish_original_close_sends_only_mt5_once(failed_close):
    result = close_cross_spread_market(
        "target", execution_mode="market", idempotency_key="new-click"
    )
    assert result.exit_plan.status == "closed"
    assert result.execution_batch.batch_id == "close"
    assert len(failed_close) == 1
    with connection() as db:
        assert (
            db.execute("SELECT count(*) FROM orders WHERE account_id='bybit-live-main'").fetchone()[
                0
            ]
            == 2
        )
        assert (
            db.execute("SELECT status FROM strategy_runs WHERE id='close'").fetchone()[0]
            == "completed"
        )
        assert (
            db.execute("SELECT count(*) FROM trade_commands WHERE id='close:mt5_leg'").fetchone()[0]
            == 1
        )
    # Repeating the user action must not dispatch either leg again.
    close_cross_spread_market("target", execution_mode="market", idempotency_key="new-click")
    assert len(failed_close) == 1


@pytest.mark.parametrize("state", ["accepted", "processing", "result_unknown", "filled"])
def test_uncertain_command_is_not_retried(failed_close, state):
    with connection() as db:
        db.execute("UPDATE trade_commands SET status=? WHERE id='close:mt5_leg'", (state,))
    with pytest.raises(HTTPException):
        close_cross_spread_market("target", execution_mode="market")
    assert not failed_close
    assert get_exit_plan("target").status == "manual_intervention"


def test_original_rejected_command_with_any_order_is_not_retried(failed_close):
    with connection() as db:
        db.execute("UPDATE orders SET command_id='close:mt5_leg' WHERE id='close:bybit_leg'")
    with pytest.raises(HTTPException):
        close_cross_spread_market("target", execution_mode="market")
    assert not failed_close


def test_changed_ticket_quantity_is_not_retried(failed_close, monkeypatch):
    monkeypatch.setattr(
        recovery,
        "list_positions",
        lambda account: [
            LivePosition(
                "mt5_live",
                "ticket:target",
                account,
                "instrument_xau_usd",
                "XAUUSD.s",
                Decimal("-0.02"),
            )
        ],
    )
    with pytest.raises(HTTPException, match="Ticket quantity"):
        close_cross_spread_market("target", execution_mode="market")
    assert not failed_close


def test_anomaly_projection_accounts_for_completed_bybit_close(failed_close):
    result = overview(market(positions=[mt5_position("target")]))
    assert not result.unattributedPositions
    row = next(r for r in result.abnormalOrders if r.planId == "target")
    assert row.bybitRemainingQuantity == 0 and row.mt5RemainingQuantity == Decimal("0.01")
    assert row.bybitCloseFilledQuantity == 1 and row.action == "finish_mt5"


def test_changed_recovery_quantity_cannot_rewrite_prior_close(failed_close):
    with pytest.raises(HTTPException, match="original close quantity"):
        close_cross_spread_market("target", execution_mode="market", quantity_oz=Decimal("0.5"))
    assert not failed_close
