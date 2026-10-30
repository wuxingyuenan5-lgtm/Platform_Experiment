import json
import sqlite3

import pytest

from app.config import get_settings
from app.data_audit import decode_report, encode_report
from app.database import initialize_database
from app.strategy_research_database import connection, migrate


def test_offline_research_copy_preserves_sparse_manifest_rowids_and_business(tmp_path):
    initialize_database()
    source = get_settings().database_path
    with sqlite3.connect(source) as db:
        db.execute(
            "INSERT INTO research_strategy_parts VALUES(?,?,?,?,?,?,?,?,?)",
            ("p", None, "cursor", "p.parquet", "a" * 64, 1, "t", "t", "t"),
        )
        db.execute("UPDATE research_strategy_parts SET rowid=123")
    target = tmp_path / "research.db"
    counts = migrate(source, target)
    assert counts["research_strategy_parts"] == 1
    get_settings().strategy_research_database_path = str(target)
    with connection() as db:
        assert db.execute("SELECT rowid FROM research_strategy_parts").fetchone()[0] == 123
        assert (
            db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='orders'").fetchone()[0] == 0
        )
    with sqlite3.connect(source) as db:
        assert db.execute("SELECT COUNT(*) FROM research_strategy_parts").fetchone()[0] == 1
    with pytest.raises(FileExistsError):
        migrate(source, target)


def test_audit_compression_preserves_entire_report_and_reads_legacy():
    report = {"checks": [{"status": "healthy", "message": "数据完整"}] * 1000}
    encoded = encode_report(report)
    assert len(encoded) < len(json.dumps(report)) // 10
    assert decode_report(encoded) == report
    assert decode_report(json.dumps(report)) == report


def test_minute_facts_roundtrip_typed_archive_projection(tmp_path):
    import pyarrow.parquet as pq

    from app.strategy_research_projection import project_next, read_projection
    from app.strategy_research_repository import publish, read_rows, root_path

    initialize_database()
    get_settings().strategy_research_path = str(tmp_path / "archive")
    get_settings().strategy_research_min_free_bytes = 0
    event = {
        "kind": "quote_minute",
        "entity": "bybit:linear:BTCUSDT",
        "bucketStartMs": 60000,
        "intervalMs": 60000,
        "count": 10,
        "values": {"bid": {"open": "1.00000000001", "high": "2", "low": "1", "close": "2"}},
        "quality": ["observation_gap"],
    }
    raw = {
        "eventId": "s:1",
        "kind": "quote_minute",
        "quoteScope": "public",
        "runtimeReceivedAt": "1970-01-01T00:02:00+00:00",
        "payload": event,
        "ingestionMode": "realtime",
        "stream": event["entity"],
    }
    part = publish(
        {"schemaVersion": "market-events.v1", "after": None, "nextCursor": "s:1", "events": [raw]}
    )
    table = pq.read_table(root_path() / (part + ".parquet"))
    assert table.column("bid_open").to_pylist() == ["1.00000000001"] * 2
    assert read_rows(kind="quote_minute")[0]["values"] == event["values"]
    assert project_next()
    rows = read_projection("quote_minute", event["entity"])
    assert rows[0]["count"] == 10 and rows[0]["quality"] == ["observation_gap"]


def test_minute_history_http_response_and_window_boundaries(authorize_funding_ceo):
    from fastapi.testclient import TestClient

    from app.main import app

    initialize_database()
    client = TestClient(app)
    authorize_funding_ceo(client)
    params = {"entity": "funding-btc", "kind": "spread_minute", "start_ms": 0, "end_ms": 60000}
    response = client.get("/api/v1/research/strategies/minute-history", params=params)
    assert response.status_code == 200
    assert response.json()["data"]["rows"] == []
    params["end_ms"] = 32 * 86400000
    assert (
        client.get("/api/v1/research/strategies/minute-history", params=params).status_code == 422
    )
