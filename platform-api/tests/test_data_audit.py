from datetime import UTC, datetime, timedelta

import pytest

from app import data_audit as audit
from app.database_connection import connection


@pytest.fixture
def store():
    from app.database import initialize_database

    initialize_database()
    audit.ensure_alert_schema()


def test_freshness_requires_timezone_and_detects_stopped_and_future_data():
    now = datetime.now(UTC)
    for timestamp in [
        None,
        "2026-01-01",
        (now - timedelta(hours=3)).isoformat(),
        (now + timedelta(hours=1)).isoformat(),
    ]:
        assert audit.freshness("x", "x", "x", timestamp, 2, now)["status"] == "error"
    assert audit.freshness("x", "x", "x", now.isoformat(), 2, now)["status"] == "healthy"


def test_missing_crowding_turnover_and_absent_day_are_not_zero():
    payload = {
        "history": [
            {
                "date": "2026-09-22",
                "targets": {
                    str(n): {
                        "code": code,
                        "amount100m": 1,
                        "amountShareOfA": 0.1,
                        "turnoverPct": None if n == 0 else 2,
                    }
                    for n, code in enumerate(["801102", "801101", "801083", "801081"])
                },
            }
        ]
    }
    rows = audit.crowding_checks(payload, {"2026-09-22", "2026-09-23"})
    assert rows[0]["status"] == "error"
    assert rows[0]["evidence"]["invalidDates"] == ["2026-09-22"]
    assert rows[0]["evidence"]["missingDates"] == ["2026-09-23"]
    assert rows[1]["status"] == "error"


def test_alert_dedup_recovery_reopen_and_restart_read(store):
    now = datetime.now(UTC)
    item = audit.check("x", "test", "test", "error", "stopped")
    audit.persist_report([item], now)
    audit.persist_report([item], now + timedelta(seconds=1))
    report = audit.read_report()
    assert len(report["alerts"]) == 1
    assert report["alerts"][0]["occurrence_count"] == 2
    audit.persist_report([audit.check("x", "test", "test")], now + timedelta(seconds=2))
    assert audit.read_report()["alerts"][0]["status"] == "closed"
    audit.persist_report([item], now + timedelta(seconds=3))
    assert audit.read_report()["alerts"][0]["status"] == "open"


def test_auditor_stall_is_not_healthy(store):
    audit.persist_report([], datetime.now(UTC) - timedelta(minutes=20))
    assert audit.read_report()["monitorStale"]


def test_received_status_does_not_hide_stale_source():
    now = datetime.now(UTC)
    assert (
        audit.source_check(
            "mt5",
            {"status": "received", "lastRangeTickCount": 2, "lastReadAt": now.isoformat()},
            now,
        )["status"]
        == "healthy"
    )
    assert (
        audit.source_check(
            "bybit",
            {"status": "received", "lastReceivedAt": (now - timedelta(days=1)).isoformat()},
            now,
        )["status"]
        == "error"
    )
    assert audit.source_check("mt5", {"status": "empty_range"}, now)["status"] == "warning"
    assert (
        audit.source_check(
            "mt5:XAUUSD",
            {
                "status": "deferred",
                "reason": "research_yielded_to_account_operations",
                "lastReadAt": now.isoformat(),
            },
            now,
        )["status"]
        == "info"
    )
    assert (
        audit.source_check(
            "mt5:XAUUSD",
            {
                "status": "deferred",
                "reason": "research_yielded_to_account_operations",
                "lastReadAt": (now - timedelta(minutes=16)).isoformat(),
            },
            now,
        )["status"]
        == "error"
    )
    assert (
        audit.source_check(
            "history",
            {"status": "up_to_date", "lastReceivedAtMs": str(int(now.timestamp() * 1000))},
            now,
        )["status"]
        == "healthy"
    )


def test_absent_or_unverified_check_cannot_close_alert(store):
    now = datetime.now(UTC)
    audit.persist_report([audit.check("source.x", "x", "x", "error")], now)
    audit.persist_report([], now + timedelta(minutes=5))
    report = audit.read_report()
    assert report["checks"][0]["status"] == "warning"
    assert report["alerts"][0]["status"] == "open"
    assert report["alerts"][0]["occurrence_count"] == 1
    audit.persist_report([audit.check("source.x", "x", "x", "info")], now + timedelta(minutes=10))
    assert audit.read_report()["alerts"][0]["status"] == "open"


def test_daily_results_survive_light_scan(store):
    now = datetime.now(UTC)
    audit.persist_report([audit.check("database.integrity", "integrity", "db")], now)
    audit.persist_report([audit.check("x", "x", "db")], now + timedelta(minutes=5))
    retained = next(r for r in audit.read_report()["checks"] if r["key"] == "database.integrity")
    assert retained["checkedAt"] == now.isoformat()


def test_scan_error_is_visible_and_does_not_refresh_sources(store, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("broken schema")

    monkeypatch.setattr(audit, "inspect_database", broken)
    monkeypatch.setattr(audit, "inspect_runtime", lambda now: [])
    monkeypatch.setattr(audit, "inspect_artifacts", lambda now: [])
    result = audit.run_audit()
    assert result["checks"][0]["status"] == "error"
    assert result["checks"][0]["key"] == "database.scan"


def test_http_internal_roles_only(store):
    from fastapi.testclient import TestClient

    from app.application import create_application
    from app.database import initialize_database
    from scripts.user_demo_seed import seed_demo_users

    initialize_database()
    accounts = seed_demo_users(password="data audit isolated password", prefix="audit")
    app = create_application()
    for role in ["ceo", "employee", "member"]:
        client = TestClient(app)
        account = next(row for row in accounts if row.role == role)
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "http://127.0.0.1:4373"},
            json={"username": account.username, "password": "data audit isolated password"},
        )
        assert response.status_code == 200
        response = client.get("/api/v1/risk/data-audit")
        assert response.status_code == (403 if role == "member" else 200)


def test_independent_calendar_finds_whole_missing_day(store):
    import json

    from app.database import initialize_database

    initialize_database()
    with connection() as db:
        db.execute(
            "INSERT INTO data_audit_calendar VALUES('CN',?,?,?)",
            (
                "2026-09-24T08:00:00+00:00",
                json.dumps(["2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"]),
                "isolated-calendar",
            ),
        )
        for day in ["2026-09-22", "2026-09-24"]:
            db.execute(
                "INSERT INTO research_a_share_history "
                "VALUES('market',?,'market','{}','fixture',?,NULL)",
                (day, day + "T08:00:00+00:00"),
            )
    checks = audit.inspect_database(datetime(2026, 9, 24, 9, tzinfo=UTC))
    row = next(c for c in checks if c["key"] == "calendar.gaps.market")
    assert row["evidence"]["missingDates"] == ["2026-09-23"]
    assert row["status"] == "error"


def test_financial_units_missingness_and_valid_empty_day():
    assert not audit.history_row_valid(
        "macro_fedwatch", "meeting", {"probabilities": {"hold": 4200}}
    )
    assert audit.history_row_valid(
        "macro_fedwatch", "meeting", {"probabilities": {"hold": 42, "cut": 58}}
    )
    assert not audit.history_row_valid(
        "market", "market", {"totalAmountYuan": 0, "up": 1, "down": 1, "flat": 0}
    )
    assert audit.history_row_valid("hot_stock", "__day__", {})
