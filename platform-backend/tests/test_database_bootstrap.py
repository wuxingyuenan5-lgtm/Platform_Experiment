import hashlib
from contextlib import contextmanager
from pathlib import Path

from app import database, database_bootstrap
from app.config import get_settings

EXPECTED_SCHEMA_SHA256 = "421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801"


def test_schema_sql_checksum_and_compatibility_identity() -> None:
    assert database.SCHEMA_SQL is database_bootstrap.SCHEMA_SQL
    assert database.migrate_schema is database_bootstrap.migrate_schema
    assert database.ensure_column is database_bootstrap.ensure_column
    assert hashlib.sha256(database_bootstrap.SCHEMA_SQL.encode("utf-8")).hexdigest() == (
        EXPECTED_SCHEMA_SHA256
    )


def test_initialize_database_preserves_bootstrap_before_seed_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    get_settings().database_path = str(tmp_path / "order.db")
    calls: list[str] = []
    sentinel = object()

    @contextmanager
    def fake_connection():
        calls.append("connection-open")
        yield sentinel
        calls.append("connection-close")

    def fake_bootstrap(db) -> None:
        assert db is sentinel
        calls.append("bootstrap")

    def fake_seed(db) -> None:
        assert db is sentinel
        calls.append("seed")

    monkeypatch.setattr(database, "connection", fake_connection)
    monkeypatch.setattr(database, "bootstrap_database", fake_bootstrap)
    monkeypatch.setattr(database, "seed_reference_data", fake_seed)

    database.initialize_database()

    assert calls == ["connection-open", "bootstrap", "seed", "connection-close"]
