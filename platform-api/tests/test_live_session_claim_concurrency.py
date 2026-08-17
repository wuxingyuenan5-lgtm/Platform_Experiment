import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.live_session_claims import validate_and_claim_live_session_atomic
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"


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


def test_concurrent_claims_ignore_legacy_daily_caps(monkeypatch, tmp_path: Path) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "atomic-live-claims.db"))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(
        settings,
        "auth_credentials_json",
        json.dumps(
            [
                credential("trader-1", "trader-token", ["trader"]),
                credential("risk-1", "risk-token", ["risk_officer"]),
            ]
        ),
    )
    monkeypatch.setattr(settings, "live_trading_enabled", True)
    monkeypatch.setattr(settings, "require_live_trading_session", True)
    monkeypatch.setattr(settings, "live_session_absolute_max_order_notional", 1000)
    monkeypatch.setattr(settings, "live_session_absolute_max_daily_notional", 2000)

    now = datetime.now(UTC)
    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                UPDATE accounts
                SET environment = 'live', account_type = 'live',
                    credential_ref = 'secret://atomic-claim-account', status = 'active'
                WHERE id = ?
                """,
                (ACCOUNT_ID,),
            )

        requested = client.post(
            "/api/v1/live-trading/sessions",
            headers=headers("trader-token"),
            json={
                "idempotencyKey": "atomic-session-001",
                "sessionType": "minimum_size_acceptance",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "symbols": ["BTCUSDT"],
                "sides": ["buy"],
                "orderTypes": ["limit"],
                "startsAt": (now - timedelta(minutes=1)).isoformat(),
                "endsAt": (now + timedelta(hours=1)).isoformat(),
                "maxOrderNotional": "100",
                "maxDailyNotional": "100",
                "readOnlyVerifiedAt": (now - timedelta(minutes=10)).isoformat(),
                "evidenceReference": "ops://readonly-preflight/atomic-001",
                "reason": "both concurrent claims succeed under non-blocking legacy caps",
            },
        )
        assert requested.status_code == 200
        session_id = requested.json()["sessionId"]
        approved = client.post(
            f"/api/v1/live-trading/sessions/{session_id}/approve",
            headers=headers("risk-token"),
            json={"reason": "atomic claim test approved by a separate risk user"},
        )
        assert approved.status_code == 200

    barrier = Barrier(2)

    def claim(command_id: str) -> tuple[str, str | int]:
        barrier.wait()
        try:
            result = validate_and_claim_live_session_atomic(
                command_id=command_id,
                strategy_instance_id=STRATEGY_ID,
                account_id=ACCOUNT_ID,
                symbol="BTCUSDT",
                side="buy",
                order_type="limit",
                quantity=Decimal("0.6"),
                price=Decimal("100"),
            )
            return ("accepted", result)
        except HTTPException as exc:
            return ("rejected", exc.status_code)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ["atomic-command-a", "atomic-command-b"]))

    assert sorted(status for status, _ in results) == ["accepted", "accepted"]
    assert [value for status, value in results if status == "accepted"] == [
        session_id,
        session_id,
    ]

    with connection() as db:
        claims = db.execute(
            "SELECT notional FROM live_trading_session_claims WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    assert sorted(Decimal(row["notional"]) for row in claims) == [
        Decimal("60.0"),
        Decimal("60.0"),
    ]
