"""Restore missing serving candles from verified, already-sealed Parquet parts.

Only INSERTs absent BTC/XAUT linear trade candles in the requested source window.
Existing prices, raw files, capture cursors and all trading tables are untouched.
Receipt-time bounds restrict archive IO; they are not candle observation dates.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database_connection import connection, read_only_connection
from app.strategy_research_repository import assert_sqlite_safe, root_path


def restore(parts, start_ms, end_ms):
    import pyarrow.parquet as pq

    inserted = eligible = 0
    for part in parts:
        path = root_path() / part["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != part["checksum"]:
            raise ValueError("published shard checksum mismatch")
        rows = {}
        table = pq.read_table(
            path,
            columns=["event_json"],
            filters=[("layer", "=", "derived"), ("kind", "=", "historical_candle")],
        )
        for item in table.to_pylist():
            row = json.loads(item["event_json"])
            if (
                row.get("quality")
                or row.get("category") != "linear"
                or row.get("symbol") not in {"BTCUSDT", "XAUTUSDT"}
                or row.get("priceType") != "trade"
                or int(row.get("intervalMs", 0)) != 60000
            ):
                continue
            stamp = int(row["closeTimeMs"])
            if start_ms <= stamp <= end_ms:
                key = ("historical_candle", f"{row['symbol']}:linear:trade", stamp)
                rows[key] = json.dumps(row, separators=(",", ":"))
        if rows:
            eligible += len(rows)
            with connection() as db:
                assert_sqlite_safe(db)
                before = db.total_changes
                db.executemany(
                    "INSERT INTO research_strategy_projection VALUES(?,?,?,?) "
                    "ON CONFLICT(kind,entity,at_ms) DO NOTHING",
                    [(*key, payload) for key, payload in rows.items()],
                )
                inserted += db.total_changes - before
    return {"parts": len(parts), "eligible": eligible, "inserted": inserted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("start", "end", "received-start", "received-end"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    start, end, received_start, received_end = [
        datetime.fromisoformat(value)
        for value in (args.start, args.end, args.received_start, args.received_end)
    ]
    if any(value.utcoffset() is None for value in (start, end, received_start, received_end)):
        raise ValueError("all bounds require timezones")
    if start > end or received_start > received_end:
        raise ValueError("invalid window")
    with read_only_connection() as db:
        parts = [
            dict(row)
            for row in db.execute(
                "SELECT path,checksum FROM research_strategy_parts WHERE first_at<=? "
                "AND last_at>=? ORDER BY rowid",
                (received_end.isoformat(), received_start.isoformat()),
            )
        ]
    print(json.dumps(restore(parts, int(start.timestamp() * 1000), int(end.timestamp() * 1000))))


if __name__ == "__main__":
    main()
