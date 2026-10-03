import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.cross_spread_exit_repository import create_exit_plan, get_exit_plan
from app.cross_spread_live_read_client import LivePosition
from app.cross_spread_position_reconciliation import (
    assert_close_positions,
    reconcile_external_cross_spread_closes,
)
from app.database import connection, initialize_database
from app.live_venue_snapshot_sync import _persist_venue_snapshot
from tests.test_cross_spread_market_lifecycle import insert_batch_with_fills


@pytest.fixture
def setup_group(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "reconcile.db"))
    monkeypatch.setattr(get_settings(), "live_trading_enabled", False)
    initialize_database()
    plans = []
    for i in range(2):
        insert_batch_with_fills(f"open-{i}", record_prefix=str(i))
        plans.append(
            create_exit_plan(
                strategy_instance_id="strategy_cross_venue_spread_instance_default",
                open_batch_id=f"open-{i}",
                direction="LONG_SPREAD",
                quantity_oz=Decimal(1),
                mt5_position_id=f"ticket-{i}",
                entry_spread=Decimal(-2),
                take_profit_spread=None,
                stop_loss_spread=None,
            )
        )
    now = datetime.now(UTC).isoformat()
    bs = dict(
        source="bybit_live",
        venue="bybit",
        asOf=now,
        historyObservedAt=now,
        dataQualityState="complete",
        positions=[],
        orders=[],
        fills=[],
    )
    for i, qty in enumerate(("0.81", "1.19")):
        bs["orders"].append(
            dict(
                externalOrderId=f"close-{i}",
                instrumentId="instrument_xau_usdt_perp",
                status="filled",
                reduceOnly=True,
            )
        )
        bs["fills"].append(
            dict(
                externalFillId=f"fill-{i}",
                externalOrderId=f"close-{i}",
                instrumentId="instrument_xau_usdt_perp",
                occurredAt=now,
                side="sell",
                quantity=qty,
            )
        )
    ms = dict(
        source="mt5_live",
        venue="mt5",
        asOf=now,
        historyObservedAt=now,
        dataQualityState="complete",
        positions=[],
        orders=[],
        fills=[
            dict(
                externalFillId=f"deal-{i}",
                instrumentId="instrument_xau_usd",
                positionId=f"ticket-{i}",
                entryType=1,
                side="buy",
                quantity="0.01",
            )
            for i in range(2)
        ],
    )
    return plans, bs, ms


def save(bs, ms):
    from app.live_venue_snapshot_sync import _write_status

    for account in ("account_crypto_test", "account_mt5_demo"):
        _write_status(account, status="ready", error_code=None, last_attempt_at=bs["asOf"])
    with connection() as db:
        _persist_venue_snapshot(db, "account_crypto_test", bs)
        _persist_venue_snapshot(db, "account_mt5_demo", ms)


def test_external_aggregate_close_is_atomic_idempotent_and_preserves_execution(setup_group):
    plans, bs, ms = setup_group
    save(bs, ms)
    with connection() as db:
        db.execute(
            "INSERT INTO execution_batches(id,idempotency_key,strategy_instance_id,account_id,"
            "strategy_key,direction,status,created_at,updated_at) "
            "VALUES ('failed-close','failed-close',?,'account_crypto_test','cross_venue_spread',"
            "'CLOSE_LONG','failed',?,?)",
            (plans[0].strategy_instance_id, bs["asOf"], bs["asOf"]),
        )
        db.execute(
            "UPDATE cross_spread_exit_plans SET status='manual_intervention',"
            "close_batch_id='failed-close' WHERE id=?",
            (plans[0].plan_id,),
        )
        before = db.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    assert set(reconcile_external_cross_spread_closes()) == {p.plan_id for p in plans}
    assert reconcile_external_cross_spread_closes() == []
    for p in plans:
        current = get_exit_plan(p.plan_id)
        assert current.status == "closed" and current.quantity_oz == 0
        assert current.close_batch_id == ("failed-close" if p == plans[0] else None)
        from app.cross_spread_synthetic_service import close_cross_spread_market

        with pytest.raises(HTTPException, match="already closed by venue reconciliation"):
            close_cross_spread_market(p.plan_id, execution_mode="market")
    with connection() as db:
        assert (
            db.execute("SELECT status FROM execution_batches WHERE id='failed-close'").fetchone()[0]
            == "failed"
        )
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == before
        audits = db.execute(
            "SELECT details_json FROM audit_events WHERE event_type="
            "'cross_spread_external_close_reconciled'"
        ).fetchall()
        assert len(audits) == 2
        assert json.loads(audits[0][0])["allocation"] == "aggregate_only_no_per_plan_pnl"


@pytest.mark.parametrize(
    "case",
    [
        "stale",
        "partial",
        "missing_ticket",
        "wrong_side",
        "not_reduce_only",
        "history_stale",
        "position_remaining",
        "unknown_command",
        "inflight",
        "other_account",
        "sync_failed",
    ],
)
def test_incomplete_or_ambiguous_evidence_never_closes(setup_group, case):
    plans, bs, ms = setup_group
    if case == "stale":
        bs["asOf"] = (datetime.now(UTC) - timedelta(minutes=3)).isoformat()
    elif case == "partial":
        bs["fills"].pop()
    elif case == "missing_ticket":
        ms["fills"].pop()
    elif case == "wrong_side":
        ms["fills"][0]["side"] = "sell"
    elif case == "not_reduce_only":
        bs["orders"][0]["reduceOnly"] = False
    elif case == "history_stale":
        ms["historyObservedAt"] = None
    elif case == "position_remaining":
        ms["positions"] = [dict(instrumentId="instrument_xau_usd", netQuantity="-0.01")]
    elif case == "unknown_command":
        with connection() as db:
            db.execute(
                "INSERT INTO trade_commands(id,idempotency_key,strategy_instance_id,"
                "account_id,instrument_id,command_type,side,order_type,quantity,status,"
                "created_at,updated_at) "
                "VALUES ('unknown','unknown',?,'account_crypto_test','instrument_xau_usdt_perp',"
                "'submit_order','sell','market','1','result_unknown',?,?)",
                (plans[0].strategy_instance_id, bs["asOf"], bs["asOf"]),
            )
    elif case == "inflight":
        with connection() as db:
            db.execute(
                "UPDATE cross_spread_exit_plans SET status='triggered' WHERE id=?",
                (plans[0].plan_id,),
            )
    elif case == "other_account":
        with connection() as db:
            _persist_venue_snapshot(db, "account_crypto_test", bs)
        assert reconcile_external_cross_spread_closes() == []
        return
    save(bs, ms)
    if case == "sync_failed":
        with connection() as db:
            db.execute(
                "UPDATE account_sync_status SET status='failed' WHERE account_id='account_mt5_demo'"
            )
    assert reconcile_external_cross_spread_closes() == []
    assert all(get_exit_plan(p.plan_id).status != "closed" for p in plans)


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "missing_ticket",
        "partial_ticket",
        "wrong_ticket_side",
        "bybit_flat",
        "bybit_drift",
        "netted_groups",
    ],
)
def test_preflight_checks_both_native_legs(setup_group, monkeypatch, case):
    import app.cross_spread as cross
    import app.cross_spread_live_read_client as client

    plans, _, _ = setup_group
    monkeypatch.setattr(cross, "get_bybit_account_id", lambda: "account_crypto_test")
    monkeypatch.setattr(cross, "get_mt5_account_id", lambda: "account_mt5_demo")
    mt5_qty = {"partial_ticket": "-0.005", "wrong_ticket_side": "0.01"}.get(case, "-0.01")
    bybit_qty = {"bybit_flat": "0", "bybit_drift": "1", "netted_groups": "0"}.get(case, "2")
    if case == "netted_groups":
        with connection() as db:
            db.execute(
                "UPDATE cross_spread_exit_plans SET direction='SHORT_SPREAD' WHERE id=?",
                (plans[1].plan_id,),
            )
    positions = {
        "account_crypto_test": [
            LivePosition(
                "bybit_live",
                "net",
                "account_crypto_test",
                "instrument_xau_usdt_perp",
                "XAUTUSDT",
                Decimal(bybit_qty),
            )
        ],
        "account_mt5_demo": []
        if case == "missing_ticket"
        else [
            LivePosition(
                "mt5_live",
                "ticket-0",
                "account_mt5_demo",
                "instrument_xau_usd",
                "XAUUSD.S",
                Decimal(mt5_qty),
            )
        ],
    }
    monkeypatch.setattr(client, "list_positions", lambda account: positions[account])
    if case in {"valid", "netted_groups"}:
        assert_close_positions(plans[0])
    else:
        with pytest.raises(HTTPException, match="reconcile before closing"):
            assert_close_positions(plans[0])


def test_stale_close_cannot_dispatch_and_becomes_manual(setup_group, monkeypatch):
    import app.cross_spread as cross
    import app.cross_spread_live_read_client as client
    import app.cross_spread_synthetic_service as service

    plans, _, _ = setup_group
    monkeypatch.setattr(cross, "get_bybit_account_id", lambda: "account_crypto_test")
    monkeypatch.setattr(cross, "get_mt5_account_id", lambda: "account_mt5_demo")
    monkeypatch.setattr(client, "list_positions", lambda _: [])
    calls = []
    monkeypatch.setattr(
        service, "submit_cross_spread_market_command", lambda *a, **k: calls.append(a)
    )
    with pytest.raises(HTTPException, match="reconcile before closing"):
        service._close_claimed_plan(plans[0], execution_mode="market")
    assert calls == []
    assert get_exit_plan(plans[0].plan_id).status == "manual_intervention"
