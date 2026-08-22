import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import permission_for_request
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


def configure_live_auth(monkeypatch, tmp_path: Path) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "auth-rbac.db"))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(
        settings,
        "auth_credentials_json",
        json.dumps(
            [
                credential("viewer-1", "viewer-token", ["viewer"]),
                credential("risk-1", "risk-token", ["risk_officer"]),
                credential("admin-1", "admin-token", ["admin"]),
            ]
        ),
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Request-ID": "test-request-id"}


def assert_auth_error(response, *, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    payload = response.json()
    assert payload["detail"]["code"] == code
    assert payload["detail"]["message"]
    assert payload["requestId"] == response.headers["x-request-id"]


def test_live_environment_rejects_anonymous_and_invalid_credentials(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_live_auth(monkeypatch, tmp_path)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

        anonymous = client.get("/api/v1/system/info")
        assert_auth_error(anonymous, status_code=401, code="bearer_required")
        assert anonymous.headers["www-authenticate"] == "Bearer"

        invalid = client.get(
            "/api/v1/system/info",
            headers=auth_headers("wrong-token"),
        )
        assert_auth_error(invalid, status_code=401, code="credential_invalid")

        valid = client.get(
            "/api/v1/system/info",
            headers=auth_headers("viewer-token"),
        )
        assert valid.status_code == 200
        assert valid.headers["x-authenticated-user"] == "viewer-1"
        assert valid.headers["x-request-id"] == "test-request-id"


def test_rbac_is_default_deny_for_trading_and_audit(monkeypatch, tmp_path: Path) -> None:
    configure_live_auth(monkeypatch, tmp_path)
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
        assert_auth_error(trading, status_code=403, code="permission_denied")

        audit = client.get(
            "/api/v1/ops/audit-events",
            headers=auth_headers("viewer-token"),
        )
        assert_auth_error(audit, status_code=403, code="permission_denied")

        admin_audit = client.get(
            "/api/v1/ops/audit-events",
            headers=auth_headers("admin-token"),
        )
        assert admin_audit.status_code == 200


def test_live_api_admin_is_not_a_ceo_trade_authority(monkeypatch, tmp_path: Path) -> None:
    configure_live_auth(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/funding/market-command",
            headers=auth_headers("admin-token"),
            json={
                "action": "OPEN_SHORT_PERP_LONG_SPOT",
                "perpetualSymbol": "BTCUSDT",
                "spotSymbol": "BTCUSDC",
                "quantity": "0.01",
            },
        )

    assert_auth_error(response, status_code=403, code="ceo_trade_authority_required")


def test_strategy_market_commands_use_ceo_browser_permission_boundary() -> None:
    assert (
        permission_for_request("POST", "/api/v1/trading/funding/market-command") == "trading.write"
    )


def test_instruction_post_uses_strategy_permission_and_ceo_trade_boundary() -> None:
    assert (
        permission_for_request(
            "POST",
            "/api/v1/strategies/strategy_funding_arbitrage_instance_default/instructions",
        )
        == "strategy:run"
    )


def test_live_api_admin_cannot_bypass_funding_gate_through_generic_command(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_live_auth(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/commands",
            headers=auth_headers("admin-token"),
            json={
                "idempotencyKey": "admin-funding-generic-command",
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

    assert_auth_error(response, status_code=403, code="ceo_trade_authority_required")
    assert (
        permission_for_request("POST", "/api/v1/trading/cross-spread/market-command")
        == "trading.write"
    )


def test_live_actor_field_cannot_impersonate_another_user(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_live_auth(monkeypatch, tmp_path)
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
        assert_auth_error(mismatch, status_code=403, code="request_identity_mismatch")
        assert "must match the authenticated user" in mismatch.json()["detail"]["message"]

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


def test_live_environment_refuses_development_auth_mode(monkeypatch, tmp_path: Path) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "unsafe-auth-mode.db"))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "development")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    with TestClient(app) as client:
        response = client.get("/api/v1/system/info")
        assert_auth_error(response, status_code=503, code="live_auth_mode_required")
        assert "requires api_key" in response.json()["detail"]["message"]
