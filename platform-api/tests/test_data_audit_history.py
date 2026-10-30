from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app import data_audit_history as history
from app.database import connection, database_path, initialize_database


@pytest.fixture
def store():
    initialize_database()


def put(day, close, *, fetched="2026-10-30T00:00:00+00:00", db=None):
    sql = (
        "INSERT INTO research_a_share_history VALUES('stock',?,'600519',?,'fixture',?,NULL) "
        "ON CONFLICT(dataset,observed_at,entity_code) DO UPDATE SET "
        "payload_json=excluded.payload_json,fetched_at=excluded.fetched_at"
    )
    args = (day, '{"close":' + str(close) + "}", fetched)
    if db is not None:
        db.execute(sql, args)
    else:
        with connection() as db:
            db.execute(sql, args)


def test_changes_include_old_revisions_and_recover_without_full_scan(store):
    now = datetime.now(UTC)
    put("2020-01-01", 10)
    put("2026-10-29", 20)
    first = history.inspect_changes(now, batch_size=1)
    assert first["processed"] == 1 and first["pending"]
    assert history.inspect_changes(now)["status"] == "healthy"
    # An old-day correction is found even though the latest date has not moved.
    put("2020-01-01", -1)
    invalid = history.inspect_changes(now)
    assert invalid["status"] == "error"
    assert invalid["findings"][0]["observed_at"] == "2020-01-01"
    # The finding stays open across a run with no changes.
    assert history.inspect_changes(now)["status"] == "error"
    put("2020-01-01", 11)
    assert history.inspect_changes(now)["status"] == "healthy"
    with connection() as db:
        db.execute("DELETE FROM research_a_share_history WHERE observed_at='2020-01-01'")
    assert history.inspect_changes(now)["deleted"] == 1


def test_transaction_rollback_and_fetch_only_touch_do_not_create_false_changes(store):
    now = datetime.now(UTC)
    with pytest.raises(RuntimeError), connection() as db:
        put("2026-10-28", -1, db=db)
        raise RuntimeError("rollback")
    assert history.inspect_changes(now)["processed"] == 0
    put("2026-10-28", 10)
    history.inspect_changes(now)
    put("2026-10-28", 10, fetched="2026-10-30T01:00:00+00:00")
    assert history.inspect_changes(now)["processed"] == 0


def test_failed_incremental_write_keeps_queue_and_cursor(store, monkeypatch):
    put("2026-10-28", 10)
    # The audit must defer instead of holding business writes for 30 seconds.
    import sqlite3

    db = sqlite3.connect(database_path())
    db.execute("BEGIN IMMEDIATE")
    result = history.inspect_changes(datetime.now(UTC))
    assert result["status"] == "warning"
    db.rollback()
    db.close()
    assert history.inspect_changes(datetime.now(UTC))["processed"] == 1


def test_full_audit_is_readonly_for_business_data_and_reports_scope(store, tmp_path):
    put("2020-01-01", -1)
    with connection() as db:
        before = db.execute("SELECT payload_json FROM research_a_share_history").fetchone()[0]
    result = history.full_audit(database_path(), tmp_path / "audit")
    assert result["complete"] and result["status"] == "error"
    assert result["checkedRows"] == 1
    assert result["invalidRows"] == {"stock": 1}
    assert result["integrity"] == [["ok"]]
    assert Path(result["snapshot"]).resolve() != database_path().resolve()
    with connection() as db:
        assert (
            db.execute("SELECT payload_json FROM research_a_share_history").fetchone()[0] == before
        )
        assert db.execute("SELECT count(*) FROM data_audit_history_changes").fetchone()[0] == 1
    # A failed subsequent copy must not turn the prior invalid baseline healthy.
    failed = history.full_audit(database_path(), tmp_path / "audit", copy_seconds=-1)
    assert not failed["complete"] and failed["status"] == "warning"
    assert failed["lastComplete"]["invalidRows"] == {"stock": 1}
    accepted = Path(result["snapshot"]).read_bytes()
    put("2020-01-01", 10)
    failed_scan = history.full_audit(database_path(), tmp_path / "audit", scan_seconds=-1)
    assert not failed_scan["complete"]
    assert Path(result["snapshot"]).read_bytes() == accepted
    assert failed_scan["lastComplete"]["invalidRows"] == {"stock": 1}


def test_full_schedule_is_weekly_at_night_and_failed_attempts_do_not_spin():
    now = datetime(2026, 10, 30, 19, 30, tzinfo=UTC)  # 03:30 Shanghai
    assert history.full_audit_due(now, None)
    assert not history.full_audit_due(now + timedelta(hours=6), None)
    report = dict(startedAt=(now - timedelta(hours=1)).isoformat(), complete=False)
    assert not history.full_audit_due(now, report)
    report = dict(
        startedAt=(now - timedelta(days=2)).isoformat(),
        complete=True,
        finishedAt=(now - timedelta(days=2)).isoformat(),
    )
    assert not history.full_audit_due(now, report)
    assert history.full_audit_due(now + timedelta(days=7), report)


def test_published_returns_are_recomputed_and_gaps_not_filled(store):
    import json

    days = [(datetime(2026, 9, 1) + timedelta(days=i)).date().isoformat() for i in range(21)]
    for i, day in enumerate(days):
        put(day, 100 + i)
    stock = dict(
        code="600519",
        status="ready",
        history_date=days[-1],
        change_5d=120 / 115 - 1,
        change_20d=0.2,
    )
    with connection() as db:
        db.execute(
            "INSERT INTO data_audit_calendar VALUES('CN',?,?,?)",
            ("2026-10-30T00:00:00+00:00", json.dumps(days), "fixture"),
        )
        db.execute(
            "INSERT INTO research_a_share_dataset_snapshots "
            "(dataset,fetched_at,status,source,payload_json) "
            "VALUES('stock_pool',?,'ready','fixture',?)",
            ("2026-10-30T00:00:00+00:00", json.dumps(dict(stocks=[stock]))),
        )
    assert history.inspect_stock_returns()["checked"] == 2
    assert history.inspect_stock_returns()["status"] == "healthy"
    # Alter an earlier price: unchanged published returns must be detected.
    put(days[0], 50)
    result = history.inspect_stock_returns()
    assert result["status"] == "error" and result["samples"][0]["field"] == "change_20d"
    with connection() as db:
        db.execute("DELETE FROM research_a_share_history WHERE observed_at=?", (days[0],))
    assert history.inspect_stock_returns()["samples"][0]["reason"] == "missing_input"


def test_copy_replays_concurrent_revision_delete_and_insert_after_base_copy(
    store, tmp_path, monkeypatch
):
    put("2020-01-01", 10)
    put("2020-01-02", 20)
    publish = history._publish
    changed = False

    def revise(directory, report):
        nonlocal changed
        publish(directory, report)
        if (
            report.get("tableCopyWindows", {}).get("research_a_share_history", {}).get("finishedAt")
            and not changed
        ):
            changed = True
            put("2020-01-01", -1)
            with connection() as db:
                db.execute("DELETE FROM research_a_share_history WHERE observed_at='2020-01-02'")
            put("2020-01-03", 30)
            # Consuming live checks must not remove the copy reader's recent journal.
            history.inspect_changes(datetime.now(UTC))

    monkeypatch.setattr(history, "_publish", revise)
    result = history.full_audit(database_path(), tmp_path / "copy")
    assert result["complete"] and result["checkedRows"] == 2
    assert result["invalidRows"] == {"stock": 1}
    import sqlite3

    with sqlite3.connect(result["snapshot"]) as db:
        assert [
            r[0]
            for r in db.execute(
                "SELECT observed_at FROM research_a_share_history ORDER BY observed_at"
            )
        ] == ["2020-01-01", "2020-01-03"]
        assert db.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchone() is None


def test_copy_includes_refresh_provenance_added_during_replay(store, tmp_path, monkeypatch):
    publish = history._publish
    changed = False

    def revise(directory, report):
        nonlocal changed
        publish(directory, report)
        if (
            report.get("tableCopyWindows", {})
            .get("research_a_share_refresh_runs", {})
            .get("finishedAt")
            and not changed
        ):
            changed = True
            with connection() as db:
                db.execute(
                    "INSERT INTO research_a_share_refresh_runs VALUES "
                    "('new-run','2026-10-29','2026-10-30T00:00:00Z',NULL,'running',NULL,NULL)"
                )
                db.execute(
                    "INSERT INTO research_a_share_history VALUES "
                    "('stock','2026-10-29','600519','{\"close\":10}',"
                    "'fixture','2026-10-30T00:00:00Z','new-run')"
                )

    monkeypatch.setattr(history, "_publish", revise)
    result = history.full_audit(database_path(), tmp_path / "provenance")
    assert changed and result["complete"]
    assert result["checkedRows"] == 1 and result["foreignKeyViolations"] == []


def test_single_full_worker_lock_prevents_duplicate_copy(store, tmp_path):
    directory = tmp_path / "locked"
    with history._worker_lock(directory) as acquired:
        assert acquired
        assert history.full_audit(database_path(), directory) == {"status": "busy"}


def test_copy_read_retries_only_busy_with_a_deadline(monkeypatch):
    import sqlite3
    import time

    busy = sqlite3.OperationalError("database is locked")
    busy.sqlite_errorcode = sqlite3.SQLITE_BUSY
    attempts = 0

    def read():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise busy
        return [1]

    monkeypatch.setattr(history.time, "sleep", lambda _: None)
    assert history._copy_read(read, time.monotonic() + 1) == [1]
    assert attempts == 2
    with pytest.raises(TimeoutError):
        history._copy_read(read, time.monotonic() - 1)
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        history._copy_read(
            lambda: (_ for _ in ()).throw(sqlite3.OperationalError("no such table")),
            time.monotonic() + 1,
        )


@pytest.mark.parametrize("foreign_source", [False, True])
def test_persisted_baseline_does_not_hide_failure_or_validate_another_database(
    store, monkeypatch, foreign_source
):
    from app import data_audit as audit

    now = datetime.now(UTC).isoformat()
    source = str(database_path())
    baseline = dict(
        source=source,
        status="error",
        complete=True,
        finishedAt=now,
        integrity=[["ok"]],
        foreignKeyViolations=[],
    )
    report = dict(
        source=str(database_path().parent / "other.db") if foreign_source else source,
        status="warning",
        complete=False,
        lastComplete=baseline,
    )
    monkeypatch.setattr(history, "read_full_report", lambda: report)
    monkeypatch.setattr(history, "inspect_changes", lambda _: dict(status="healthy"))
    monkeypatch.setattr(history, "inspect_stock_returns", lambda: dict(status="healthy"))
    for name in ("inspect_database", "inspect_runtime", "inspect_artifacts"):
        monkeypatch.setattr(audit, name, lambda _: [])
    monkeypatch.setattr(audit, "persist_report", lambda checks, _: checks)
    result = {c["key"]: c for c in audit.run_audit()}
    assert result["history.full"]["status"] == ("warning" if foreign_source else "error")
    assert result["database.integrity"]["status"] == ("warning" if foreign_source else "healthy")
