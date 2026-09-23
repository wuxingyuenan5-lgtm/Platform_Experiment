"""Bound SQLite observational history to the platform's documented read model.

The live tables keep full recent observations, hourly observations for the last
14 days, and daily observations for the last 400 days. This is an operational
history compaction only; orders, fills, financial facts and research archives
are outside its scope.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

TABLES = {
    "market_spread_snapshots": {
        "time": "observed_at",
        "partition": "strategy_key,strategy_instance_id",
    },
    "account_risk_snapshots": {
        "time": "as_of",
        "partition": "account_id,currency,asset_scope",
    },
    "balance_snapshots": {
        "time": "as_of",
        "partition": "account_id,currency",
    },
    "account_valuation_rates": {
        "time": "as_of",
        "partition": "account_id,currency",
    },
}


def counts(db: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in TABLES
    }


def verify_database_backup(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"backup database not found: {path}")
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise SystemExit(f"backup integrity check failed: {integrity}")
        return {
            "path": str(path),
            "integrity": integrity,
            "migration": db.execute("SELECT max(version) FROM schema_migrations").fetchone()[0],
            "counts": counts(db),
        }
    finally:
        db.close()


def compact(db: sqlite3.Connection, now: datetime) -> None:
    hourly = (now - timedelta(days=14)).isoformat()
    daily = (now - timedelta(days=400)).isoformat()
    for table, spec in TABLES.items():
        time_column = spec["time"]
        partition = spec["partition"]
        tie_breaker = (
            "julianday(created_at) DESC, rowid DESC"
            if table != "account_valuation_rates"
            else "julianday(as_of) DESC, rowid DESC"
        )
        db.execute(
            f"DELETE FROM {table} WHERE julianday({time_column}) < julianday(?)",
            (daily,),
        )
        for floor, bucket in ((hourly, "%Y-%m-%d %H"), (daily, "%Y-%m-%d") ):
            db.execute(
                f"""
                WITH ranked AS (
                    SELECT rowid,
                           ROW_NUMBER() OVER (
                               PARTITION BY {partition}, strftime(?, {time_column})
                               ORDER BY julianday({time_column}) DESC, {tie_breaker}
                           ) AS rank
                    FROM {table}
                    WHERE julianday({time_column}) < julianday(?)
                      AND julianday({time_column}) >= julianday(?)
                )
                DELETE FROM {table}
                WHERE rowid IN (SELECT rowid FROM ranked WHERE rank > 1)
                """,
                (bucket, floor, daily if bucket.endswith("%d") else hourly),
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-backup", type=Path, required=True)
    parser.add_argument(
        "--database", type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "platform.db",
    )
    args = parser.parse_args()
    database = args.database.resolve()
    backup = args.database_backup.resolve()
    before_backup = verify_database_backup(backup)
    if not database.is_file():
        raise SystemExit(f"database not found: {database}")

    db = sqlite3.connect(database, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    before_size = database.stat().st_size
    try:
        before_integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if before_integrity != "ok":
            raise SystemExit(
                "database integrity check failed before compaction: "
                f"{before_integrity}"
            )
        before = counts(db)
        db.execute("BEGIN IMMEDIATE")
        compact(db, datetime.now(UTC))
        db.commit()
        db.execute("VACUUM")
        after_integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if after_integrity != "ok":
            raise SystemExit(f"database integrity check failed after compaction: {after_integrity}")
        after = counts(db)
        preserved = {
            table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("orders", "fills", "financial_facts", "research_strategy_parts")
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
        }
    finally:
        db.close()

    after_size = database.stat().st_size
    print(json.dumps({
        "database": str(database),
        "databaseBackup": before_backup,
        "beforeBytes": before_size,
        "afterBytes": after_size,
        "reclaimedBytes": before_size - after_size,
        "before": before,
        "after": after,
        "preserved": preserved,
        "integrity": "ok",
        "policy": {
            "fullRecentDays": 1,
            "hourlyDays": 14,
            "dailyDays": 400,
        },
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
