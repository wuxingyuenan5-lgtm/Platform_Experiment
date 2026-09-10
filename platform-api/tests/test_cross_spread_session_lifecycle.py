"""Browser lifetime must not own persisted Cross exits; all execution is stubbed."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app import cross_spread_synthetic_service as service
from app.config import get_settings
from app.cross_spread_exit_repository import create_exit_plan, get_exit_plan
from app.database import connection
from app.main import app
from app.user_service import create_initial_ceo, issue_browser_session, logout_by_token
from app.user_session_auth import BrowserSessionError, authenticate_browser_session
from tests.test_cross_spread_market_lifecycle import (
    available_snapshot,
    configure_platform,
    insert_batch_with_fills,
)


@pytest.mark.parametrize("session_end", ["expired", "logout"])
def test_background_exit_survives_browser_end_and_application_restart(
    monkeypatch, tmp_path, session_end
):
    configure_platform(tmp_path)
    settings = get_settings()
    with TestClient(app):
        insert_batch_with_fills("browser-independent-open")
        plan = create_exit_plan(
            strategy_instance_id="strategy_cross_venue_spread_instance_default",
            open_batch_id="browser-independent-open",
            direction="LONG_SPREAD",
            quantity_oz=Decimal("1"),
            mt5_position_id="778899",
            entry_spread=Decimal("-2"),
            take_profit_spread=Decimal("-1.3"),
            stop_loss_spread=Decimal("-3"),
        )
        owner = create_initial_ceo(username="exit-owner", password="isolated owner password 123!")
        now = datetime.now(UTC)
        issued = issue_browser_session(
            user_id=owner.id, ip_address=None, user_agent="pytest", now=now
        )
        if session_end == "logout":
            logout_by_token(
                raw_session_token=issued.session_token,
                request_id="isolated-logout",
                ip_address=None,
                now=now,
            )
        with pytest.raises(BrowserSessionError):
            authenticate_browser_session(
                issued.session_token, settings, now=now + timedelta(minutes=31)
            )
        assert get_exit_plan(plan.plan_id).model_dump() == plan.model_dump()

    # New application lifespan, with no browser cookie or authenticated request.
    # Only the final trading boundary is replaced; the real monitor reads and
    # atomically claims the plan from the same isolated on-disk SQLite database.
    attempted = []
    reached = Event()

    def record_close(claimed):
        attempted.append((claimed.plan_id, claimed.mt5_position_id, claimed.trigger_reason))
        reached.set()

    monkeypatch.setattr(service, "get_cross_spread_snapshot", available_snapshot)
    monkeypatch.setattr(service, "_close_claimed_plan_for_trigger", record_close)
    monkeypatch.setattr(settings, "cross_spread_exit_monitor_enabled", True)
    monkeypatch.setattr(settings, "cross_spread_exit_monitor_interval_seconds", 0.01)
    with TestClient(app):
        assert reached.wait(3), "Backend monitor did not resume after application restart"
        assert get_exit_plan(plan.plan_id).status == "triggered"
        assert service.evaluate_cross_spread_exit_plans().triggered_count == 0
    assert attempted == [(plan.plan_id, "778899", "take_profit")]
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 0


def test_reload_and_backend_restart_reuse_browser_session(tmp_path):
    configure_platform(tmp_path)
    settings = get_settings()
    with TestClient(app) as client:
        owner = create_initial_ceo(username="refresh-owner", password="isolated password 123!")
        issued = issue_browser_session(user_id=owner.id, ip_address=None, user_agent="pytest")
        client.cookies.set(settings.session_cookie_name, issued.session_token)
        for _ in range(4):
            response = client.get("/api/v1/auth/me")
            assert response.status_code == 200
            assert response.json()["session"]["sessionId"] == issued.session_id
    with TestClient(app) as restarted:
        restarted.cookies.set(settings.session_cookie_name, issued.session_token)
        response = restarted.get("/api/v1/auth/me")
        assert response.status_code == 200
        assert response.json()["session"]["sessionId"] == issued.session_id
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM user_sessions").fetchone()[0] == 1
