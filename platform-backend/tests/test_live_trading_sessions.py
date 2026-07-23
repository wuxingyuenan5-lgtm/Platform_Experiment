import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def credential(user_id: str, token: str, roles: list[str]) -> dict[str, object]:
    return {
        "credentialId": f"credential-{user_id}",
        "userId": user_id,
        "tokenSha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "roles": roles,
        "status": "active",
    }


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def configure_live(monkeypatch, tmp_path: Path) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "live-sessions.db"))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(
        settings,
        "auth_credentials_json",
        json.dumps(
            [
                credential("trader-1", "trader-token", ["trader"]),
                credential("risk-1", "risk-token", ["risk_officer"]),
                credential("admin-1", "admin-token", ["admin"]),
            ]
        ),
    )
    monkeypatch.setattr(settings, "live_trading_enabled", True)
    monkeypatch.setattr(settings, "require_live_trading_session", True)
    monkeypatch.setattr(settings, "live_session_absolute_max_order_notional", 1000)
    monkeypatch.setattr(settings, "live_session_absolute_max_daily_notional", 2000)


def make_account_live() -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE accounts
            SET environment = 'live', account_type = 'live',
                credential_ref = 'secret://test-live-account', status = 'active'
            WHERE id = ?
            """,
            (ACCOUNT_ID,),
        )


def session_payload(key: str = "minimum-live-session-001") -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "idempotencyKey": key,
        "sessionType": "minimum_size_acceptance",
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "symbols": ["BTCUSDT"],
        "sides": ["buy", "sell"],
        "orderTypes": ["limit"],
        "startsAt": (now - timedelta(minutes=1)).isoformat(),
        "endsAt": (now + timedelta(hours=1)).isoformat(),
        "maxOrderNotional": "100",
        "maxDailyNotional": "200",
        "readOnlyVerifiedAt": (now - timedelta(minutes=10)).isoformat(),
        "evidenceReference": "ops://readonly-preflight/test-001",
        "reason": "minimum-size real-account acceptance window",
    }


def order_payload(key: str) -> dict[str, str]:
    return {
        "idempotencyKey": key,
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "instrumentId": INSTRUMENT_ID,
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": "0.01",
        "price": "100",
    }


def test_two_person_approval_and_live_order_claim(monkeypatch, tmp_path: Path) -> None:
    configure_live(monkeypatch, tmp_path)
    with TestClient(app) as client:
        make_account_live()

        requested = client.post(
            "/api/v1/live-trading/sessions",
            headers=headers("trader-token"),
            json=session_payload(),
        )
        assert requested.status_code == 200
        session = requested.json()
        assert session["status"] == "pending"
        assert session["applicantUserId"] == "trader-1"

        replay = client.post(
            "/api/v1/live-trading/sessions",
            headers=headers("trader-token"),
            json=session_payload(),
        )
        assert replay.status_code == 200
        assert replay.json()["sessionId"] == session["sessionId"]

        approved = client.post(
            f"/api/v1/live-trading/sessions/{session['sessionId']}/approve",
            headers=headers("risk-token"),
            json={"reason": "read-only evidence and minimum limits verified"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert approved.json()["approverUserId"] == "risk-1"
        assert approved.json()["applicantUserId"] != approved.json()["approverUserId"]

        def runtime_unavailable(*args, **kwargs):
            raise httpx.ConnectError("runtime unavailable")

        monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_unavailable)
        order = client.post(
            "/api/v1/trading/commands",
            headers=headers("trader-token"),
            json=order_payload("live-command-approved-001"),
        )
        assert order.status_code == 200
        assert order.json()["status"] == "result_unknown"

        with connection() as db:
            claims = db.execute(
                "SELECT COUNT(*) AS count FROM live_trading_session_claims"
            ).fetchone()["count"]
        assert claims == 1


def test_applicant_cannot_self_approve_even_with_admin_role(monkeypatch, tmp_path: Path) -> None:
    configure_live(monkeypatch, tmp_path)
    with TestClient(app) as client:
        make_account_live()
        requested = client.post(
            "/api/v1/live-trading/sessions",
            headers=headers("admin-token"),
            json=session_payload("admin-self-approval-session"),
        )
        assert requested.status_code == 200
        response = client.post(
            f"/api/v1/live-trading/sessions/{requested.json()['sessionId']}/approve",
            headers=headers("admin-token"),
            json={"reason": "must be rejected because applicant and approver are identical"},
        )
        assert response.status_code == 403
        assert "cannot approve" in response.json()["detail"]


def test_live_order_without_approved_session_is_rejected(monkeypatch, tmp_path: Path) -> None:
    configure_live(monkeypatch, tmp_path)
    with TestClient(app) as client:
        make_account_live()
        response = client.post(
            "/api/v1/trading/commands",
            headers=headers("trader-token"),
            json=order_payload("live-command-without-session"),
        )
        assert response.status_code == 403
        assert "LiveTradingSession" in response.json()["detail"]


def test_limit_and_kill_switch_block_session_approval(monkeypatch, tmp_path: Path) -> None:
    configure_live(monkeypatch, tmp_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "live_session_absolute_max_order_notional", 50)
    with TestClient(app) as client:
        make_account_live()
        requested = client.post(
            "/api/v1/live-trading/sessions",
            headers=headers("trader-token"),
            json=session_payload("session-over-absolute-limit"),
        )
        approval = client.post(
            f"/api/v1/live-trading/sessions/{requested.json()['sessionId']}/approve",
            headers=headers("risk-token"),
            json={"reason": "must be blocked by absolute limit"},
        )
        assert approval.status_code == 422
        assert "absolute limit" in str(approval.json()["detail"])

        monkeypatch.setattr(settings, "live_session_absolute_max_order_notional", 1000)
        kill_switch = client.put(
            "/api/v1/risk/kill-switches/global/*",
            headers=headers("risk-token"),
            json={
                "idempotencyKey": "global-kill-session-test",
                "enabled": True,
                "reason": "block live session approval",
                "actor": "risk-1",
            },
        )
        assert kill_switch.status_code == 200

        requested_two = client.post(
            "/api/v1/live-trading/sessions",
            headers=headers("trader-token"),
            json=session_payload("session-kill-switch-blocked"),
        )
        approval_two = client.post(
            f"/api/v1/live-trading/sessions/{requested_two.json()['sessionId']}/approve",
            headers=headers("risk-token"),
            json={"reason": "must be blocked by kill switch"},
        )
        assert approval_two.status_code == 422
        assert "Kill Switch" in str(approval_two.json()["detail"])
