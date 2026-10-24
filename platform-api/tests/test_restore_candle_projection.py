import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.config import get_settings
from app.database import initialize_database
from app.database_connection import connection
from scripts.restore_candle_projection import restore


def test_restore_is_bounded_insert_only_verified_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "restore.db"))
    monkeypatch.setattr(get_settings(), "strategy_research_path", str(tmp_path))
    initialize_database()
    base = dict(
        category="linear",
        symbol="BTCUSDT",
        priceType="trade",
        intervalMs="60000",
        close="100.123456789012345",
        quality=[],
    )
    events = [dict(base, closeTimeMs=str(stamp)) for stamp in (60000, 120000, 180000)]
    events += [dict(base, closeTimeMs="90000", quality=["numeric_invalid"])]
    events += [dict(base, closeTimeMs="90000", category="spot")]
    path = tmp_path / "test.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                dict(layer="derived", kind="historical_candle", event_json=json.dumps(row))
                for row in events
            ]
        ),
        path,
    )
    parts = [dict(path=path.name, checksum=hashlib.sha256(path.read_bytes()).hexdigest())]
    with connection() as db:
        db.execute(
            "INSERT INTO research_strategy_projection VALUES(?,?,?,?)",
            ("historical_candle", "BTCUSDT:linear:trade", 60000, '{"close":"999"}'),
        )
    result = restore(parts, 60000, 120000)
    assert result["inserted"] == 1
    assert restore(parts, 60000, 120000)["inserted"] == 0
    with connection() as db:
        rows = db.execute(
            "SELECT at_ms,payload_json FROM research_strategy_projection ORDER BY at_ms"
        ).fetchall()
    assert [row[0] for row in rows] == [60000, 120000]
    assert json.loads(rows[0][1])["close"] == "999"
    assert json.loads(rows[1][1])["close"] == "100.123456789012345"
    with pytest.raises(ValueError, match="checksum"):
        restore([dict(path=path.name, checksum="bad")], 0, 999999)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == parts[0]["checksum"]
