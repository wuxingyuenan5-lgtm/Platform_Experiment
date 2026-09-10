import hashlib
import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry, generate_latest

from app.application import app
from app.config import get_settings
from app.database import connection, initialize_database
from app.execution_risk_repository import ensure_schema as ensure_risk_schema
from app.operational_metrics import OperationalCollector


def collect():
    registry = CollectorRegistry()
    registry.register(OperationalCollector())
    return generate_latest(registry).decode()


def test_scrape_missing_database_does_not_create_files(monkeypatch, tmp_path):
    target = tmp_path / "not-created" / "platform.db"
    monkeypatch.setattr(get_settings(), "database_path", str(target))
    assert "vg_platform_metrics_snapshot_available 0.0" in collect()
    assert not target.parent.exists()


def test_scrape_reads_existing_snapshot_without_writes_or_financial_labels(monkeypatch, tmp_path):
    target = tmp_path / "metrics.db"
    monkeypatch.setattr(get_settings(), "database_path", str(target))
    initialize_database()
    stamp = (datetime.now(UTC) - timedelta(seconds=120)).isoformat()
    with connection() as db:
        db.execute(
            "INSERT INTO strategy_runs "
            "(id,idempotency_key,strategy_instance_id,strategy_key,direction,status,"
            "created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                "secret-instruction-id",
                "secret-identity",
                "strategy_funding_arbitrage_instance_default",
                "funding_arbitrage",
                "long",
                "reconciling",
                stamp,
                stamp,
            ),
        )
        db.execute(
            "INSERT INTO account_sync_status "
            "(account_id,status,last_success_at,updated_at) VALUES (?,?,?,?)",
            ("account_sim_usdt", "error", stamp, stamp),
        )
    before = target.read_bytes()
    output = collect()
    expected = 'vg_platform_pending_instructions{state="reconciling",strategy="funding_arbitrage"}'
    assert f"{expected} 1.0" in output
    assert "secret-instruction" not in output
    assert "account_sim_usdt" not in output
    assert "vg_platform_account_sync_oldest_success_seconds" in output
    assert "NaN" in output  # No source snapshot is unavailable, never fabricated age zero.
    assert target.read_bytes() == before
    assert "vg_platform_metrics_risk_store_available 0.0" in output
    ensure_risk_schema()
    assert "vg_platform_metrics_risk_store_available 1.0" in collect()


def test_metrics_use_existing_audit_read_permission(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "auth.db"))
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "environment", "live")
    credentials = [
        {
            "credentialId": role,
            "userId": role,
            "roles": [role],
            "status": "active",
            "tokenSha256": hashlib.sha256(role.encode()).hexdigest(),
        }
        for role in ("viewer", "risk_officer")
    ]
    monkeypatch.setattr(settings, "auth_credentials_json", json.dumps(credentials))
    initialize_database()
    client = TestClient(app)  # No lifespan: no runner or external refresh starts.
    assert client.get("/api/v1/ops/metrics").status_code == 401
    assert (
        client.get("/api/v1/ops/metrics", headers={"Authorization": "Bearer viewer"}).status_code
        == 403
    )
    response = client.get("/api/v1/ops/metrics", headers={"Authorization": "Bearer risk_officer"})
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
