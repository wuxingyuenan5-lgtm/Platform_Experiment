import time

import pytest

from app.market_spool import MarketSpool
from app.research_minute import MinuteHistory


def test_ack_reclaims_only_older_sealed_segments_and_retains_anchor(tmp_path):
    spool = MarketSpool(tmp_path, min_free_bytes=0, segment_bytes=1)
    spool.start()
    try:
        for i in range(5):
            seq = spool.capture("fixture", "fixture", "public", {"i": i})
            deadline = time.monotonic() + 3
            while spool.durable_sequence < seq and time.monotonic() < deadline:
                time.sleep(0.01)
        batch = spool.read(limit=5000)
        cursor = batch["nextCursor"]
        older = [name for name in spool.durable if name < cursor.split(":")[0]]
        assert older
        with pytest.raises(ValueError):
            spool.acknowledge("../escape:0", "a" * 64)
        spool.acknowledge(cursor, "a" * 64)
        assert all(not (tmp_path / name).exists() for name in older)
        assert (tmp_path / cursor.split(":")[0]).exists()
        assert (tmp_path / spool._name).exists()
        assert spool.read(cursor)["events"] == []
        spool.acknowledge(cursor, "a" * 64)  # response lost: retry is safe
        assert spool.reclaimed_bytes > 0
    finally:
        spool.close()
    reopened = MarketSpool(tmp_path, min_free_bytes=0)
    reopened.start()
    try:
        assert all(row["kind"] == "quality" for row in reopened.read(cursor)["events"])
    finally:
        reopened.close()


def test_minute_ohlc_uses_every_update_and_never_subtracts_leg_extrema():
    history = MinuteHistory()
    history.observe("bybit:linear:BTCUSDT", 61000, 61000, "100.000000000001", "101")
    history.observe("bybit:spot:BTCUSDT", 61010, 61010, "90", "91")
    history.observe("bybit:linear:BTCUSDT", 62000, 62000, "120", "121")
    history.observe("bybit:spot:BTCUSDT", 63000, 63000, "110", "111")
    rows = []
    history.flush(119999, lambda row: rows.append(row))
    assert rows == []
    history.flush(122000, lambda row: rows.append(row))
    quote = next(r for r in rows if r["entity"] == "bybit:linear:BTCUSDT")
    assert quote["values"]["bid"] == dict(
        open="100.000000000001", high="120", low="100.000000000001", close="120"
    )
    spread = next(r for r in rows if r["kind"] == "spread_minute")
    assert spread["values"]["buySpread"]["high"] == "31"
    assert spread["count"] == 3
    assert "collector_partial_minute" in spread["quality"]
    history.flush(180000, lambda row: rows.append(row))
    assert len(rows) == 3  # no forward-filled empty minute


def test_invalid_quote_has_explicit_minute_evidence_and_no_prices():
    history = MinuteHistory()
    history.observe("mt5:XAUUSD", 61000, 61000, "nan", "2")
    rows = []
    history.flush(122000, lambda row: rows.append(row))
    assert rows[0]["invalidQuoteCount"] == 1
    assert rows[0]["values"] == {}
    assert "numeric_invalid" in rows[0]["quality"]
