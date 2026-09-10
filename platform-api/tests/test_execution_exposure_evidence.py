from __future__ import annotations

import json
from decimal import Decimal

import pytest

from app.config import get_settings
from app.database import connection, initialize_database
from app.execution_exposure import calculate_residual_exposure
from app.execution_risk import initialize_batch_risk
from app.execution_risk_repository import (
    filled_quantity,
    recheck_batch_risk,
    recheck_risks_for_order,
    set_batch_risk_state,
)
from app.live_venue_snapshot_sync import _persist_venue_event

pytestmark = pytest.mark.integration
STRATEGY = "strategy_cross_venue_spread_instance_default"
ACCOUNT = "account_sim_usdt"
INSTRUMENT = "instrument_btc_usdt"
AT = "2026-09-08T08:00:00+00:00"


def add_order(db, name, side, *, key=None, status="filled", quantity="1", account=ACCOUNT):
    db.execute(
        "INSERT INTO trade_commands (id,idempotency_key,strategy_instance_id,account_id,"
        "instrument_id,command_type,side,order_type,quantity,status,created_at,updated_at) "
        "VALUES (?,?,?,?,?,'place_order',?,'market',?,?,?,?)",
        (name, key or name, STRATEGY, account, INSTRUMENT, side, quantity, status, AT, AT),
    )
    db.execute(
        "INSERT INTO orders (id,command_id,account_id,instrument_id,symbol,side,order_type,"
        "quantity,status,external_order_id,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,'market',?,?,?,?,?)",
        (
            name,
            name,
            account,
            INSTRUMENT,
            "BTCUSDT",
            side,
            quantity,
            status,
            f"native-{name}",
            AT,
            AT,
        ),
    )


def add_fill(db, order, quantity, *, suffix="confirm", origin="runtime_confirmation", price="100"):
    o = db.execute("SELECT * FROM orders WHERE id=?", (order,)).fetchone()
    db.execute(
        "INSERT INTO fills (id,order_id,account_id,instrument_id,side,quantity,price,"
        "occurred_at,origin) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            f"{order}:{suffix}",
            order,
            o["account_id"],
            o["instrument_id"],
            o["side"],
            quantity,
            price,
            AT,
            origin,
        ),
    )


def add_native(db, order, quantity, *, suffix="native", external_order_id=None, side=None):
    o = db.execute("SELECT * FROM orders WHERE id=?", (order,)).fetchone()
    _persist_venue_event(
        db,
        o["account_id"],
        "trade_fill",
        {
            "source": "test-venue",
            "accountId": o["account_id"],
            "instrumentId": o["instrument_id"],
            "externalOrderId": external_order_id or o["external_order_id"],
            "externalFillId": f"{order}:{suffix}",
            "side": side or o["side"],
            "quantity": quantity,
            "price": "101",
            "occurredAt": AT,
            "symbol": o["symbol"],
            "currency": "USDT",
        },
    )


@pytest.fixture
def batch(tmp_path):
    get_settings().database_path = str(tmp_path / "exposure.db")
    initialize_database()
    with connection() as db:
        db.execute(
            "INSERT INTO execution_batches (id,idempotency_key,strategy_instance_id,account_id,"
            "strategy_key,direction,status,created_at,updated_at) "
            "VALUES ('batch','batch',?,?,'cross_venue_spread','OPEN_LONG','hedged',?,?)",
            (STRATEGY, ACCOUNT, AT, AT),
        )
        for index, (name, side) in enumerate((("first", "buy"), ("second", "sell"))):
            add_order(db, name, side)
            add_fill(db, name, "1")
            db.execute(
                "INSERT INTO execution_batch_legs (id,batch_id,sequence,role,account_id,"
                "instrument_id,"
                "symbol,side,order_type,quantity,order_id,status,created_at,updated_at) "
                "VALUES (?,'batch',?,?,?,?,'BTCUSDT',?,'market','1',?,'filled',?,?)",
                (
                    name,
                    index,
                    "bybit_leg" if index == 0 else "mt5_leg",
                    ACCOUNT,
                    INSTRUMENT,
                    side,
                    name,
                    AT,
                    AT,
                ),
            )
    initialize_batch_risk("batch", STRATEGY)
    set_batch_risk_state(
        "batch",
        "escalated",
        residual=Decimal("100"),
        reason="Historical second leg acknowledgement",
    )
    return "batch"


def test_legacy_confirmation_and_executions_require_native_proof_and_audited_closure(batch):
    with connection() as db:
        db.execute("UPDATE fills SET origin='legacy'")
        add_fill(db, "first", "0.4", suffix="old-part-a", origin="legacy")
        add_fill(db, "first", "0.6", suffix="old-part-b", origin="legacy")
        original = [tuple(row) for row in db.execute("SELECT * FROM fills ORDER BY id")]
    assert calculate_residual_exposure(batch)[2] == "incomplete"
    assert recheck_batch_risk(batch, reason="No native proof").risk_status == "escalated"
    with connection() as db:
        add_native(db, "first", "0.4", suffix="a")
        add_native(db, "first", "0.6", suffix="b")
        add_native(db, "second", "1")
    result = recheck_batch_risk(batch, reason="Verified historical native executions")
    assert result.risk_status == "resolved"
    assert result.residual_exposure_notional == 0
    assert filled_quantity("first", Decimal("1")) == Decimal("1")
    with connection() as db:
        audit_count = db.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        evidence = json.loads(
            db.execute(
                "SELECT details_json FROM audit_events "
                "WHERE event_type='execution_batch_risk_reconciled' "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()[0]
        )
        assert len(evidence["orders"][0]["fillIds"]) == 2
        assert original == [tuple(row) for row in db.execute("SELECT * FROM fills ORDER BY id")]
    assert recheck_batch_risk(batch, reason="Replay").risk_status == "resolved"
    with connection() as db:
        assert audit_count == db.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]


@pytest.mark.parametrize("status", ["acknowledged", "result_unknown", "processing"])
def test_balanced_known_quantities_do_not_clear_unresolved_orders(batch, status):
    with connection() as db:
        db.execute("UPDATE orders SET status=? WHERE id='second'", (status,))
        db.execute("UPDATE trade_commands SET status=? WHERE id='second'", (status,))
    result = recheck_batch_risk(batch, reason="Incomplete terminal evidence")
    assert result.risk_status == "escalated"
    assert result.data_quality_state == "incomplete"


def test_partial_fills_are_counted_even_when_the_leg_is_acknowledged(batch):
    with connection() as db:
        db.execute("UPDATE fills SET quantity='0.4' WHERE order_id='second'")
        db.execute("UPDATE orders SET status='acknowledged' WHERE id='second'")
        db.execute("UPDATE execution_batch_legs SET status='acknowledged' WHERE order_id='second'")
    residual, _, quality = calculate_residual_exposure(batch)
    assert residual == Decimal("60")
    assert quality == "incomplete"


def test_actual_native_overfill_is_preserved_and_blocks_even_when_net_zero(batch):
    with connection() as db:
        for order in ("first", "second"):
            add_native(db, order, "1.2")
    residual, _, quality = calculate_residual_exposure(batch)
    assert residual == 0
    assert quality == "incomplete"
    assert recheck_batch_risk(batch, reason="Excess execution evidence").risk_status == "escalated"


@pytest.mark.parametrize("rollback_status", ["filled", "result_unknown"])
def test_independent_rollback_is_matched_by_exact_command_identity(batch, rollback_status):
    with connection() as db:
        db.execute("UPDATE execution_batches SET status='failed' WHERE id=?", (batch,))
        db.execute(
            "UPDATE execution_batch_legs SET order_id=NULL,status='failed' WHERE role='mt5_leg'"
        )
        add_order(
            db,
            "rollback",
            "sell",
            key=f"cross-spread-rollback:{batch}:bybit",
            status=rollback_status,
        )
        add_fill(db, "rollback", "1")
    recheck_risks_for_order("rollback", reason="Rollback execution reconciled")
    result = recheck_batch_risk(batch, reason="Replay")
    assert result.risk_status == ("resolved" if rollback_status == "filled" else "escalated")
    assert result.residual_exposure_notional == 0


def test_unrelated_same_account_order_does_not_offset_residual(batch):
    with connection() as db:
        db.execute(
            "UPDATE execution_batch_legs SET order_id=NULL,status='failed' WHERE role='mt5_leg'"
        )
        add_order(db, "unrelated", "sell", key="cross-spread-rollback:another-batch:bybit")
        add_fill(db, "unrelated", "1")
    assert calculate_residual_exposure(batch)[0] == Decimal("100")


def test_native_side_conflict_cannot_clear_risk(batch):
    with connection() as db:
        add_native(db, "first", "1", side="sell")
    assert recheck_batch_risk(batch, reason="Conflicting side").data_quality_state == "incomplete"


def test_late_runtime_recovery_refreshes_existing_batch_risk_without_an_order_submission(
    batch, monkeypatch
):
    from app.trading import reconcile_order

    with connection() as db:
        db.execute("DELETE FROM fills WHERE order_id='second'")
        db.execute("UPDATE orders SET status='result_unknown' WHERE id='second'")
        db.execute("UPDATE trade_commands SET status='result_unknown' WHERE id='second'")
        db.execute("UPDATE execution_batches SET status='manual_intervention' WHERE id=?", (batch,))
        db.execute("UPDATE execution_batch_legs SET status='acknowledged' WHERE order_id='second'")
    monkeypatch.setattr(
        "app.trading.recover_and_read_runtime_events",
        lambda _: [
            {
                "event_id": "late-fill",
                "command_id": "second",
                "platform_order_id": "second",
                "event_type": "order_filled",
                "external_order_id": "native-second",
                "fill_quantity": "1",
                "fill_price": "100",
                "occurred_at": AT,
                "reason": None,
            }
        ],
    )
    assert reconcile_order("second").status == "filled"
    assert recheck_batch_risk(batch, reason="Replay").risk_status == "resolved"
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 2
