import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import trade_commands
from app.database import connection, initialize_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.schemas import CreateTradeCommandRequest
from tests.test_idempotency_conflicts import filled_runtime_response, trade_command_payload

pytestmark = pytest.mark.usefixtures("generic_trading_instance")


def test_concurrent_symbol_claims_dispatch_only_the_winner(monkeypatch):
    initialize_database()
    barrier = Barrier(2, timeout=5)
    validate = trade_commands.validate_trade_command_catalog
    calls = []

    def synchronize(request):
        validate(request)
        barrier.wait()

    def runtime_post(*args, **kwargs):
        calls.append(kwargs["json"])
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr(trade_commands, "validate_trade_command_catalog", synchronize)
    monkeypatch.setattr("app.runtime_transport.post", runtime_post)

    def submit(symbol):
        return TestClient(app).post("/api/v1/trading/commands", json={
            **trade_command_payload("1"), "symbol": symbol,
        })

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, ["BTCUSDT", "ETHUSDT"]))
    assert sorted(response.status_code for response in results) == [200, 409]
    assert len(calls) == 1
    with connection() as db:
        row = db.execute("SELECT symbol FROM trade_commands").fetchone()
        assert row["symbol"] == calls[0]["symbol"]
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1


def test_rejected_command_without_order_preserves_original_symbol(monkeypatch):
    initialize_database()
    payload = trade_command_payload("1")

    def reject(*args, **kwargs):
        raise HTTPException(422, "isolated pre-dispatch rejection")

    monkeypatch.setattr(trade_commands, "submit_trade_command_order", reject)
    client = TestClient(app)
    assert client.post("/api/v1/trading/commands", json=payload).status_code == 422
    assert client.post("/api/v1/trading/commands", json={
        **payload, "symbol": "ETHUSDT",
    }).status_code == 409
    with pytest.raises(HTTPException) as error:
        trade_commands.retry_unsubmitted_trade_command(
            CreateTradeCommandRequest.model_validate({**payload, "symbol": "ETHUSDT"})
        )
    assert error.value.status_code == 409
    with connection() as db:
        row = db.execute("SELECT status,symbol FROM trade_commands").fetchone()
        assert tuple(row) == ("rejected", "BTCUSDT")
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_symbol_migration_only_backfills_unambiguous_order_evidence():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE trade_commands(id TEXT PRIMARY KEY);
        CREATE TABLE orders(command_id TEXT, symbol TEXT);
        INSERT INTO trade_commands VALUES ('unique'), ('none'), ('ambiguous');
        INSERT INTO orders VALUES ('unique','XAUUSD.a'), ('unique','XAUUSD.a'),
                                  ('ambiguous','BTCUSDT'), ('ambiguous','ETHUSDT');
    """)
    migration = next(m for m in PLATFORM_MIGRATIONS if m.version == 48)
    apply_migrations(db, (migration,))
    apply_migrations(db, (migration,))
    assert dict(db.execute("SELECT id,symbol FROM trade_commands")) == {
        "unique": "XAUUSD.a", "none": None, "ambiguous": None,
    }
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 4


def test_legacy_command_without_symbol_evidence_fails_closed(monkeypatch):
    initialize_database()

    def reject(*args, **kwargs):
        raise HTTPException(422, "isolated pre-dispatch rejection")

    monkeypatch.setattr(trade_commands, "submit_trade_command_order", reject)
    client = TestClient(app)
    payload = trade_command_payload("1")
    assert client.post("/api/v1/trading/commands", json=payload).status_code == 422
    with connection() as db:
        db.execute("UPDATE trade_commands SET symbol=NULL")
    assert client.post("/api/v1/trading/commands", json=payload).status_code == 409
