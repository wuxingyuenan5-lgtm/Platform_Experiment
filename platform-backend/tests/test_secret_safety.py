from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection, initialize_database
from app.main import app


def test_credential_references_expose_metadata_without_secret_material(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "credentials.db")

    with TestClient(app) as client:
        response = client.get("/api/v1/security/credential-references")

        assert response.status_code == 200
        body = response.json()
        assert {item["credentialRef"] for item in body} >= {
            "secret://crypto-test-001",
            "secret://crypto-test-002",
            "secret://mt5-demo-001",
        }
        serialized = str(body).lower()
        assert "apikey" not in serialized
        assert "api_key" not in serialized
        assert "secretkey" not in serialized
        assert "passphrase" not in serialized


def test_live_account_order_is_blocked_when_global_live_switch_is_disabled(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "live-guard.db")
    settings.live_trading_enabled = False
    initialize_database()
    seed_live_account_for_test()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/orders",
            json={
                "accountId": "account_live_guard",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65000",
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "Live trading is disabled by global safety switch"
        )


def test_all_accounts_must_be_active_before_order_submission(tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "live-account-status.db")
    settings.live_trading_enabled = True
    initialize_database()
    seed_live_account_for_test(status="paused")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/orders",
            json={
                "accountId": "account_live_guard",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65000",
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Account is not active"


def seed_live_account_for_test(status: str = "active") -> None:
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO credential_references (
                id, credential_ref, venue_id, environment, purpose, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "credential_live_guard",
                "secret://live-guard",
                "venue_crypto",
                "live",
                "trading",
                "active",
                "2026-07-20T00:00:00+00:00",
            ),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO accounts (
                id, venue_id, account_code, name, account_type, environment, base_currency,
                credential_ref, status, data_quality_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "account_live_guard",
                "venue_crypto",
                "LIVE-GUARD-001",
                "Live Guard Account",
                "crypto",
                "live",
                "USDT",
                "secret://live-guard",
                status,
                "partial",
                "2026-07-20T00:00:00+00:00",
            ),
        )
