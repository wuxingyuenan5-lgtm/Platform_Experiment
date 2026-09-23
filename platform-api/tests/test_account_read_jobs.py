from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from test_live_venue_snapshot_sync import StubResponse, base_snapshot

from app.account_history_sync import _merge_history, sync_account_history
from app.account_read_jobs import financial_sync_state, record_job
from app.config import get_settings
from app.database import connection, initialize_database
from app.live_venue_snapshot_sync import _persist_venue_snapshot, sync_venue_snapshots


def history_payload(start: str, end: str, *, quality: str = "complete") -> dict:
    return {
        "historyStart": start,
        "historyEnd": end,
        "economicEventsQuality": quality,
        "fills": [],
        "economicEvents": [],
        "orders": [],
    }


def bootstrap(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "account-read-jobs.db")
    initialize_database()


def test_financial_sync_state_recovers_after_failed_job(tmp_path: Path) -> None:
    bootstrap(tmp_path)

    account = "bybit-live-main"
    record_job(account, "history", "ready")
    record_job(account, "settlements", "failed", "RuntimeError")
    with connection() as db:
        failed = financial_sync_state(db, account)
    assert failed["financialSyncStatus"] == "failed"
    assert failed["financialSyncErrorCode"] == "settlements:RuntimeError"

    record_job(account, "settlements", "ready")
    with connection() as db:
        recovered = financial_sync_state(db, account)
    assert recovered["financialSyncStatus"] == "ready"
    assert recovered["financialSyncErrorCode"] is None


def test_current_snapshot_remains_ready_when_settlement_projection_fails(
    monkeypatch, tmp_path: Path
) -> None:
    bootstrap(tmp_path)
    account = "bybit-live-main"
    snapshot = base_snapshot(account)
    snapshot["economicEventsQuality"] = "complete"
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(snapshot),
    )
    monkeypatch.setattr(
        "app.funding_settlement_accounting.sync_funding_settlements",
        lambda account_id: (_ for _ in ()).throw(RuntimeError("settlement unavailable")),
    )
    monkeypatch.setattr("app.account_performance.sync_capital_history", lambda account_id: None)

    result = sync_venue_snapshots(account)

    assert result.overall_status == "synced"
    with connection() as db:
        current = db.execute(
            "SELECT status, error_code FROM account_sync_status WHERE account_id=?",
            (account,),
        ).fetchone()
        state = financial_sync_state(db, account)
    assert dict(current) == {"status": "ready", "error_code": None}
    assert state["financialSyncStatus"] == "failed"
    assert state["financialSyncErrorCode"] == "settlements:RuntimeError"


def test_merge_history_deduplicates_overlap_and_retains_seven_day_coverage() -> None:
    previous = history_payload("2026-09-01T00:00:00+00:00", "2026-09-08T00:00:00+00:00")
    previous["fills"] = [
        {"source": "venue", "externalFillId": "old", "occurredAt": "2026-09-07T00:00:00+00:00"},
        {"source": "venue", "externalFillId": "overlap", "occurredAt": "2026-09-08T00:00:00+00:00"},
    ]
    incoming = history_payload("2026-09-07T23:50:00+00:00", "2026-09-09T00:00:00+00:00")
    incoming["fills"] = [
        {"source": "venue", "externalFillId": "overlap", "occurredAt": "2026-09-08T00:00:00+00:00"},
        {"source": "venue", "externalFillId": "new", "occurredAt": "2026-09-09T00:00:00+00:00"},
    ]

    merged = _merge_history(previous, incoming, incremental=True)

    assert merged["historyStart"] == "2026-09-02T00:00:00+00:00"
    assert {row["externalFillId"] for row in merged["fills"]} == {"old", "overlap", "new"}

    full = _merge_history(previous, incoming, incremental=False)
    assert full["historyStart"] == incoming["historyStart"]
    assert [row["externalFillId"] for row in full["fills"]] == ["overlap", "new"]


def test_merge_history_does_not_claim_coverage_for_gap_or_unavailable_window() -> None:
    previous = history_payload("2026-09-01T00:00:00+00:00", "2026-09-08T00:00:00+00:00")
    previous["fills"] = [
        {"source": "venue", "externalFillId": "old", "occurredAt": "2026-09-07T00:00:00+00:00"}
    ]
    gap = history_payload("2026-09-09T00:00:00+00:00", "2026-09-10T00:00:00+00:00")
    gap["fills"] = [
        {"source": "venue", "externalFillId": "gap", "occurredAt": "2026-09-09T00:00:00+00:00"}
    ]
    unavailable = history_payload(
        "2026-09-07T00:00:00+00:00", "2026-09-09T00:00:00+00:00", quality="unavailable"
    )

    gap_result = _merge_history(previous, gap, incremental=True)
    unavailable_result = _merge_history(previous, unavailable, incremental=True)

    assert gap_result["historyStart"] == gap["historyStart"]
    assert [row["externalFillId"] for row in gap_result["fills"]] == ["gap"]
    assert unavailable_result["historyStart"] == unavailable["historyStart"]
    assert unavailable_result["economicEventsQuality"] == "unavailable"


def test_merge_history_older_response_cannot_replace_newer_history() -> None:
    previous = history_payload("2026-09-01T00:00:00+00:00", "2026-09-10T00:00:00+00:00")
    previous["fills"] = [
        {"source": "venue", "externalFillId": "new", "occurredAt": "2026-09-10T00:00:00+00:00"}
    ]
    older = history_payload("2026-09-01T00:00:00+00:00", "2026-09-09T00:00:00+00:00")
    older["fills"] = [
        {"source": "venue", "externalFillId": "old", "occurredAt": "2026-09-09T00:00:00+00:00"}
    ]

    assert _merge_history(previous, older, incremental=True) == previous


def test_incremental_history_request_uses_last_end_and_retains_audit_timestamp(
    monkeypatch, tmp_path: Path
) -> None:
    bootstrap(tmp_path)
    account = "bybit-live-main"
    now = datetime.now(UTC).replace(microsecond=0)
    end = now - timedelta(minutes=30)
    start = end - timedelta(days=6)
    audit = now - timedelta(hours=1)
    prior = base_snapshot(account)
    prior.update(
        historyStart=start.isoformat(),
        historyEnd=end.isoformat(),
        historyAuditAt=audit.isoformat(),
        economicEventsQuality="complete",
    )
    with connection() as db:
        _persist_venue_snapshot(db, account, prior)

    captured: dict[str, object] = {}
    incoming = base_snapshot(account)
    incoming.update(
        historyStart=(end - timedelta(minutes=10)).isoformat(),
        historyEnd=now.isoformat(),
        economicEventsQuality="complete",
    )

    def fake_runtime_get(path, params=None):
        captured.update(params or {})
        return StubResponse(incoming)

    monkeypatch.setattr("app.account_history_sync.runtime_get", fake_runtime_get)
    monkeypatch.setattr("app.account_history_sync._sync_account_finance", lambda account_id: None)
    sync_account_history(account)

    assert captured["historyStart"] == (end - timedelta(minutes=10)).isoformat()
    with connection() as db:
        payload = json.loads(
            db.execute(
                "SELECT payload_json FROM account_venue_snapshots WHERE account_id=?", (account,)
            ).fetchone()[0]
        )
    assert payload["historyAuditAt"] == audit.isoformat()


def test_mt5_future_history_end_uses_observed_time_and_retains_window_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    bootstrap(tmp_path)
    account = "account_mt5_short_term_a"
    now = datetime.now(UTC).replace(microsecond=0)
    observed = now - timedelta(hours=1)
    audit = now - timedelta(minutes=20)
    window_seconds = 30 * 86400
    prior = base_snapshot(account)
    prior["venue"] = "mt5"
    prior.update(
        historyStart=(observed - timedelta(seconds=window_seconds)).isoformat(),
        historyEnd=(now + timedelta(days=1)).isoformat(),
        historyObservedAt=observed.isoformat(),
        historyAuditAt=audit.isoformat(),
        historyWindowSeconds=window_seconds,
        economicEventsQuality="complete",
    )
    with connection() as db:
        _persist_venue_snapshot(db, account, prior)

    captured: dict[str, object] = {}
    incoming = base_snapshot(account)
    incoming.update(
        historyStart=(observed - timedelta(days=1, minutes=10)).isoformat(),
        historyEnd=(now + timedelta(days=1, hours=1)).isoformat(),
        economicEventsQuality="complete",
        asOf=now.isoformat(),
    )

    def fake_runtime_get(path, params=None):
        captured.update(params or {})
        return StubResponse(incoming)

    monkeypatch.setattr("app.account_history_sync.runtime_get", fake_runtime_get)
    monkeypatch.setattr("app.account_history_sync._sync_account_finance", lambda account_id: None)
    sync_account_history(account)

    expected_start = (observed - timedelta(days=1, minutes=10)).isoformat()
    assert captured["historyStart"] == expected_start
    assert datetime.fromisoformat(str(captured["historyStart"])) <= now
    with connection() as db:
        payload = json.loads(
            db.execute(
                "SELECT payload_json FROM account_venue_snapshots WHERE account_id=?", (account,)
            ).fetchone()[0]
        )
    assert payload["historyWindowSeconds"] == window_seconds
    assert payload["historyAuditAt"] == audit.isoformat()
    assert payload["historyObservedAt"] == incoming["asOf"]
