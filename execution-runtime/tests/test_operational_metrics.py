import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry, generate_latest

from app.config import get_settings
from app.operational_metrics import JournalCollector, router


def collect():
    registry = CollectorRegistry()
    registry.register(JournalCollector())
    return generate_latest(registry).decode()


def test_missing_journal_is_not_initialized(monkeypatch, tmp_path):
    target = tmp_path / "not-created" / "journal.db"
    monkeypatch.setattr(get_settings(), "journal_path", str(target))
    assert "vg_runtime_metrics_journal_available 0.0" in collect()
    assert not target.parent.exists()


def test_restart_scrape_reads_persisted_unknown_without_recovery_or_writes(monkeypatch, tmp_path):
    target = tmp_path / "journal.db"
    monkeypatch.setattr(get_settings(), "journal_path", str(target))
    stamp = (datetime.now(UTC) - timedelta(seconds=90)).isoformat()
    db = sqlite3.connect(target)
    db.execute("CREATE TABLE runtime_commands (status TEXT, created_at TEXT)")
    db.execute("INSERT INTO runtime_commands VALUES ('result_unknown',?)", (stamp,))
    db.commit()
    db.close()
    before = target.read_bytes()
    output = collect()
    assert 'vg_runtime_pending_commands{state="result_unknown"} 1.0' in output
    assert 'vg_runtime_pending_commands{state="processing"} 0.0' in output
    line = next(
        line
        for line in output.splitlines()
        if line.startswith('vg_runtime_pending_commands_oldest_seconds{state="result_unknown"}')
    )
    assert 90 <= float(line.rsplit(" ", 1)[1]) < 100
    assert target.read_bytes() == before


def test_runtime_metrics_restrict_clients_to_loopback(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "journal_path", str(tmp_path / "absent.db"))
    app = FastAPI()
    app.include_router(router)
    assert TestClient(app, client=("203.0.113.2", 1234)).get("/metrics").status_code == 403
    assert TestClient(app, client=("127.0.0.1", 1234)).get("/metrics").status_code == 200
