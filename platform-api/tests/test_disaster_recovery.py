import hashlib
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.execution_risk import ensure_schema as ensure_risk_schema
from app.main import app


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def create_runtime_journal(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE runtime_commands (
                command_id TEXT PRIMARY KEY,
                command_type TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE runtime_events (
                event_id TEXT PRIMARY KEY,
                command_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
            INSERT INTO runtime_commands VALUES (
                'command-1', 'submit_order', 'completed', '{}',
                '2026-07-23T00:00:00+00:00', '2026-07-23T00:00:01+00:00'
            );
            INSERT INTO runtime_events VALUES (
                'event-1', 'command-1', 'order_acknowledged', '{}',
                '2026-07-23T00:00:01+00:00'
            );
            """
        )
        db.commit()
    finally:
        db.close()


def configure_paths(
    monkeypatch,
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, Path]:
    platform_path = tmp_path / "active" / "platform.db"
    runtime_path = tmp_path / "active" / "runtime_journal.db"
    avatar_root = tmp_path / "active" / "avatars"
    backup_root = tmp_path / "backups"
    restore_root = tmp_path / "restore-drills"
    platform_path.parent.mkdir(parents=True)
    avatar_root.mkdir(parents=True)
    create_runtime_journal(runtime_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(platform_path))
    monkeypatch.setattr(settings, "runtime_journal_path", str(runtime_path))
    monkeypatch.setattr(settings, "avatar_data_directory", str(avatar_root))
    monkeypatch.setattr(settings, "operations_backup_root", str(backup_root))
    monkeypatch.setattr(settings, "operations_restore_root", str(restore_root))
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_mode", "development")
    monkeypatch.setattr(settings, "development_roles", "admin")
    monkeypatch.setattr(settings, "live_trading_enabled", False)
    return platform_path, runtime_path, avatar_root, backup_root, restore_root


def test_consistent_backup_and_restore_drill_enforce_safe_state(
    monkeypatch, tmp_path: Path
) -> None:
    platform_path, runtime_path, avatar_root, _, _ = configure_paths(monkeypatch, tmp_path)
    avatar_name = "11111111-1111-1111-1111-111111111111.webp"
    avatar_payload = b"test-avatar-payload"
    (avatar_root / avatar_name).write_bytes(avatar_payload)
    with TestClient(app) as client:
        ensure_risk_schema()
        with connection() as db:
            db.execute(
                """
                INSERT INTO orders (
                    id, command_id, account_id, instrument_id, symbol, side,
                    order_type, quantity, price, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "backup-order-1",
                    "backup-command-1",
                    "account_sim_usdt",
                    "instrument_btc_usdt",
                    "BTCUSDT",
                    "buy",
                    "limit",
                    "0.01",
                    "100",
                    "filled",
                    "2026-07-23T00:00:00+00:00",
                    "2026-07-23T00:00:01+00:00",
                ),
            )

        backup = client.post(
            "/api/v1/ops/backups",
            json={"idempotencyKey": "backup-001", "label": "nightly"},
        )
        assert backup.status_code == 200
        body = backup.json()
        assert body["status"] == "completed"
        assert len(body["files"]) == 3
        manifest_path = Path(body["manifestPath"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        serialized_manifest = json.dumps(manifest).lower()
        assert "api_key" not in serialized_manifest
        assert "password_hash" not in serialized_manifest
        assert "token_hash" not in serialized_manifest
        assert "$argon2" not in serialized_manifest
        assert manifest["safeRestoreDefaults"] == {
            "globalKillSwitchEnabled": True,
            "platformLiveTradingEnabled": False,
            "runtimeLiveWriteEnabled": False,
        }
        for item in manifest["files"]:
            file_path = manifest_path.parent / item["fileName"]
            assert sha256_file(file_path) == item["sha256"]
            assert item["integrity"] == "ok"
        platform_manifest = next(
            item for item in manifest["files"] if item["logicalName"] == "platform_database"
        )
        assert "users" in platform_manifest["tableCounts"]
        avatar_manifest = next(
            item for item in manifest["files"] if item["logicalName"] == "avatar_archive"
        )
        assert avatar_manifest["fileCount"] == 1
        assert avatar_manifest["totalBytes"] == len(avatar_payload)

        replay = client.post(
            "/api/v1/ops/backups",
            json={"idempotencyKey": "backup-001", "label": "nightly"},
        )
        assert replay.status_code == 200
        assert replay.json()["backupId"] == body["backupId"]

        restore = client.post(
            "/api/v1/ops/restore-drills",
            json={
                "idempotencyKey": "restore-001",
                "backupId": body["backupId"],
                "label": "monthly-drill",
            },
        )
        assert restore.status_code == 200
        restored = restore.json()
        assert restored["status"] == "completed"
        assert restored["integrity"]["platform"] == "ok"
        assert restored["integrity"]["runtime"] == "ok"
        assert restored["integrity"]["avatars"] == {
            "fileCount": 1,
            "status": "ok",
            "totalBytes": len(avatar_payload),
        }
        assert restored["safeState"] == {
            "globalKillSwitchEnabled": True,
            "platformLiveTradingEnabled": False,
            "productionPathsModified": False,
            "runtimeLiveWriteEnabled": False,
            "startupOverrideFile": "safe-startup.env",
        }

        drill_directory = Path(restored["destinationDirectory"])
        safe_env = (drill_directory / "safe-startup.env").read_text(encoding="utf-8")
        assert "VG_LIVE_TRADING_ENABLED=false" in safe_env
        assert "VG_RUNTIME_LIVE_WRITE_ENABLED=false" in safe_env
        restored_avatar = drill_directory / "avatars.restored" / avatar_name
        assert restored_avatar.read_bytes() == avatar_payload

        restored_db = sqlite3.connect(drill_directory / "platform.restored.db")
        try:
            kill_switch = restored_db.execute(
                """
                SELECT enabled FROM trading_kill_switches
                WHERE scope_type = 'global' AND scope_id = '*'
                """
            ).fetchone()
            assert kill_switch == (1,)
        finally:
            restored_db.close()

        with connection() as db:
            production_kill_switch = db.execute(
                """
                SELECT enabled FROM trading_kill_switches
                WHERE scope_type = 'global' AND scope_id = '*'
                """
            ).fetchone()
        assert production_kill_switch is None
        assert platform_path.exists()
        assert runtime_path.exists()


def test_backup_rejects_invalid_label_and_missing_runtime(monkeypatch, tmp_path: Path) -> None:
    _, runtime_path, _, _, _ = configure_paths(monkeypatch, tmp_path)
    with TestClient(app) as client:
        invalid = client.post(
            "/api/v1/ops/backups",
            json={"idempotencyKey": "bad-label", "label": "../escape"},
        )
        assert invalid.status_code == 422

        runtime_path.unlink()
        failed = client.post(
            "/api/v1/ops/backups",
            json={"idempotencyKey": "missing-runtime", "label": "nightly"},
        )
        assert failed.status_code == 500
        records = client.get("/api/v1/ops/backups")
        assert records.status_code == 200
        assert records.json()[0]["status"] == "failed"
        assert records.json()[0]["error"]


def test_backup_rejects_unsupported_avatar_directory_entry(monkeypatch, tmp_path: Path) -> None:
    _, _, avatar_root, _, _ = configure_paths(monkeypatch, tmp_path)
    (avatar_root / "unexpected.txt").write_text("not-an-avatar", encoding="utf-8")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ops/backups",
            json={"idempotencyKey": "unsupported-avatar", "label": "nightly"},
        )
        assert response.status_code == 500
        records = client.get("/api/v1/ops/backups")
        assert records.status_code == 200
        assert records.json()[0]["status"] == "failed"
        assert "unsupported entry" in records.json()[0]["error"]
