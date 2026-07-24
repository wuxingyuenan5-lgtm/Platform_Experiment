from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from app.database import connection

LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
"""


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...] = ()

    @property
    def checksum(self) -> str:
        payload = json.dumps(
            {
                "version": self.version,
                "name": self.name,
                "statements": self.statements,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Version 1 records the schema that already existed before the ledger was introduced.
# It is intentionally a no-op: existing tables, indexes, columns and seed identifiers
# remain owned by their current modules until a dedicated migration is reviewed.
PLATFORM_MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="existing-platform-schema-baseline"),
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def validate_migrations(migrations: tuple[Migration, ...]) -> None:
    versions = [migration.version for migration in migrations]
    names = [migration.name for migration in migrations]
    if versions != sorted(versions) or len(versions) != len(set(versions)):
        raise RuntimeError("Schema migration versions must be unique and strictly ordered")
    if len(names) != len(set(names)):
        raise RuntimeError("Schema migration names must be unique")
    if any(version <= 0 for version in versions):
        raise RuntimeError("Schema migration versions must be positive integers")


def apply_migrations(
    db: sqlite3.Connection,
    migrations: tuple[Migration, ...] = PLATFORM_MIGRATIONS,
) -> None:
    validate_migrations(migrations)
    db.executescript(LEDGER_SQL)

    for migration in migrations:
        existing = db.execute(
            "SELECT name, checksum FROM schema_migrations WHERE version = ?",
            (migration.version,),
        ).fetchone()
        if existing is not None:
            if existing["name"] != migration.name or existing["checksum"] != migration.checksum:
                raise RuntimeError(
                    f"Schema migration {migration.version} changed after it was applied"
                )
            continue

        for statement in migration.statements:
            db.execute(statement)
        db.execute(
            """
            INSERT INTO schema_migrations (version, name, checksum, applied_at)
            VALUES (?, ?, ?, ?)
            """,
            (migration.version, migration.name, migration.checksum, utc_now_iso()),
        )


def apply_platform_migrations() -> None:
    with connection() as db:
        apply_migrations(db)


def list_applied_migrations() -> list[dict[str, object]]:
    with connection() as db:
        db.executescript(LEDGER_SQL)
        rows = db.execute(
            """
            SELECT version, name, checksum, applied_at
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()
    return [
        {
            "version": int(row["version"]),
            "name": row["name"],
            "checksum": row["checksum"],
            "appliedAt": row["applied_at"],
        }
        for row in rows
    ]
