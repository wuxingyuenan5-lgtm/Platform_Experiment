"""Bounded history change checks and isolated, low-priority snapshot audits."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.database_connection import database_path

RULE_DATASETS = {"market", "hot_stock", "index", "stock", "macro_fedwatch"}
BATCH_SIZE = 500
FULL_INTERVAL = timedelta(days=7)


def audit_directory() -> Path:
    return database_path().parent / "audits"


def validate_record(dataset, entity, raw):
    from app.data_audit import history_row_valid

    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return "payload_not_object"
        if not history_row_valid(dataset, entity, payload):
            return "invalid_required_fields"
    except (ValueError, TypeError, AttributeError):
        return "invalid_payload"
    return None


def inspect_changes(now: datetime, *, batch_size=BATCH_SIZE):
    """Read a bounded batch; findings and cursor commit atomically, or neither."""
    stamp = now.isoformat()
    db = sqlite3.connect(database_path(), timeout=0.25)
    db.row_factory = sqlite3.Row
    deadline = time.monotonic() + 1
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    try:
        cursor = db.execute("SELECT * FROM data_audit_history_cursor WHERE id=1").fetchone()
        last_seq = cursor["last_seq"] if cursor else 0
        events = db.execute(
            "SELECT c.seq,c.dataset,c.observed_at,c.entity_code,c.operation,h.payload_json "
            "FROM data_audit_history_changes c LEFT JOIN research_a_share_history h "
            "ON h.dataset=c.dataset AND h.observed_at=c.observed_at "
            "AND h.entity_code=c.entity_code "
            "WHERE c.seq>? ORDER BY c.seq LIMIT ?",
            (last_seq, batch_size),
        ).fetchall()
        inspected = []
        unsupported = set()
        for row in events:
            if time.monotonic() > deadline:
                break
            problem = (
                validate_record(row["dataset"], row["entity_code"], row["payload_json"])
                if row["payload_json"] is not None
                else None
            )
            inspected.append((row, problem))
            if row["dataset"] not in RULE_DATASETS:
                unsupported.add(row["dataset"])
        # Never hold a business write transaction while parsing history payloads.
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "INSERT OR IGNORE INTO data_audit_history_cursor VALUES(1,0,?,?)",
            (stamp, stamp),
        )
        for row, problem in inspected:
            key = (row["dataset"], row["observed_at"], row["entity_code"])
            if problem:
                db.execute(
                    "INSERT INTO data_audit_history_findings VALUES(?,?,?,?,?) "
                    "ON CONFLICT(dataset,observed_at,entity_code) DO UPDATE SET "
                    "problem=excluded.problem,checked_at=excluded.checked_at",
                    (*key, problem, stamp),
                )
            else:
                db.execute(
                    "DELETE FROM data_audit_history_findings "
                    "WHERE dataset=? AND observed_at=? AND entity_code=?",
                    key,
                )
        if inspected:
            end = inspected[-1][0]["seq"]
            db.execute(
                "DELETE FROM data_audit_history_changes WHERE seq IN "
                "(SELECT seq FROM data_audit_history_changes WHERE seq<=? AND changed_at<? "
                "ORDER BY seq LIMIT 1000)",
                (end, (now - timedelta(days=7)).isoformat()),
            )
            db.execute(
                "UPDATE data_audit_history_cursor SET last_seq=?,checked_at=? WHERE id=1",
                (end, stamp),
            )
        db.commit()
        findings = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM data_audit_history_findings LIMIT 21",
            ).fetchall()
        ]
        state = dict(db.execute("SELECT * FROM data_audit_history_cursor WHERE id=1").fetchone())
        pending = (
            db.execute(
                "SELECT 1 FROM data_audit_history_changes WHERE seq>? LIMIT 1",
                (state["last_seq"],),
            ).fetchone()
            is not None
        )
        return dict(
            status="error" if findings else "warning" if pending or unsupported else "healthy",
            processed=len(inspected),
            pending=pending,
            findings=findings[:20],
            moreFindings=len(findings) > 20,
            startedAt=state["started_at"],
            checkedAt=stamp,
            lastSequence=state["last_seq"],
            deleted=sum(r["operation"] == "delete" for r, _ in inspected),
            scope="changes_since_installation",
            batchLimit=batch_size,
            ruleDatasets=sorted(RULE_DATASETS),
            datasetsWithoutFieldRules=sorted(unsupported),
        )
    except sqlite3.Error as exc:
        db.rollback()
        return dict(
            status="warning",
            reason=type(exc).__name__,
            detail=str(exc),
            scope="changes_not_verified",
        )
    finally:
        db.close()


def inspect_stock_returns():
    """Recompute published mainland 5/20-session returns from bounded input windows."""
    db = sqlite3.connect(f"file:{database_path()}?mode=ro", uri=True, timeout=0.25)
    deadline = time.monotonic() + 1
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    checked, skipped, errors = 0, 0, []
    try:
        row = db.execute(
            "SELECT payload_json FROM research_a_share_dataset_snapshots "
            "WHERE dataset='stock_pool'",
        ).fetchone()
        if not row:
            return dict(status="warning", reason="stock_pool_unavailable")
        payload = json.loads(row[0])
        calendar_row = db.execute(
            "SELECT days_json FROM data_audit_calendar WHERE market='CN'"
        ).fetchone()
        if not calendar_row:
            return dict(status="warning", reason="independent_calendar_unavailable")
        days = sorted(json.loads(calendar_row[0]))
        stocks = [r for r in payload.get("stocks", []) if len(str(r.get("code", ""))) == 6]
        if not stocks:
            return dict(status="warning", reason="no_mainland_stocks")
        for stock in stocks[:200]:
            if time.monotonic() > deadline:
                break
            day = stock.get("history_date")
            if stock.get("status") != "ready" or not day:
                skipped += 2
                continue
            prices = {
                r[0]: Decimal(str(json.loads(r[1])["close"]))
                for r in db.execute(
                    "SELECT observed_at,payload_json FROM research_a_share_history "
                    "WHERE dataset='stock' AND entity_code=? AND observed_at<=? "
                    "ORDER BY observed_at DESC LIMIT 21",
                    (stock["code"], day),
                ).fetchall()
            }
            for n, field in [(5, "change_5d"), (20, "change_20d")]:
                window = [d for d in days if d <= day][-n - 1 :]
                if len(window) != n + 1 or any(d not in prices for d in window):
                    skipped += 1
                    if stock.get(field) is not None:
                        errors.append(dict(code=stock["code"], field=field, reason="missing_input"))
                    continue
                expected = prices[window[-1]] / prices[window[0]] - 1
                actual = stock.get(field)
                checked += 1
                if actual is None or abs(expected - Decimal(str(actual))) > Decimal("0.00000001"):
                    errors.append(
                        dict(code=stock["code"], field=field, expected=str(expected), actual=actual)
                    )
        return dict(
            status="error"
            if errors
            else "warning"
            if skipped or checked + skipped < 2 * len(stocks)
            else "healthy",
            checked=checked,
            unavailable=skipped,
            targetChecks=2 * len(stocks),
            samples=errors[:20],
            scope="published_mainland_pool_5d_20d",
            stockLimit=200,
        )
    except (
        sqlite3.Error,
        ValueError,
        TypeError,
        KeyError,
        InvalidOperation,
        ZeroDivisionError,
    ) as exc:
        return dict(
            status="warning",
            reason=type(exc).__name__,
            detail=str(exc),
            checked=checked,
            scope="not_fully_verified",
        )
    finally:
        db.close()


def read_full_report(directory: Path | None = None):
    try:
        return json.loads(
            ((directory or audit_directory()) / "history-full.json").read_text("utf-8")
        )
    except FileNotFoundError:
        return None


def _publish(directory, report):
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "history-full.json"
    temp = directory / f"history-full-{uuid4().hex}.tmp"
    temp.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    temp.replace(target)


@contextmanager
def _worker_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "history-full.lock").open("a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                yield False
                return
        else:
            import fcntl

            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                yield False
                return
        try:
            yield True
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _copy_read(read, deadline):
    """Retry only transient source contention, without retaining a read transaction."""
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("snapshot_copy_budget_exceeded")
        try:
            return read()
        except sqlite3.OperationalError as exc:
            code = getattr(exc, "sqlite_errorcode", 0) & 255
            if code not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                raise
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))


def copy_research_snapshot(source, temp, directory, report, seconds):
    """Copy owned tables; replay value changes to a short, consistent history cutoff."""
    tables = (
        "research_a_share_history",
        "data_audit_calendar",
        "research_a_share_market_archive",
        "research_a_share_price_history",
        "research_a_share_archive_conflicts",
        "research_a_share_refresh_runs",
    )
    deadline = time.monotonic() + seconds
    if temp.exists():
        with closing(sqlite3.connect(temp)) as old:
            old.execute("PRAGMA schema_version").fetchone()
        temp.unlink()  # Only this worker's fixed unfinished scratch file.
    with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=0.25)) as live:
        live.row_factory = sqlite3.Row
        live.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)

        def read(sql, params=()):
            return _copy_read(lambda: live.execute(sql, params).fetchall(), deadline)

        if not any(
            r[1] == "changed_at" for r in read("PRAGMA table_info(data_audit_history_changes)")
        ):
            raise ValueError("retained_change_journal_required")
        marker = read("SELECT seq FROM sqlite_sequence WHERE name='data_audit_history_changes'")
        start_seq = marker[0][0] if marker else 0
        windows = {}
        with closing(sqlite3.connect(temp)) as dest:
            for table in tables:
                report["copyTable"] = table
                _publish(directory, report)
                windows[table] = dict(startedAt=datetime.now(UTC).isoformat())
                schema = read(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
                )
                dest.execute(schema[0][0])
                columns = [r[1] for r in read(f'PRAGMA table_info("{table}")')]
                select_columns = ",".join('"' + c + '"' for c in columns)
                insert = (
                    f'INSERT OR REPLACE INTO "{table}"({select_columns}) VALUES ('
                    + ",".join("?" for _ in columns)
                    + ")"
                )
                last = None
                copied = 0
                while True:
                    rows = read(
                        f'SELECT rowid,{select_columns} FROM "{table}" '
                        + ("WHERE rowid>? " if last is not None else "")
                        + "ORDER BY rowid LIMIT 1000",
                        (last,) if last is not None else (),
                    )
                    if not rows:
                        break
                    dest.executemany(insert, [tuple(r)[1:] for r in rows])
                    dest.commit()
                    last = rows[-1][0]
                    copied += len(rows)
                    if time.monotonic() > deadline:
                        raise TimeoutError("snapshot_copy_budget_exceeded")
                    time.sleep(0.005)
                windows[table].update(finishedAt=datetime.now(UTC).isoformat(), copiedRows=copied)
                report.update(copyTable=table, tableCopyWindows=windows)
                _publish(directory, report)
            last_seq = start_seq

            def read_tail():
                live.execute("BEGIN")
                try:
                    marker = live.execute(
                        "SELECT seq FROM sqlite_sequence WHERE name='data_audit_history_changes'"
                    ).fetchone()
                    cutoff = marker[0] if marker else 0
                    events = live.execute(
                        "SELECT c.seq,c.dataset,c.observed_at,c.entity_code,"
                        "h.payload_json,h.source,h.fetched_at,h.refresh_run_id "
                        "FROM data_audit_history_changes c LEFT JOIN research_a_share_history h "
                        "ON h.dataset=c.dataset AND h.observed_at=c.observed_at "
                        "AND h.entity_code=c.entity_code WHERE c.seq>? AND c.seq<=? "
                        "ORDER BY c.seq LIMIT 501",
                        (last_seq, cutoff),
                    ).fetchall()
                    run_ids = {r[7] for r in events[:500] if r[7] is not None}
                    runs = (
                        live.execute(
                            "SELECT * FROM research_a_share_refresh_runs WHERE run_id IN ("
                            + ",".join("?" for _ in run_ids)
                            + ")",
                            tuple(run_ids),
                        ).fetchall()
                        if run_ids
                        else []
                    )
                finally:
                    live.rollback()
                return cutoff, events, runs

            while True:
                cutoff, events, runs = _copy_read(read_tail, deadline)
                if runs:
                    dest.executemany(
                        "INSERT OR REPLACE INTO research_a_share_refresh_runs "
                        "VALUES(?,?,?,?,?,?,?)",
                        [tuple(r) for r in runs],
                    )
                for row in events[:500]:
                    key = tuple(row)[1:4]
                    if row[4] is None:
                        dest.execute(
                            "DELETE FROM research_a_share_history "
                            "WHERE dataset=? AND observed_at=? AND entity_code=?",
                            key,
                        )
                    else:
                        dest.execute(
                            "INSERT OR REPLACE INTO research_a_share_history VALUES(?,?,?,?,?,?,?)",
                            tuple(row)[1:],
                        )
                    last_seq = row[0]
                dest.commit()
                if len(events) <= 500:
                    report.update(
                        historyCutoffSequence=cutoff,
                        snapshotAt=datetime.now(UTC).isoformat(),
                        copyScope="research_tables",
                        fetchMetadataAtCopyTime=True,
                    )
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("snapshot_replay_budget_exceeded")
                time.sleep(0.005)


def full_audit(source: Path, directory: Path, *, copy_seconds=600, scan_seconds=1200):
    """Copy owned research data with replay; all full scans run on the copy."""
    source, directory = source.resolve(), directory.resolve()
    if not source.is_file() or source in (
        directory / "history-full.sqlite",
        directory / "history-copy.sqlite",
    ):
        raise ValueError("audit_snapshot_must_be_separate_from_existing_source")
    with _worker_lock(directory) as acquired:
        if not acquired:
            return {"status": "busy"}
        previous = read_full_report(directory) or {}
        retained = previous.get("lastComplete")
        if previous.get("complete"):
            retained = {k: v for k, v in previous.items() if k != "lastComplete"}
        report = dict(
            status="running",
            phase="copy",
            complete=False,
            startedAt=datetime.now(UTC).isoformat(),
            snapshotId=uuid4().hex,
            source=str(source),
            scope="research_history_and_research_snapshot_structure",
            lastComplete=retained,
        )
        _publish(directory, report)
        try:
            temp = directory / "history-copy.sqlite"
            copy_research_snapshot(source, temp, directory, report, copy_seconds)
            target = directory / "history-full.sqlite"
            report.update(phase="scan", snapshot=str(temp))
            _publish(directory, report)
            deadline = time.monotonic() + scan_seconds
            counts, invalid, unsupported, samples = {}, {}, set(), []
            with closing(sqlite3.connect(f"file:{temp}?mode=ro", uri=True)) as db:
                db.row_factory = sqlite3.Row
                db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
                db.execute("PRAGMA cache_size=-8192")
                integrity = [list(r) for r in db.execute("PRAGMA quick_check(10)").fetchall()]
                foreign_keys = [
                    list(r) for r in db.execute("PRAGMA foreign_key_check").fetchmany(20)
                ]
                report.update(integrity=integrity, foreignKeyViolations=foreign_keys)
                from app.data_audit import a_share_archive_check

                report["sourceArchiveCheck"] = a_share_archive_check(db)
                last = None
                while True:
                    rows = db.execute(
                        "SELECT rowid,dataset,entity_code,observed_at,payload_json "
                        "FROM research_a_share_history "
                        + ("WHERE rowid>? " if last is not None else "")
                        + "ORDER BY rowid LIMIT 1000",
                        (last,) if last is not None else (),
                    ).fetchall()
                    if not rows:
                        break
                    for rowid, dataset, entity, observed, raw in rows:
                        counts[dataset] = counts.get(dataset, 0) + 1
                        if dataset not in RULE_DATASETS:
                            unsupported.add(dataset)
                        problem = validate_record(dataset, entity, raw)
                        if problem:
                            invalid[dataset] = invalid.get(dataset, 0) + 1
                            if len(samples) < 20:
                                samples.append(
                                    dict(
                                        dataset=dataset,
                                        entity=entity,
                                        date=observed,
                                        problem=problem,
                                    )
                                )
                        last = rowid
                    if time.monotonic() > deadline:
                        raise TimeoutError("snapshot_scan_budget_exceeded")
                    time.sleep(0.005)
            temp.replace(target)
            report.update(
                snapshot=str(target),
                complete=True,
                phase="done",
                status="error"
                if invalid
                or integrity != [["ok"]]
                or foreign_keys
                or report["sourceArchiveCheck"]["status"] == "error"
                else "warning"
                if unsupported or report["sourceArchiveCheck"]["status"] == "warning"
                else "healthy",
                counts=counts,
                checkedRows=sum(counts.values()),
                invalidRows=invalid,
                samples=samples,
                ruleDatasets=sorted(RULE_DATASETS),
                datasetsWithoutFieldRules=sorted(unsupported),
                finishedAt=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:
            logging.getLogger(__name__).exception("Research snapshot audit did not complete")
            report.update(
                status="warning",
                complete=False,
                phase="failed",
                errorType=type(exc).__name__,
                reason=str(exc)[:160],
                finishedAt=datetime.now(UTC).isoformat(),
            )
        _publish(directory, report)
        return report


def full_audit_due(now, report):
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    if not 3 <= local.hour < 5:
        return False
    if report:
        started = datetime.fromisoformat(report["startedAt"])
        if started.astimezone(ZoneInfo("Asia/Shanghai")).date() >= local.date():
            return False
        baseline = report if report.get("complete") else report.get("lastComplete")
        if baseline and now - datetime.fromisoformat(baseline["finishedAt"]) < FULL_INTERVAL:
            return False
    return True


def launch_full_audit_if_due(now):
    if not full_audit_due(now, read_full_report()):
        return False
    directory = audit_directory()
    directory.mkdir(parents=True, exist_ok=True)
    flags = (
        (subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        if os.name == "nt"
        else 0
    )
    with (directory / "history-full.log").open("ab") as log:
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "app.data_audit_history",
                "--source",
                str(database_path().resolve()),
                "--directory",
                str(directory.resolve()),
            ],
            cwd=Path(__file__).resolve().parents[1],
            stdout=log,
            stderr=log,
            creationflags=flags,
            close_fds=True,
        )
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if os.name != "nt":
        os.nice(10)
    result = full_audit(args.source, args.directory)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result.get("complete") else 1)
