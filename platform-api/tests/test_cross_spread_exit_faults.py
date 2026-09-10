"""Persisted exits under quote outages and competing callers; no live I/O."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, Event

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import cross_spread_synthetic_service as service
from app.config import get_settings
from app.cross_spread_exit_repository import create_exit_plan, get_exit_plan
from app.database import connection
from app.main import app
from tests.test_cross_spread_market_lifecycle import (
    available_snapshot,
    batch_response,
    configure_platform,
    insert_batch_with_fills,
)


@pytest.fixture
def saved_exit(tmp_path, monkeypatch):
    configure_platform(tmp_path)
    monkeypatch.setattr(get_settings(), "research_refresh_enabled", False)
    with TestClient(app):
        insert_batch_with_fills("fault-open")
        plan = create_exit_plan(
            strategy_instance_id="strategy_cross_venue_spread_instance_default",
            open_batch_id="fault-open",
            direction="LONG_SPREAD",
            quantity_oz=Decimal("1"),
            mt5_position_id="778899",
            entry_spread=Decimal("-2"),
            take_profit_spread=Decimal("-1.3"),
            stop_loss_spread=Decimal("-3"),
        )
    return plan


def isolated_submitter(monkeypatch, *, before_return=None):
    submissions = []

    def submit(request, **kwargs):
        submissions.append((request, kwargs))
        if before_return:
            before_return()
        result = batch_response("fault-close", direction="CLOSE_LONG")
        with connection() as db:
            db.execute(
                "INSERT INTO execution_batches "
                "(id,idempotency_key,strategy_instance_id,account_id,strategy_key,direction,"
                "status,requires_manual_intervention,created_at,updated_at) "
                "SELECT ?,?,strategy_instance_id,account_id,strategy_key,'CLOSE_LONG',"
                "'hedged',0,created_at,updated_at FROM execution_batches WHERE id='fault-open'",
                (result.batch_id, kwargs["idempotency_key"]),
            )
        return result

    monkeypatch.setattr(service, "submit_cross_spread_market_command", submit)
    return submissions


@pytest.mark.parametrize("failure", ["unavailable", "exception"])
def test_monitor_recovers_quotes_without_replaying_missed_threshold(
    saved_exit, monkeypatch, failure
):
    stage = {"value": "outage"}
    outage_seen, recovered_seen, closed = Event(), Event(), Event()
    submissions = isolated_submitter(monkeypatch, before_return=closed.set)

    def snapshot():
        quote = available_snapshot()
        if stage["value"] == "outage":
            outage_seen.set()
            if failure == "exception":
                raise RuntimeError("isolated market transport disconnected")
            # Keep the old crossed spread to prove status gates cached prices.
            return quote.model_copy(update={"status": "unavailable"})
        if stage["value"] == "recovered":
            recovered_seen.set()
            return quote.model_copy(update={"short_spread": Decimal("-2")})
        return quote

    monkeypatch.setattr(service, "get_cross_spread_snapshot", snapshot)
    monkeypatch.setattr(get_settings(), "cross_spread_exit_monitor_enabled", True)
    monkeypatch.setattr(get_settings(), "cross_spread_exit_monitor_interval_seconds", 0.01)
    with TestClient(app):
        assert outage_seen.wait(3)
        assert get_exit_plan(saved_exit.plan_id).status == "active"
        assert not submissions
        stage["value"] = "recovered"
        assert recovered_seen.wait(3)
        assert service.evaluate_cross_spread_exit_plans().triggered_count == 0
        assert get_exit_plan(saved_exit.plan_id).status == "active"
        assert not submissions
        stage["value"] = "crossed"
        assert closed.wait(3)
    assert get_exit_plan(saved_exit.plan_id).status == "closed"
    assert get_exit_plan(saved_exit.plan_id).quantity_oz == 0
    assert len(submissions) == 1
    # Another lifespan must read the settled plan rather than resubmit it.
    with TestClient(app):
        assert service.evaluate_cross_spread_exit_plans().triggered_count == 0
    assert len(submissions) == 1


@pytest.mark.parametrize("winner", ["manual", "take_profit"])
def test_manual_close_and_background_trigger_share_atomic_claim(saved_exit, monkeypatch, winner):
    ready, claimed, loser_finished = Barrier(2), Event(), Event()
    original_claim = service.claim_exit_plan

    def ordered_claim(plan_id, **kwargs):
        ready.wait(timeout=3)
        if kwargs["trigger_reason"] == winner:
            result = original_claim(plan_id, **kwargs)
            claimed.set()
            return result
        assert claimed.wait(3)
        result = original_claim(plan_id, **kwargs)
        assert result is None
        loser_finished.set()
        return result

    def wait_for_loser():
        assert loser_finished.wait(3)

    monkeypatch.setattr(service, "claim_exit_plan", ordered_claim)
    monkeypatch.setattr(service, "get_cross_spread_snapshot", available_snapshot)
    monkeypatch.setattr(service, "assert_cross_spread_live_execution_enabled", lambda: None)
    submissions = isolated_submitter(monkeypatch, before_return=wait_for_loser)

    def manual_close():
        try:
            return service.close_cross_spread_market(
                saved_exit.plan_id, execution_mode="market", idempotency_key="fault-manual"
            )
        except HTTPException as exc:
            assert exc.status_code == 409
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        manual = pool.submit(manual_close)
        background = pool.submit(service.evaluate_cross_spread_exit_plans)
        manual_result = manual.result(timeout=5)
        background_result = background.result(timeout=5)
    assert (manual_result is not None) == (winner == "manual")
    assert background_result.triggered_count == (winner == "take_profit")
    current = get_exit_plan(saved_exit.plan_id)
    assert (current.status, current.quantity_oz, current.trigger_reason) == (
        "closed", Decimal("0"), winner
    )
    assert len(submissions) == 1
    request, options = submissions[0]
    assert request.quantity_oz == Decimal("1")
    assert options["mt5_position_id"] == "778899"
    assert options["mt5_reduce_only"] is True
    with connection() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM execution_batches WHERE direction='CLOSE_LONG'"
        ).fetchone()[0] == 1


def test_limit_trigger_loses_quote_before_dispatch_then_recovers(saved_exit, monkeypatch):
    from app.cross_spread_exit_repository import update_exit_plan_settings

    update_exit_plan_settings(
        saved_exit.plan_id,
        take_profit_execution_mode="limit",
        update_take_profit_execution_mode=True,
    )
    calls = []
    quotes = iter([
        available_snapshot(),
        available_snapshot().model_copy(update={"status": "unavailable"}),
    ])
    monkeypatch.setattr(service, "get_cross_spread_snapshot", lambda: next(quotes))
    monkeypatch.setattr(service, "_submit_limit_batch", lambda *a, **k: calls.append(k))
    result = service.evaluate_cross_spread_exit_plans()
    assert result.triggered_count == 1
    current = get_exit_plan(saved_exit.plan_id)
    assert current.status == "active"
    assert current.triggered_at is None
    assert current.close_batch_id is None
    assert not calls
    submissions = isolated_submitter(monkeypatch)
    monkeypatch.setattr(service, "get_cross_spread_snapshot", available_snapshot)
    monkeypatch.setattr(service, "get_bybit_catalog_tick_size", lambda: Decimal("0.1"))
    monkeypatch.setattr(get_settings(), "cross_spread_limit_hedge_reserve_price", Decimal("0"))
    monkeypatch.setattr(
        service, "_submit_limit_batch", service.submit_cross_spread_market_command
    )
    assert service.evaluate_cross_spread_exit_plans().triggered_count == 1
    assert get_exit_plan(saved_exit.plan_id).status == "closed"
    assert len(submissions) == 1
