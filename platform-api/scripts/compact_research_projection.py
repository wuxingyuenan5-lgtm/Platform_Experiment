"""Safely clear and compact the rebuildable strategy research projection.

The projection is a serving cache generated from the sealed Parquet catalog. It
is intentionally kept out of the long-running trading API. This maintenance
command requires a verified backup before changing the business database and
never deletes the source catalog or the backup.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.strategy_research_repository import verify_backup

PROJECTION_SCHEMA = (
    """CREATE TABLE research_strategy_projection (
        kind TEXT NOT NULL, entity TEXT NOT NULL, at_ms INTEGER NOT NULL,
        payload_json TEXT NOT NULL, PRIMARY KEY(kind,entity,at_ms)
    ) WITHOUT ROWID""",
    """CREATE TABLE research_strategy_projection_cursor (
        id INTEGER PRIMARY KEY CHECK(id=1), part_rowid INTEGER NOT NULL,
        state_json TEXT NOT NULL, updated_at TEXT NOT NULL
    )""",
)
PRESERVED_TABLES = (
    "orders",
    "fills",
    "financial_facts",
    "research_strategy_parts",
    "research_strategy_capture",
    "research_strategy_experiments",
)


def _count(db: sqlite3.Connection, table: str) -> int | None:
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is None:
        return None
    return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backup", type=Path, required=True,
        help="Verified backup directory created by strategy_research_ops.py",
    )
    parser.add_argument(
        "--database", type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "platform.db",
    )
    args = parser.parse_args()
    backup = args.backup.resolve()
    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"database not found: {database}")

    backup_result = verify_backup(backup)
    before_size = database.stat().st_size
    db = sqlite3.connect(database, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    try:
        before_integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if before_integrity != "ok":
            raise SystemExit(
                "database integrity check failed before maintenance: "
                f"{before_integrity}"
            )
        before = {
            "projection": _count(db, "research_strategy_projection"),
            "cursor": _count(db, "research_strategy_projection_cursor"),
            "preserved": {table: _count(db, table) for table in PRESERVED_TABLES},
        }
        db.execute("BEGIN IMMEDIATE")
        db.execute("DROP TABLE IF EXISTS research_strategy_projection")
        db.execute("DROP TABLE IF EXISTS research_strategy_projection_cursor")
        for statement in PROJECTION_SCHEMA:
            db.execute(statement)
        db.commit()
        db.execute("VACUUM")
        after_integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if after_integrity != "ok":
            raise SystemExit(
                "database integrity check failed after maintenance: "
                f"{after_integrity}"
            )
        after = {
            "projection": _count(db, "research_strategy_projection"),
            "cursor": _count(db, "research_strategy_projection_cursor"),
            "preserved": {table: _count(db, table) for table in PRESERVED_TABLES},
        }
    finally:
        db.close()

    after_size = database.stat().st_size
    print(json.dumps({
        "database": str(database),
        "backup": str(backup),
        "backupVerification": backup_result,
        "beforeBytes": before_size,
        "afterBytes": after_size,
        "reclaimedBytes": before_size - after_size,
        "before": before,
        "after": after,
        "integrity": "ok",
        "sourceCatalogPreserved": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
