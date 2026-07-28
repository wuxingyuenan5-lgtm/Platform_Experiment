from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"expected one target in {path}, found {count}: {old[:100]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


disaster = ROOT / "platform-backend/app/disaster_recovery.py"
replace_once(
    disaster,
    "from app.redaction import redact_sensitive\n",
    "from app.redaction import redact_sensitive\n"
    "from app.user_backup_archive import (\n"
    "    USER_PLATFORM_TABLES,\n"
    "    avatar_archive_manifest,\n"
    "    restore_avatar_archive,\n"
    ")\n",
)
replace_once(
    disaster,
    '    "live_trading_sessions",\n)\n',
    '    "live_trading_sessions",\n    *USER_PLATFORM_TABLES,\n)\n',
)
replace_once(disaster, '"schemaVersion": 1,', '"schemaVersion": 2,')
replace_once(
    disaster,
    '''        platform_backup = destination / "platform.db"\n        runtime_backup = destination / "runtime_journal.db"\n        online_backup(platform_source, platform_backup)\n        online_backup(runtime_source, runtime_backup)\n\n        files = [\n            file_manifest(\n                logical_name="platform_database",\n                path=platform_backup,\n                source_file_name=platform_source.name,\n                tables=PLATFORM_TABLES,\n            ),\n            file_manifest(\n                logical_name="runtime_journal",\n                path=runtime_backup,\n                source_file_name=runtime_source.name,\n                tables=RUNTIME_TABLES,\n            ),\n        ]\n''',
    '''        platform_backup = destination / "platform.db"\n        runtime_backup = destination / "runtime_journal.db"\n        avatar_backup = destination / "avatars.zip"\n        online_backup(platform_source, platform_backup)\n        online_backup(runtime_source, runtime_backup)\n\n        files = [\n            file_manifest(\n                logical_name="platform_database",\n                path=platform_backup,\n                source_file_name=platform_source.name,\n                tables=PLATFORM_TABLES,\n            ),\n            file_manifest(\n                logical_name="runtime_journal",\n                path=runtime_backup,\n                source_file_name=runtime_source.name,\n                tables=RUNTIME_TABLES,\n            ),\n            avatar_archive_manifest(settings.avatar_data_directory, avatar_backup),\n        ]\n''',
)
replace_once(
    disaster,
    '''        platform_source = backup_directory / str(source_files["platform_database"]["fileName"])\n        runtime_source = backup_directory / str(source_files["runtime_journal"]["fileName"])\n\n        for source, logical_name in (\n            (platform_source, "platform_database"),\n            (runtime_source, "runtime_journal"),\n        ):\n''',
    '''        platform_source = backup_directory / str(source_files["platform_database"]["fileName"])\n        runtime_source = backup_directory / str(source_files["runtime_journal"]["fileName"])\n        avatar_source = backup_directory / str(source_files["avatar_archive"]["fileName"])\n\n        for source, logical_name in (\n            (platform_source, "platform_database"),\n            (runtime_source, "runtime_journal"),\n            (avatar_source, "avatar_archive"),\n        ):\n''',
)
replace_once(
    disaster,
    '''        platform_restored = destination / "platform.restored.db"\n        runtime_restored = destination / "runtime_journal.restored.db"\n        online_backup(platform_source, platform_restored)\n        online_backup(runtime_source, runtime_restored)\n\n        integrity = {\n            "platform": integrity_result(platform_restored),\n            "runtime": integrity_result(runtime_restored),\n            "platformCounts": database_counts(platform_restored, PLATFORM_TABLES),\n            "runtimeCounts": database_counts(runtime_restored, RUNTIME_TABLES),\n        }\n''',
    '''        platform_restored = destination / "platform.restored.db"\n        runtime_restored = destination / "runtime_journal.restored.db"\n        avatars_restored = destination / "avatars.restored"\n        online_backup(platform_source, platform_restored)\n        online_backup(runtime_source, runtime_restored)\n        avatar_integrity = restore_avatar_archive(\n            avatar_source,\n            avatars_restored,\n            expected_file_count=int(source_files["avatar_archive"]["fileCount"]),\n            expected_total_bytes=int(source_files["avatar_archive"]["totalBytes"]),\n        )\n\n        integrity = {\n            "platform": integrity_result(platform_restored),\n            "runtime": integrity_result(runtime_restored),\n            "avatars": avatar_integrity,\n            "platformCounts": database_counts(platform_restored, PLATFORM_TABLES),\n            "runtimeCounts": database_counts(runtime_restored, RUNTIME_TABLES),\n        }\n''',
)

test = ROOT / "platform-backend/tests/test_disaster_recovery.py"
replace_once(
    test,
    '''def configure_paths(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path, Path]:\n    platform_path = tmp_path / "active" / "platform.db"\n    runtime_path = tmp_path / "active" / "runtime_journal.db"\n    backup_root = tmp_path / "backups"\n    restore_root = tmp_path / "restore-drills"\n    platform_path.parent.mkdir(parents=True)\n    create_runtime_journal(runtime_path)\n\n    settings = get_settings()\n    monkeypatch.setattr(settings, "database_path", str(platform_path))\n    monkeypatch.setattr(settings, "runtime_journal_path", str(runtime_path))\n    monkeypatch.setattr(settings, "operations_backup_root", str(backup_root))\n    monkeypatch.setattr(settings, "operations_restore_root", str(restore_root))\n    monkeypatch.setattr(settings, "environment", "development")\n    monkeypatch.setattr(settings, "auth_mode", "development")\n    monkeypatch.setattr(settings, "development_roles", "admin")\n    monkeypatch.setattr(settings, "live_trading_enabled", False)\n    return platform_path, runtime_path, backup_root, restore_root\n''',
    '''def configure_paths(\n    monkeypatch,\n    tmp_path: Path,\n) -> tuple[Path, Path, Path, Path, Path]:\n    platform_path = tmp_path / "active" / "platform.db"\n    runtime_path = tmp_path / "active" / "runtime_journal.db"\n    avatar_root = tmp_path / "active" / "avatars"\n    backup_root = tmp_path / "backups"\n    restore_root = tmp_path / "restore-drills"\n    platform_path.parent.mkdir(parents=True)\n    avatar_root.mkdir(parents=True)\n    create_runtime_journal(runtime_path)\n\n    settings = get_settings()\n    monkeypatch.setattr(settings, "database_path", str(platform_path))\n    monkeypatch.setattr(settings, "runtime_journal_path", str(runtime_path))\n    monkeypatch.setattr(settings, "avatar_data_directory", str(avatar_root))\n    monkeypatch.setattr(settings, "operations_backup_root", str(backup_root))\n    monkeypatch.setattr(settings, "operations_restore_root", str(restore_root))\n    monkeypatch.setattr(settings, "environment", "development")\n    monkeypatch.setattr(settings, "auth_mode", "development")\n    monkeypatch.setattr(settings, "development_roles", "admin")\n    monkeypatch.setattr(settings, "live_trading_enabled", False)\n    return platform_path, runtime_path, avatar_root, backup_root, restore_root\n''',
)
replace_once(
    test,
    '''    platform_path, runtime_path, _, _ = configure_paths(monkeypatch, tmp_path)\n    with TestClient(app) as client:\n''',
    '''    platform_path, runtime_path, avatar_root, _, _ = configure_paths(monkeypatch, tmp_path)\n    avatar_name = "11111111-1111-1111-1111-111111111111.webp"\n    avatar_payload = b"test-avatar-payload"\n    (avatar_root / avatar_name).write_bytes(avatar_payload)\n    with TestClient(app) as client:\n''',
)
replace_once(test, '        assert len(body["files"]) == 2\n', '        assert len(body["files"]) == 3\n')
replace_once(
    test,
    '''        for item in manifest["files"]:\n            file_path = manifest_path.parent / item["fileName"]\n            assert sha256_file(file_path) == item["sha256"]\n            assert item["integrity"] == "ok"\n\n''',
    '''        for item in manifest["files"]:\n            file_path = manifest_path.parent / item["fileName"]\n            assert sha256_file(file_path) == item["sha256"]\n            assert item["integrity"] == "ok"\n        platform_manifest = next(\n            item for item in manifest["files"] if item["logicalName"] == "platform_database"\n        )\n        assert "users" in platform_manifest["tableCounts"]\n        avatar_manifest = next(\n            item for item in manifest["files"] if item["logicalName"] == "avatar_archive"\n        )\n        assert avatar_manifest["fileCount"] == 1\n        assert avatar_manifest["totalBytes"] == len(avatar_payload)\n\n''',
)
replace_once(
    test,
    '''        assert restored["integrity"]["platform"] == "ok"\n        assert restored["integrity"]["runtime"] == "ok"\n''',
    '''        assert restored["integrity"]["platform"] == "ok"\n        assert restored["integrity"]["runtime"] == "ok"\n        assert restored["integrity"]["avatars"] == {\n            "fileCount": 1,\n            "status": "ok",\n            "totalBytes": len(avatar_payload),\n        }\n''',
)
replace_once(
    test,
    '''        safe_env = (drill_directory / "safe-startup.env").read_text(encoding="utf-8")\n        assert "VG_LIVE_TRADING_ENABLED=false" in safe_env\n        assert "VG_RUNTIME_LIVE_WRITE_ENABLED=false" in safe_env\n\n''',
    '''        safe_env = (drill_directory / "safe-startup.env").read_text(encoding="utf-8")\n        assert "VG_LIVE_TRADING_ENABLED=false" in safe_env\n        assert "VG_RUNTIME_LIVE_WRITE_ENABLED=false" in safe_env\n        restored_avatar = drill_directory / "avatars.restored" / avatar_name\n        assert restored_avatar.read_bytes() == avatar_payload\n\n''',
)
replace_once(test, '    _, runtime_path, _, _ = configure_paths(monkeypatch, tmp_path)\n', '    _, runtime_path, _, _, _ = configure_paths(monkeypatch, tmp_path)\n')
test.write_text(
    test.read_text(encoding="utf-8")
    + '''\n\ndef test_backup_rejects_unsupported_avatar_directory_entry(monkeypatch, tmp_path: Path) -> None:\n    _, _, avatar_root, _, _ = configure_paths(monkeypatch, tmp_path)\n    (avatar_root / "unexpected.txt").write_text("not-an-avatar", encoding="utf-8")\n\n    with TestClient(app) as client:\n        response = client.post(\n            "/api/v1/ops/backups",\n            json={"idempotencyKey": "unsupported-avatar", "label": "nightly"},\n        )\n        assert response.status_code == 500\n        records = client.get("/api/v1/ops/backups")\n        assert records.status_code == 200\n        assert records.json()[0]["status"] == "failed"\n        assert "unsupported entry" in records.json()[0]["error"]\n''',
    encoding="utf-8",
)
