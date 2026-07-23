from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import require_principal
from app.config import get_settings
from app.database import connection
from app.redaction import redact_sensitive

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS production_backup_records (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    label TEXT NOT NULL,
    status TEXT NOT NULL,
    destination_directory TEXT NOT NULL,
    manifest_path TEXT,
    files_json TEXT NOT NULL,
    error TEXT,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS production_restore_drills (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    backup_id TEXT NOT NULL,
    label TEXT NOT NULL,
    status TEXT NOT NULL,
    destination_directory TEXT NOT NULL,
    integrity_json TEXT NOT NULL,
    safe_state_json TEXT NOT NULL,
    error TEXT,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(backup_id) REFERENCES production_backup_records(id)
);

CREATE INDEX IF NOT EXISTS idx_production_backups_created
ON production_backup_records(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_restore_drills_created
ON production_restore_drills(created_at DESC);
"""

PLATFORM_TABLES = (
    "audit_events",
    "orders",
    "trade_commands",
    "financial_facts",
    "reconciliation_differences",
    "eod_reconciliation_reports",
    "live_trading_sessions",
)
RUNTIME_TABLES = ("runtime_commands", "runtime_events")
SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class CreateBackupRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    label: str = Field(default="scheduled", min_length=1, max_length=128)


class BackupResponse(BaseModel):
    backup_id: str = Field(alias="backupId")
    idempotency_key: str = Field(alias="idempotencyKey")
    label: str
    status: str
    destination_directory: str = Field(alias="destinationDirectory")
    manifest_path: str | None = Field(default=None, alias="manifestPath")
    files: list[dict[str, object]]
    error: str | None = None
    actor: str
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class CreateRestoreDrillRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    backup_id: str = Field(alias="backupId", min_length=1, max_length=128)
    label: str = Field(default="restore-drill", min_length=1, max_length=128)


class RestoreDrillResponse(BaseModel):
    restore_drill_id: str = Field(alias="restoreDrillId")
    idempotency_key: str = Field(alias="idempotencyKey")
    backup_id: str = Field(alias="backupId")
    label: str
    status: str
    destination_directory: str = Field(alias="destinationDirectory")
    integrity: dict[str, object]
    safe_state: dict[str, object] = Field(alias="safeState")
    error: str | None = None
    actor: str
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def audit(event_type: str, subject_type: str, subject_id: str, details: dict[str, object]) -> None:
    safe_details = redact_sensitive(details)
    with connection() as db:
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                event_type,
                subject_type,
                subject_id,
                json.dumps(safe_details, ensure_ascii=False, sort_keys=True, default=str),
                now_iso(),
            ),
        )


def validate_label(label: str) -> str:
    normalized = label.strip()
    if not SAFE_LABEL.fullmatch(normalized):
        raise HTTPException(
            status_code=422,
            detail="Label may contain only letters, numbers, dot, underscore, and hyphen",
        )
    return normalized


def root_path(raw_path: str) -> Path:
    root = Path(raw_path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def new_child_directory(root: Path, name: str) -> Path:
    target = (root / validate_label(name)).resolve()
    if target.parent != root:
        raise HTTPException(status_code=422, detail="Destination escapes the configured root")
    if target.exists() and any(target.iterdir()):
        raise HTTPException(status_code=409, detail="Destination directory is not empty")
    target.mkdir(parents=False, exist_ok=True)
    return target


def source_database_path(raw_path: str, label: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"{label} source database is unavailable")
    return path


def online_backup(source: Path, destination: Path) -> None:
    if source.resolve() == destination.resolve():
        raise RuntimeError("Backup destination cannot equal the active database")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_db = sqlite3.connect(source)
    destination_db = sqlite3.connect(destination)
    try:
        source_db.backup(destination_db)
        destination_db.commit()
    finally:
        destination_db.close()
        source_db.close()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def database_counts(path: Path, tables: tuple[str, ...]) -> dict[str, int]:
    db = sqlite3.connect(path)
    try:
        available = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        return {
            table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
            if table in available
        }
    finally:
        db.close()


def integrity_result(path: Path) -> str:
    db = sqlite3.connect(path)
    try:
        return str(db.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        db.close()


def file_manifest(
    *,
    logical_name: str,
    path: Path,
    source_file_name: str,
    tables: tuple[str, ...],
) -> dict[str, object]:
    return {
        "logicalName": logical_name,
        "fileName": path.name,
        "sourceFileName": source_file_name,
        "sha256": sha256_file(path),
        "sizeBytes": path.stat().st_size,
        "tableCounts": database_counts(path, tables),
        "integrity": integrity_result(path),
    }


def create_backup(request: CreateBackupRequest, *, actor: str) -> BackupResponse:
    ensure_schema()
    label = validate_label(request.label)
    payload = {"label": label, "actor": actor}
    payload_hash = canonical_hash(payload)

    with connection() as db:
        existing = db.execute(
            "SELECT * FROM production_backup_records WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
    if existing is not None:
        if existing["payload_hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="Backup idempotency key was reused with a different payload",
            )
        return backup_from_row(existing)

    settings = get_settings()
    backup_id = str(uuid4())
    created_at = now_iso()
    directory_name = f"{created_at[:19].replace(':', '')}-{label}-{backup_id[:8]}"
    backup_root = root_path(settings.operations_backup_root)
    destination = new_child_directory(backup_root, directory_name)

    with connection() as db:
        db.execute(
            """
            INSERT INTO production_backup_records (
                id, idempotency_key, payload_hash, label, status,
                destination_directory, manifest_path, files_json, error,
                actor, created_at, completed_at
            ) VALUES (?, ?, ?, ?, 'processing', ?, NULL, '[]', NULL, ?, ?, NULL)
            """,
            (
                backup_id,
                request.idempotency_key,
                payload_hash,
                label,
                str(destination),
                actor,
                created_at,
            ),
        )

    try:
        platform_source = source_database_path(settings.database_path, "Platform")
        runtime_source = source_database_path(settings.runtime_journal_path, "Runtime Journal")
        platform_backup = destination / "platform.db"
        runtime_backup = destination / "runtime_journal.db"
        online_backup(platform_source, platform_backup)
        online_backup(runtime_source, runtime_backup)

        files = [
            file_manifest(
                logical_name="platform_database",
                path=platform_backup,
                source_file_name=platform_source.name,
                tables=PLATFORM_TABLES,
            ),
            file_manifest(
                logical_name="runtime_journal",
                path=runtime_backup,
                source_file_name=runtime_source.name,
                tables=RUNTIME_TABLES,
            ),
        ]
        if any(file["integrity"] != "ok" for file in files):
            raise RuntimeError("SQLite integrity check failed for a backup artifact")

        manifest = {
            "schemaVersion": 1,
            "backupId": backup_id,
            "createdAt": created_at,
            "environment": settings.environment,
            "files": files,
            "safeRestoreDefaults": {
                "platformLiveTradingEnabled": False,
                "runtimeLiveWriteEnabled": False,
                "globalKillSwitchEnabled": True,
            },
        }
        manifest_path = destination / "manifest.json"
        manifest_path.write_text(
            json.dumps(redact_sensitive(manifest), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        completed_at = now_iso()
        with connection() as db:
            db.execute(
                """
                UPDATE production_backup_records
                SET status = 'completed', manifest_path = ?, files_json = ?,
                    completed_at = ?, error = NULL
                WHERE id = ?
                """,
                (
                    str(manifest_path),
                    json.dumps(files, ensure_ascii=False, sort_keys=True),
                    completed_at,
                    backup_id,
                ),
            )
            row = db.execute(
                "SELECT * FROM production_backup_records WHERE id = ?",
                (backup_id,),
            ).fetchone()
        audit(
            "production_backup_completed",
            "production_backup",
            backup_id,
            {
                "backupId": backup_id,
                "label": label,
                "actor": actor,
                "files": [file["logicalName"] for file in files],
            },
        )
        return backup_from_row(row)
    except Exception as exc:
        safe_error = str(redact_sensitive(exc))
        with connection() as db:
            db.execute(
                """
                UPDATE production_backup_records
                SET status = 'failed', error = ?, completed_at = ?
                WHERE id = ?
                """,
                (safe_error, now_iso(), backup_id),
            )
        audit(
            "production_backup_failed",
            "production_backup",
            backup_id,
            {"backupId": backup_id, "label": label, "actor": actor, "error": safe_error},
        )
        raise HTTPException(status_code=500, detail="Production backup failed") from exc


def list_backups() -> list[BackupResponse]:
    ensure_schema()
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM production_backup_records ORDER BY created_at DESC"
        ).fetchall()
    return [backup_from_row(row) for row in rows]


def create_restore_drill(
    request: CreateRestoreDrillRequest,
    *,
    actor: str,
) -> RestoreDrillResponse:
    ensure_schema()
    label = validate_label(request.label)
    payload = {"backupId": request.backup_id, "label": label, "actor": actor}
    payload_hash = canonical_hash(payload)

    with connection() as db:
        existing = db.execute(
            "SELECT * FROM production_restore_drills WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        backup = db.execute(
            "SELECT * FROM production_backup_records WHERE id = ?",
            (request.backup_id,),
        ).fetchone()
    if existing is not None:
        if existing["payload_hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="Restore drill idempotency key was reused with a different payload",
            )
        return restore_from_row(existing)
    if backup is None or backup["status"] != "completed" or not backup["manifest_path"]:
        raise HTTPException(status_code=422, detail="Completed backup is required for restore drill")

    settings = get_settings()
    restore_id = str(uuid4())
    created_at = now_iso()
    restore_root = root_path(settings.operations_restore_root)
    directory_name = f"{created_at[:19].replace(':', '')}-{label}-{restore_id[:8]}"
    destination = new_child_directory(restore_root, directory_name)

    active_paths = {
        Path(settings.database_path).expanduser().resolve(),
        Path(settings.runtime_journal_path).expanduser().resolve(),
    }
    if destination in active_paths or any(destination.is_relative_to(path.parent) and destination == path for path in active_paths):
        raise HTTPException(status_code=422, detail="Restore drill cannot target an active data path")

    with connection() as db:
        db.execute(
            """
            INSERT INTO production_restore_drills (
                id, idempotency_key, payload_hash, backup_id, label, status,
                destination_directory, integrity_json, safe_state_json, error,
                actor, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, 'processing', ?, '{}', '{}', NULL, ?, ?, NULL)
            """,
            (
                restore_id,
                request.idempotency_key,
                payload_hash,
                request.backup_id,
                label,
                str(destination),
                actor,
                created_at,
            ),
        )

    try:
        manifest_path = Path(backup["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        backup_directory = Path(backup["destination_directory"])
        source_files = {file["logicalName"]: file for file in manifest["files"]}
        platform_source = backup_directory / str(source_files["platform_database"]["fileName"])
        runtime_source = backup_directory / str(source_files["runtime_journal"]["fileName"])

        for source, logical_name in (
            (platform_source, "platform_database"),
            (runtime_source, "runtime_journal"),
        ):
            expected = source_files[logical_name]["sha256"]
            if sha256_file(source) != expected:
                raise RuntimeError(f"Backup checksum mismatch for {logical_name}")

        platform_restored = destination / "platform.restored.db"
        runtime_restored = destination / "runtime_journal.restored.db"
        online_backup(platform_source, platform_restored)
        online_backup(runtime_source, runtime_restored)

        integrity = {
            "platform": integrity_result(platform_restored),
            "runtime": integrity_result(runtime_restored),
            "platformCounts": database_counts(platform_restored, PLATFORM_TABLES),
            "runtimeCounts": database_counts(runtime_restored, RUNTIME_TABLES),
        }
        if integrity["platform"] != "ok" or integrity["runtime"] != "ok":
            raise RuntimeError("Restored SQLite integrity check failed")
        if integrity["platformCounts"] != source_files["platform_database"]["tableCounts"]:
            raise RuntimeError("Restored Platform table counts differ from backup manifest")
        if integrity["runtimeCounts"] != source_files["runtime_journal"]["tableCounts"]:
            raise RuntimeError("Restored Runtime table counts differ from backup manifest")

        enforce_restored_safe_state(platform_restored, actor)
        safe_env = destination / "safe-startup.env"
        safe_env.write_text(
            "\n".join(
                (
                    "VG_LIVE_TRADING_ENABLED=false",
                    "VG_RUNTIME_LIVE_WRITE_ENABLED=false",
                    "VG_RUNTIME_LIVE_ACCOUNT_ALLOWLIST=",
                    "VG_RUNTIME_LIVE_STRATEGY_ALLOWLIST=",
                    "VG_RUNTIME_LIVE_SYMBOL_ALLOWLIST=",
                    "VG_RUNTIME_LIVE_MAX_ORDER_NOTIONAL=0",
                    "VG_RUNTIME_LIVE_MAX_DAILY_NOTIONAL=0",
                    "",
                )
            ),
            encoding="utf-8",
        )
        safe_state = {
            "platformLiveTradingEnabled": False,
            "runtimeLiveWriteEnabled": False,
            "globalKillSwitchEnabled": restored_global_kill_switch_enabled(platform_restored),
            "startupOverrideFile": safe_env.name,
            "productionPathsModified": False,
        }
        if safe_state["globalKillSwitchEnabled"] is not True:
            raise RuntimeError("Restored Global Kill Switch is not enabled")

        completed_at = now_iso()
        with connection() as db:
            db.execute(
                """
                UPDATE production_restore_drills
                SET status = 'completed', integrity_json = ?, safe_state_json = ?,
                    completed_at = ?, error = NULL
                WHERE id = ?
                """,
                (
                    json.dumps(integrity, ensure_ascii=False, sort_keys=True),
                    json.dumps(safe_state, ensure_ascii=False, sort_keys=True),
                    completed_at,
                    restore_id,
                ),
            )
            row = db.execute(
                "SELECT * FROM production_restore_drills WHERE id = ?",
                (restore_id,),
            ).fetchone()
        audit(
            "production_restore_drill_completed",
            "production_restore_drill",
            restore_id,
            {
                "restoreDrillId": restore_id,
                "backupId": request.backup_id,
                "actor": actor,
                "safeState": safe_state,
            },
        )
        return restore_from_row(row)
    except Exception as exc:
        safe_error = str(redact_sensitive(exc))
        with connection() as db:
            db.execute(
                """
                UPDATE production_restore_drills
                SET status = 'failed', error = ?, completed_at = ?
                WHERE id = ?
                """,
                (safe_error, now_iso(), restore_id),
            )
        audit(
            "production_restore_drill_failed",
            "production_restore_drill",
            restore_id,
            {
                "restoreDrillId": restore_id,
                "backupId": request.backup_id,
                "actor": actor,
                "error": safe_error,
            },
        )
        raise HTTPException(status_code=500, detail="Production restore drill failed") from exc


def enforce_restored_safe_state(path: Path, actor: str) -> None:
    db = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        if "trading_kill_switches" not in tables:
            raise RuntimeError("Restored Platform database has no Kill Switch table")
        timestamp = now_iso()
        db.execute(
            """
            INSERT INTO trading_kill_switches (
                scope_type, scope_id, enabled, reason, actor, version, updated_at
            ) VALUES ('global', '*', 1, ?, ?, 1, ?)
            ON CONFLICT(scope_type, scope_id) DO UPDATE SET
                enabled = 1,
                reason = excluded.reason,
                actor = excluded.actor,
                version = trading_kill_switches.version + 1,
                updated_at = excluded.updated_at
            """,
            ("restore drill safe state", actor, timestamp),
        )
        db.commit()
    finally:
        db.close()


def restored_global_kill_switch_enabled(path: Path) -> bool:
    db = sqlite3.connect(path)
    try:
        row = db.execute(
            """
            SELECT enabled FROM trading_kill_switches
            WHERE scope_type = 'global' AND scope_id = '*'
            """
        ).fetchone()
        return row is not None and int(row[0]) == 1
    finally:
        db.close()


def list_restore_drills() -> list[RestoreDrillResponse]:
    ensure_schema()
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM production_restore_drills ORDER BY created_at DESC"
        ).fetchall()
    return [restore_from_row(row) for row in rows]


def backup_from_row(row) -> BackupResponse:
    return BackupResponse(
        backupId=row["id"],
        idempotencyKey=row["idempotency_key"],
        label=row["label"],
        status=row["status"],
        destinationDirectory=row["destination_directory"],
        manifestPath=row["manifest_path"],
        files=json.loads(row["files_json"]),
        error=row["error"],
        actor=row["actor"],
        createdAt=row["created_at"],
        completedAt=row["completed_at"],
    )


def restore_from_row(row) -> RestoreDrillResponse:
    return RestoreDrillResponse(
        restoreDrillId=row["id"],
        idempotencyKey=row["idempotency_key"],
        backupId=row["backup_id"],
        label=row["label"],
        status=row["status"],
        destinationDirectory=row["destination_directory"],
        integrity=json.loads(row["integrity_json"]),
        safeState=json.loads(row["safe_state_json"]),
        error=row["error"],
        actor=row["actor"],
        createdAt=row["created_at"],
        completedAt=row["completed_at"],
    )


router = APIRouter(prefix=get_settings().api_prefix, tags=["production-operations"])


@router.post("/ops/backups", response_model=BackupResponse)
def run_backup(request: CreateBackupRequest, http_request: Request) -> BackupResponse:
    principal = require_principal(http_request)
    return create_backup(request, actor=principal.user_id)


@router.get("/ops/backups", response_model=list[BackupResponse])
def backups() -> list[BackupResponse]:
    return list_backups()


@router.post("/ops/restore-drills", response_model=RestoreDrillResponse)
def run_restore_drill(
    request: CreateRestoreDrillRequest,
    http_request: Request,
) -> RestoreDrillResponse:
    principal = require_principal(http_request)
    return create_restore_drill(request, actor=principal.user_id)


@router.get("/ops/restore-drills", response_model=list[RestoreDrillResponse])
def restore_drills() -> list[RestoreDrillResponse]:
    return list_restore_drills()
