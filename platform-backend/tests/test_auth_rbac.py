import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def credential(user_id: str, token: str, roles: list[str]) -> dict[str, object]:
    return {
        "credentialId": f"credential-{user_id}",
        "userId": user_id,
        "tokenSha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "roles": roles,
        "status": "active",
    }


def configure_live_auth(tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "auth-rbac.db")
    settings.environment = "live"
    settings.auth_mode = "api_key"
    settings.auth_credentials_json = json.dumps(
        [
            credential("viewer-1", "viewer-token", ["viewer"]),
            credential("risk-1", "risk-token", ["risk_officer"]),
            credential("admin-1", "admin-token", ["admin"]),
        ]
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Request-ID": "test-request-id"}


def test_live_environment_rejects_anonymous_and_invalid_credentials(tmp_path: Path) -> None:
    configure_live_auth(tmp_path)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

        anonymous = client.get("/api/v1/system/info")
        assert anonymous.status_code == 401
        assert anonymous.headers["www-authenticate"] == "Bearer"
        assert anonymous.json()["requestId"]

        invalid = client.get(
            "/api/v1/system/info",
            headers=auth_headers("wrong-token"),
        )
        assert invalid.status_code == 401

        valid = client.get(
            "/api/v1/system/info",
            headers=auth_headers("viewer-token"),
        )
        assert valid.status_code == 200
        assert valid.headers["x-authenticated-user"] == "viewer-1"
        assert valid.headers["x-request-id"] == "test-request-id"


def test_rbac_is_default_deny_for_trading_and_audit(tmp_path: Path) -> None:
    configure_live_auth(tmp_path)
    with TestClient(app) as client:
        trading = client.post(
            "/api/v1/trading/commands",
            headers=auth_headers("viewer-token"),
            json={
                "idempotencyKey": "viewer-must-not-trade",
                "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
                "accountId": "account_sim_usdt",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "100",
            },
        )
        assert trading.status_code == 403

        audit = client.get(
            "/api/v1/ops/audit-events",
            headers=auth_headers("viewer-token"),
        )
        assert audit.status_code == 403

        admin_audit = client.get(
            "/api/v1/ops/audit-events",
            headers=auth_headers("admin-token"),
        )
        assert admin_audit.status_code == 200


def test_live_actor_field_cannot_impersonate_another_user(tmp_path: Path) -> None:
    configure_live_auth(tmp_path)
    with TestClient(app) as client:
        mismatch = client.put(
            "/api/v1/risk/kill-switches/global/*",
            headers=auth_headers("risk-token"),
            json={
                "idempotencyKey": "risk-actor-mismatch",
                "enabled": True,
                "reason": "test actor binding",
                "actor": "somebody-else",
            },
        )
        assert mismatch.status_code == 403
        assert "must match the authenticated user" in mismatch.json()["detail"]

        matching = client.put(
            "/api/v1/risk/kill-switches/global/*",
            headers=auth_headers("risk-token"),
            json={
                "idempotencyKey": "risk-actor-match",
                "enabled": True,
                "reason": "test actor binding",
                "actor": "risk-1",
            },
        )
        assert matching.status_code == 200


def test_live_environment_refuses_development_auth_mode(tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "unsafe-auth-mode.db")
    settings.environment = "live"
    settings.auth_mode = "development"
    settings.auth_credentials_json = "[]"
    with TestClient(app) as client:
        response = client.get("/api/v1/system/info")
        assert response.status_code == 503
        assert "requires api_key" in response.json()["detail"]
