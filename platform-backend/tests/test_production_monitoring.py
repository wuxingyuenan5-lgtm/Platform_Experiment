import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.eod_reconciliation import ensure_schema as ensure_eod_schema
from app.main import app
from app.venue_reconciliation import ensure_schema as ensure_reconciliation_schema

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


class FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "fake failure",
                request=httpx.Request("GET", "http://runtime.test"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, object]:
        return self._payload


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
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "production-monitoring.db"))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(
        settings,
        "auth_credentials_json",
        json.dumps(
            [
                credential("viewer-1", "viewer-token", ["viewer"]),
                credential("risk-1", "risk-token", ["risk_officer"]),
                credential("operations-1", "operations-token", ["operations"]),
            ]
        ),
    )


def fake_runtime_get(url: str, **kwargs) -> FakeResponse:
    if url.endswith("/status"):
        return FakeResponse(
            {
                "status": "ok",
                "service": "execution-runtime",
                "environment": "live",
                "gateway": "bybit_mt5",
            }
        )
    if url.endswith("/gateway/venue-readiness"):
        return FakeResponse({"status": "not_connected", "venues": []})
    if url.endswith("/gateway/connectivity"):
        return FakeResponse(
            {
                "gateway": "bybit_mt5",
                "credentialCount": 1,
                "configuredCredentialCount": 0,
                "credentials": [
                    {
                        "credentialRef": "secret://environment/bybit-live-001",
                        "provider": "environment",
                        "secretName": "bybit-live-001",
                        "version": "unversioned",
                        "configured": False,
                        "availableFields": [],
                        "missingFields": ["API_KEY", "SECRET"],
                    }
                ],
            }
        )
    return FakeResponse({"status": "not_connected"}, status_code=503)


def seed_blocking_conditions() -> None:
    ensure_reconciliation_schema()
    ensure_eod_schema()
    now = datetime.now(UTC)
    with connection() as db:
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side,
                order_type, quantity, price, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "unknown-order-1",
                "unknown-command-1",
                ACCOUNT_ID,
                INSTRUMENT_ID,
                "BTCUSDT",
                "buy",
                "limit",
                "0.01",
                "100",
                "result_unknown",
                now.isoformat(),
                now.isoformat(),
            ),
        )
        db.execute(
            """
            INSERT INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id,
                account_id, run_type, source, status, order_count, fill_count,
                position_count, balance_count, fact_count, difference_count,
                started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "reconciliation-run-1",
                "reconciliation-run-key-1",
                "hash",
                STRATEGY_ID,
                ACCOUNT_ID,
                "full",
                "fake",
                "completed_with_differences",
                1,
                0,
                0,
                0,
                0,
                1,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        db.execute(
            """
            INSERT INTO reconciliation_differences (
                id, run_id, difference_key, difference_type, entity_type,
                local_reference, external_reference, local_value_json,
                external_value_json, status, resolution_actor,
                resolution_reason, resolved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)
            """,
            (
                "difference-1",
                "reconciliation-run-1",
                "missing-external-order-1",
                "missing_external",
                "order",
                "unknown-order-1",
                None,
                "{}",
                "{}",
                "open",
                now.isoformat(),
            ),
        )
        db.execute(
            """
            INSERT INTO eod_reconciliation_reports (
                id, idempotency_key, natural_key, payload_hash,
                business_date, timezone, valuation_time,
                strategy_instance_id, account_id, actor, owner, due_at,
                status, scale_gate_status, order_reconciliation_count,
                account_reconciliation_run_id, economic_event_import_id,
                nav_snapshot_id, formal_pnl_count,
                formal_pnl_incomplete_count, open_difference_count,
                resolved_difference_count, accepted_difference_count,
                skipped_external_ids_json, missing_account_ids_json,
                errors_json, review_payload_hash, reviewer, review_decision,
                review_reason, reviewed_at, created_at, completed_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, NULL
            )
            """,
            (
                "eod-overdue-1",
                "eod-overdue-key-1",
                "eod-overdue-natural-key-1",
                "hash",
                now.date().isoformat(),
                "UTC",
                now.isoformat(),
                STRATEGY_ID,
                ACCOUNT_ID,
                "operations-1",
                "operations-1",
                (now - timedelta(minutes=30)).isoformat(),
                "partial",
                "blocked",
                1,
                "reconciliation-run-1",
                None,
                None,
                0,
                0,
                1,
                0,
                0,
                json.dumps([]),
                json.dumps([ACCOUNT_ID]),
                json.dumps(["runtime query incomplete"]),
                now.isoformat(),
            ),
        )


def test_status_alert_dedup_and_lifecycle(monkeypatch, tmp_path: Path) -> None:
    configure_live(monkeypatch, tmp_path)
    monkeypatch.setattr("app.production_monitoring.httpx.get", fake_runtime_get)
    with TestClient(app) as client:
        seed_blocking_conditions()

        status = client.get(
            "/api/v1/ops/production-status",
            headers=headers("risk-token"),
        )
        assert status.status_code == 200
        status_body = status.json()
        assert status_body["status"] == "critical"
        assert status_body["risk"]["resultUnknownOrderCount"] == 1
        assert status_body["reconciliation"]["openDifferenceCount"] == 1
        assert status_body["eod"]["overdue"] is True

        viewer_status = client.get(
            "/api/v1/ops/production-status",
            headers=headers("viewer-token"),
        )
        assert viewer_status.status_code == 403

        first = client.post(
            "/api/v1/ops/alerts/scan",
            headers=headers("operations-token"),
            json={"idempotencyKey": "scan-001", "owner": "operations-1"},
        )
        assert first.status_code == 200
        categories = {item["category"] for item in first.json()}
        assert {
            "venue_unavailable",
            "credential_reference_unavailable",
            "result_unknown_orders",
            "open_reconciliation_differences",
            "eod_overdue",
            "eod_not_clean",
        }.issubset(categories)

        replay = client.post(
            "/api/v1/ops/alerts/scan",
            headers=headers("operations-token"),
            json={"idempotencyKey": "scan-001", "owner": "operations-1"},
        )
        assert replay.status_code == 200
        assert replay.json() == first.json()

        second = client.post(
            "/api/v1/ops/alerts/scan",
            headers=headers("operations-token"),
            json={"idempotencyKey": "scan-002", "owner": "operations-1"},
        )
        assert second.status_code == 200
        result_unknown_alert = next(
            item for item in second.json() if item["category"] == "result_unknown_orders"
        )
        assert result_unknown_alert["occurrenceCount"] == 2

        alert_id = result_unknown_alert["alertId"]
        acknowledged = client.post(
            f"/api/v1/ops/alerts/{alert_id}/acknowledge",
            headers=headers("risk-token"),
            json={"reason": "reconciliation owner assigned", "owner": "risk-1"},
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["status"] == "acknowledged"
        assert acknowledged.json()["acknowledgedBy"] == "risk-1"

        closed = client.post(
            f"/api/v1/ops/alerts/{alert_id}/close",
            headers=headers("operations-token"),
            json={"reason": "test lifecycle closure"},
        )
        assert closed.status_code == 200
        assert closed.json()["status"] == "closed"
        assert closed.json()["closedBy"] == "operations-1"

        viewer_alerts = client.get(
            "/api/v1/ops/alerts",
            headers=headers("viewer-token"),
        )
        assert viewer_alerts.status_code == 403


def test_controlled_scheduler_accepts_only_fixed_operations(monkeypatch, tmp_path: Path) -> None:
    configure_live(monkeypatch, tmp_path)
    monkeypatch.setattr("app.production_monitoring.httpx.get", fake_runtime_get)
    with TestClient(app) as client:
        scheduled_for = datetime.now(UTC).isoformat()
        scheduled = client.post(
            "/api/v1/ops/controlled-operations",
            headers=headers("operations-token"),
            json={
                "idempotencyKey": "controlled-health-001",
                "taskType": "health_scan",
                "scheduledFor": scheduled_for,
                "payload": {"owner": "operations-1"},
            },
        )
        assert scheduled.status_code == 200
        assert scheduled.json()["status"] == "completed"
        assert scheduled.json()["taskType"] == "health_scan"

        replay = client.post(
            "/api/v1/ops/controlled-operations",
            headers=headers("operations-token"),
            json={
                "idempotencyKey": "controlled-health-001",
                "taskType": "health_scan",
                "scheduledFor": scheduled_for,
                "payload": {"owner": "operations-1"},
            },
        )
        assert replay.status_code == 200
        assert replay.json()["runId"] == scheduled.json()["runId"]

        forbidden_task = client.post(
            "/api/v1/ops/controlled-operations",
            headers=headers("operations-token"),
            json={
                "idempotencyKey": "controlled-trade-forbidden",
                "taskType": "trade",
                "scheduledFor": datetime.now(UTC).isoformat(),
                "payload": {},
            },
        )
        assert forbidden_task.status_code == 422
