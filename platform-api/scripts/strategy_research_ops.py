"""Local research preflight and verified backup. Does not enable connectivity or trading."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.database_connection import connection
from app.strategy_research_repository import assert_sqlite_safe, backup, verify_backup

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["check", "backup", "verify-backup"])
parser.add_argument("--destination", type=Path)
args = parser.parse_args()

if args.action == "check":
    settings = get_settings()
    with connection() as db:
        assert_sqlite_safe(db)
        migration = db.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
        print(
            json.dumps(
                {
                    "sqliteVersion": sqlite3.sqlite_version,
                    "migration": migration,
                    "journalMode": db.execute("PRAGMA journal_mode").fetchone()[0],
                    "synchronous": db.execute("PRAGMA synchronous").fetchone()[0],
                    "liveWrite": settings.live_trading_enabled,
                    "researchEnabled": settings.strategy_research_enabled,
                    "database": str(Path(settings.database_path).resolve()),
                    "archive": str(Path(settings.strategy_research_path).resolve()),
                }
            )
        )
        if settings.live_trading_enabled:
            raise SystemExit("Live Write is active; research startup must not change trading mode")
elif args.action == "backup":
    if args.destination is None:
        parser.error("--destination is required")
    print(json.dumps(backup(args.destination.resolve())))
else:
    if args.destination is None:
        parser.error("--destination is required")
    print(json.dumps(verify_backup(args.destination)))
