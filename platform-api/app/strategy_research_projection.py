"""Rebuildable serving data, incrementally projected from sealed research shards.

Raw events remain in Parquet. SQLite contains minute observations and spread
seconds only. A crash before cursor publication replays idempotent upserts.
No HTTP read rebuilds this projection or contacts a venue.
"""

import hashlib
import json
from collections import Counter
from decimal import Decimal

from app.database_connection import connection, read_only_connection
from app.strategy_research_repository import assert_sqlite_safe, now, root_path
from app.strategy_research_series import quantile, seconds_series, time_ms

# The funding page currently exposes these paired instruments.  Keeping the
# list in the projection worker (rather than in the Web client) makes the
# persisted basis read model the single owner of the supported universe.
FUNDING_BASIS_SYMBOLS = ("XAUT", "BTC", "ETH", "CRCL", "MSTR")


def read_projection(
    kind, entity=None, start=0, end=9223372036854775807, interval_ms=None, limit=None
):
    clauses, args = ["kind=?", "at_ms>=?", "at_ms<=?"], [kind, start, end]
    if entity is not None:
        clauses.append("entity=?")
        args.append(entity)
    with read_only_connection() as db:
        where = " AND ".join(clauses)
        if interval_ms:
            rows = db.execute(
                "SELECT p.payload_json FROM ("
                "SELECT entity,MAX(at_ms) AS at_ms FROM research_strategy_projection WHERE "
                + where
                + " GROUP BY entity, (at_ms-1)/?) b CROSS JOIN research_strategy_projection p "
                "WHERE p.kind=? "
                "AND p.entity=b.entity AND p.at_ms=b.at_ms ORDER BY p.at_ms,p.entity",
                [*args, interval_ms, kind],
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT payload_json FROM research_strategy_projection WHERE "
                + where
                + " ORDER BY at_ms,entity LIMIT ?",
                [*args, limit if limit is not None else -1],
            ).fetchall()
    return [json.loads(r[0]) for r in rows]


def price_coverage(symbol, start, end):
    with read_only_connection() as db:
        r = db.execute(
            "SELECT COUNT(*),MIN(at_ms),MAX(at_ms) FROM research_strategy_projection "
            "WHERE kind='historical_candle' AND entity IN (?,?) AND at_ms BETWEEN ? AND ?",
            (symbol + ":linear:trade", symbol + ":spot:trade", start, end),
        ).fetchone()
    return {
        "count": r[0],
        "start": str(r[1]) if r[1] is not None else None,
        "end": str(r[2]) if r[2] is not None else None,
    }


def projection_status():
    with read_only_connection() as db:
        row = db.execute(
            "SELECT part_rowid,updated_at FROM research_strategy_projection_cursor WHERE id=1"
        ).fetchone()
        last = db.execute("SELECT COALESCE(MAX(rowid),0) FROM research_strategy_parts").fetchone()[
            0
        ]
    return {
        "processedParts": row[0] if row else 0,
        "publishedParts": last,
        "updatedAt": row[1] if row else None,
        "caughtUp": (row[0] if row else 0) == last,
    }


def funding_basis_status():
    with read_only_connection() as db:
        row = db.execute(
            "SELECT last_at_ms,completed,updated_at FROM funding_basis_projection_cursor WHERE id=1"
        ).fetchone()
    return {
        "lastAtMs": str(row[0]) if row else None,
        "completed": bool(row[1]) if row else False,
        "updatedAt": row[2] if row else None,
    }


def project_candle_next():
    """Project closed BTC/XAUT candles without waiting on spread replay.

    The strategy archive also contains high-volume order-book events.  The
    hedge-board cumulative producer only needs the already-derived one-minute
    candles, so it gets a small independent cursor and can stay fresh while
    the full spread projection catches up.
    """
    with connection() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS research_strategy_candle_cursor "
            "(id INTEGER PRIMARY KEY CHECK(id=1), part_rowid INTEGER NOT NULL, "
            "updated_at TEXT NOT NULL)"
        )
        checkpoint = db.execute(
            "SELECT part_rowid FROM research_strategy_candle_cursor WHERE id=1"
        ).fetchone()
        cursor = checkpoint[0] if checkpoint else 0
        # The full projection already writes the same candle rows.  On first
        # enable, skip its completed prefix instead of replaying every shard.
        full_checkpoint = db.execute(
            "SELECT part_rowid FROM research_strategy_projection_cursor WHERE id=1"
        ).fetchone()
        if full_checkpoint:
            cursor = max(cursor, full_checkpoint[0])
        part = db.execute(
            "SELECT rowid AS ordinal,* FROM research_strategy_parts "
            "WHERE rowid>? ORDER BY rowid LIMIT 1",
            (cursor,),
        ).fetchone()
    if part is None:
        return False
    path = root_path() / part["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != part["checksum"]:
        raise ValueError("published shard checksum mismatch")
    import pyarrow.parquet as pq

    table = pq.read_table(path, columns=["layer", "kind", "event_json"])
    values = {}
    for item in table.to_pylist():
        if item["layer"] != "derived" or item["kind"] != "historical_candle":
            continue
        row = json.loads(item["event_json"])
        if (
            row.get("priceType") != "trade"
            or row.get("quality")
            or int(row.get("intervalMs", 0)) != 60000
            or row.get("symbol") not in {"BTCUSDT", "XAUTUSDT"}
            or row.get("category") != "linear"
        ):
            continue
        entity = f"{row['symbol']}:{row['category']}:{row['priceType']}"
        values[("historical_candle", entity, int(row["closeTimeMs"]))] = json.dumps(
            row, separators=(",", ":")
        )
    with connection() as db:
        assert_sqlite_safe(db)
        if values:
            db.executemany(
                "INSERT INTO research_strategy_projection VALUES(?,?,?,?) "
                "ON CONFLICT(kind,entity,at_ms) DO UPDATE SET payload_json=excluded.payload_json",
                [
                    (kind, entity, stamp, payload)
                    for (kind, entity, stamp), payload in values.items()
                ],
            )
        db.execute(
            "INSERT INTO research_strategy_candle_cursor VALUES(1,?,?) "
            "ON CONFLICT(id) DO UPDATE SET part_rowid=excluded.part_rowid,"
            "updated_at=excluded.updated_at",
            (part["ordinal"], now()),
        )
    return True


def project_next():
    with connection() as db:
        checkpoint = db.execute(
            "SELECT * FROM research_strategy_projection_cursor WHERE id=1"
        ).fetchone()
        cursor = checkpoint["part_rowid"] if checkpoint else 0
        part = db.execute(
            "SELECT rowid AS ordinal,* FROM research_strategy_parts "
            "WHERE rowid>? ORDER BY rowid LIMIT 1",
            (cursor,),
        ).fetchone()
    if part is None:
        return False
    state = json.loads(checkpoint["state_json"]) if checkpoint else {}
    # Read each sealed shard once.  The old implementation scanned the same
    # Parquet file twice (derived rows, then raw market_scan rows), which made
    # projection throughput roughly equal to live publication and left the
    # cumulative-volatility producer permanently behind.
    import pyarrow.parquet as pq

    path = root_path() / part["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != part["checksum"]:
        raise ValueError("published shard checksum mismatch")
    table = pq.read_table(
        path,
        columns=["layer", "kind", "event_json"],
        # Raw order-book JSON is retained in the archive but is not an input
        # to this projection. Filter in Arrow before converting/decoding it.
        filters=[[("layer", "=", "derived")],
                 [("layer", "=", "raw"), ("kind", "=", "market_scan")]],
    )
    rows = []
    market_scan_rows = []
    for item in table.to_pylist():
        event = json.loads(item["event_json"])
        if item["layer"] == "derived":
            rows.append(event)
        elif item["layer"] == "raw" and item["kind"] == "market_scan":
            market_scan_rows.append(event)
    # The original raw scan includes perpetuals without a spot listing too.
    # Reuse that evidence for the funding catalog (never invent a paired market).
    for event in market_scan_rows:
        for item in event["payload"].get("linearTickers", {}).get("result", {}).get("list", []):
            if item.get("fundingRate") not in (None, ""):
                rows.append(
                    {
                        "kind": "funding_scan",
                        "payload": item,
                        "receivedAt": event["runtimeReceivedAt"],
                    }
                )
    updates = {}
    candle_payloads = {}
    candle_stamps = {}

    def put(kind, entity, stamp, payload):
        updates[(kind, entity, int(stamp))] = json.dumps(payload, separators=(",", ":"))

    spreads = {}
    rows.sort(key=lambda r: time_ms(r["receivedAt"]))
    for r in rows:
        kind = r["kind"]
        if kind == "historical_candle":
            if int(r["intervalMs"]) == 60000 and not r.get("quality") and r["priceType"] == "trade":
                entity = r["symbol"] + ":" + r["category"] + ":" + r["priceType"]
                put(kind, entity, r["closeTimeMs"], r)
                symbol_base = str(r["symbol"]).removesuffix("USDT")
                if symbol_base in FUNDING_BASIS_SYMBOLS and r["category"] in {"spot", "linear"}:
                    stamp = int(r["closeTimeMs"])
                    candle_payloads[(entity, stamp)] = r
                    candle_stamps.setdefault(symbol_base, set()).add(stamp)
        elif kind == "mt5_history_quote":
            put(kind, "cross-gold", int(r["sourceTimeMs"]) // 60000 * 60000, r)
        elif kind == "funding_settlement":
            put(kind, r["payload"]["symbol"], r["payload"]["fundingRateTimestamp"], r)
        elif kind in ("funding_scan", "funding_indication"):
            symbol = r["payload"]["symbol"]
            put("funding_latest", symbol, 0, r)
            # Rates do not need tick frequency; retain last observed value per minute.
            if kind == "funding_indication":
                put("funding_minute", symbol, time_ms(r["receivedAt"]) // 60000 * 60000, r)
        elif kind == "borrow_profile":
            put(kind, "Bybit", time_ms(r.get("observedAt") or r["receivedAt"]) // 60000 * 60000, r)
        elif kind == "spread":
            spreads.setdefault(r["pairId"], []).append(r)
    for pair, events in spreads.items():
        previous = state.get(pair, {"events": [], "rewriteFrom": 0})
        tail = previous["events"]
        events = tail + events
        # Recompute the last two seconds with the next sealed shard, so durations
        # spanning a shard boundary equal a single chronological derivation.
        boundary = time_ms(events[-1]["receivedAt"]) // 1000 * 1000 - 2000
        for view in ("valid", "all"):
            for second in seconds_series(events, valid_only=view == "valid"):
                if int(second["timeMs"]) >= previous["rewriteFrom"]:
                    put("spread_" + view, pair, second["timeMs"], second)
        for e in events[len(tail) :]:
            put("spread_latest", pair, 0, e)
        # Keep all events in the trailing seconds plus their immediate predecessor.
        first = next(
            (i for i, e in enumerate(events) if time_ms(e["receivedAt"]) >= boundary),
            len(events) - 1,
        )
        state[pair] = {"events": events[max(0, first - 1) :], "rewriteFrom": boundary}

    # Derive candle-based funding basis in the serving projection itself.  The
    # incoming shard may contain only one leg; merge it with already-persisted
    # candles so a leg split across shards still produces exactly one point.
    if candle_stamps:
        entities = [
            f"{base}USDT:{category}:trade"
            for base in candle_stamps
            for category in ("spot", "linear")
        ]
        lo = min(stamp for stamps in candle_stamps.values() for stamp in stamps)
        hi = max(stamp for stamps in candle_stamps.values() for stamp in stamps)
        placeholders = ",".join("?" for _ in entities)
        with read_only_connection() as db:
            existing = db.execute(
                "SELECT entity,at_ms,payload_json FROM research_strategy_projection "
                "WHERE kind='historical_candle' AND entity IN ("
                + placeholders
                + ") AND at_ms BETWEEN ? AND ?",
                [*entities, lo, hi],
            ).fetchall()
        candles = {
            (row["entity"], int(row["at_ms"])): json.loads(row["payload_json"])
            for row in existing
        }
        candles.update(candle_payloads)
        for symbol_base, stamps in candle_stamps.items():
            linear_entity = f"{symbol_base}USDT:linear:trade"
            spot_entity = f"{symbol_base}USDT:spot:trade"
            for stamp in sorted(stamps):
                linear = candles.get((linear_entity, stamp))
                spot = candles.get((spot_entity, stamp))
                if not linear or not spot:
                    continue
                try:
                    linear_close = Decimal(str(linear["close"]))
                    spot_close = Decimal(str(spot["close"]))
                except (KeyError, TypeError, ValueError):
                    continue
                if (
                    not linear_close.is_finite()
                    or not spot_close.is_finite()
                    or linear_close <= 0
                    or spot_close <= 0
                ):
                    continue
                put(
                    "funding_basis",
                    symbol_base,
                    stamp,
                    {
                        "timeMs": str(stamp),
                        "validDurationMs": 60000,
                        "quality": [],
                        "ohlc": {
                            "midSpread": {"close": str(linear_close - spot_close)}
                        },
                        "basisSource": "same_bucket_historical_closes",
                        "linearClose": str(linear_close),
                        "spotClose": str(spot_close),
                    },
                )
    values = [(k, e, t, p) for (k, e, t), p in updates.items()]
    # Bounded short transactions; cursor advances only after every upsert is durable.
    for offset in range(0, len(values), 500):
        with connection() as db:
            assert_sqlite_safe(db)
            db.executemany(
                "INSERT INTO research_strategy_projection VALUES(?,?,?,?) "
                "ON CONFLICT(kind,entity,at_ms) DO UPDATE SET payload_json=excluded.payload_json",
                values[offset : offset + 500],
            )
    with connection() as db:
        db.execute(
            "INSERT INTO research_strategy_projection_cursor VALUES(1,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET part_rowid=excluded.part_rowid,"
            "state_json=excluded.state_json,updated_at=excluded.updated_at",
            (part["ordinal"], json.dumps(state), now()),
        )
    return True


def project_funding_basis_next(batch_size: int = 5000):
    """Backfill paired candle basis that predates the serving worker.

    The normal shard projector handles newly arriving candles, including legs
    split over adjacent shards.  This bounded join brings the already-built
    historical candle projection into the same ``funding_basis`` read model
    after an upgrade, without scanning the archive or doing arithmetic in an
    HTTP request.
    """
    entities = [
        f"{base}USDT:{category}:trade"
        for base in FUNDING_BASIS_SYMBOLS
        for category in ("spot", "linear")
    ]
    placeholders = ",".join("?" for _ in entities)
    with connection() as db:
        cursor = db.execute(
            "SELECT last_at_ms,completed FROM funding_basis_projection_cursor WHERE id=1"
        ).fetchone()
        if cursor and cursor[1]:
            return False
        last_at_ms = int(cursor[0]) if cursor else 0
        pairs = db.execute(
            "SELECT l.at_ms,l.payload_json AS linear_json,s.payload_json AS spot_json "
            "FROM research_strategy_projection l "
            "JOIN research_strategy_projection s ON s.kind='historical_candle' "
            "AND s.at_ms=l.at_ms AND s.entity=replace(l.entity,':linear:',':spot:') "
            "WHERE l.kind='historical_candle' AND l.entity IN ("
            + placeholders
            + ") AND l.entity LIKE '%:linear:trade' AND l.at_ms>? "
            "ORDER BY l.at_ms LIMIT ?",
            [*entities, last_at_ms, batch_size],
        ).fetchall()
        if not pairs:
            projection = db.execute(
                "SELECT part_rowid FROM research_strategy_projection_cursor WHERE id=1"
            ).fetchone()
            published = db.execute(
                "SELECT COALESCE(MAX(rowid),0) FROM research_strategy_parts"
            ).fetchone()[0]
            completed = bool(projection and projection[0] >= published)
            db.execute(
                "INSERT INTO funding_basis_projection_cursor(id,last_at_ms,completed,updated_at) "
                "VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET completed=excluded.completed,"
                "updated_at=excluded.updated_at",
                (last_at_ms, int(completed), now()),
            )
            return False
        values = []
        max_at_ms = last_at_ms
        for pair in pairs:
            stamp = int(pair["at_ms"])
            max_at_ms = max(max_at_ms, stamp)
            try:
                linear = json.loads(pair["linear_json"])
                spot = json.loads(pair["spot_json"])
                linear_close = Decimal(str(linear["close"]))
                spot_close = Decimal(str(spot["close"]))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if (
                not linear_close.is_finite()
                or not spot_close.is_finite()
                or linear_close <= 0
                or spot_close <= 0
            ):
                continue
            symbol_base = str(linear["symbol"]).removesuffix("USDT")
            payload = {
                "timeMs": str(stamp),
                "validDurationMs": 60000,
                "quality": [],
                "ohlc": {"midSpread": {"close": str(linear_close - spot_close)}},
                "basisSource": "same_bucket_historical_closes",
                "linearClose": str(linear_close),
                "spotClose": str(spot_close),
            }
            values.append(
                ("funding_basis", symbol_base, stamp, json.dumps(payload, separators=(",", ":")))
            )
        if values:
            db.executemany(
                "INSERT INTO research_strategy_projection VALUES(?,?,?,?) "
                "ON CONFLICT(kind,entity,at_ms) DO UPDATE SET payload_json=excluded.payload_json",
                values,
            )
        db.execute(
            "INSERT INTO funding_basis_projection_cursor(id,last_at_ms,completed,updated_at) "
            "VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET last_at_ms=excluded.last_at_ms,"
            "updated_at=excluded.updated_at",
            (max_at_ms, 0, now()),
        )
    return True


def second_statistics(rows, all_rows):
    values = [
        Decimal(r["ohlc"]["midSpread"]["close"])
        for r in rows
        if r["validDurationMs"] > 0 and r["ohlc"].get("midSpread")
    ]
    bins = []
    if values:
        lo, hi = min(values), max(values)
        width = (hi - lo) / 12 if hi != lo else Decimal(1)
        counts = [0] * 12
        for value in values:
            counts[min(11, int((value - lo) / width))] += 1
        bins = [{"label": str(lo + i * width), "count": n} for i, n in enumerate(counts)]
    return {
        "sampling": "equal_1s_close",
        "quantileMethod": "linear_R7",
        "sampleCount": len(values),
        "p10": quantile(values, ".1"),
        "p50": quantile(values, ".5"),
        "p90": quantile(values, ".9"),
        "validDurationMs": str(sum(r["validDurationMs"] for r in rows)),
        "exclusions": dict(Counter(q for r in all_rows for q in r.get("quality", []))),
        "exclusionUnit": "seconds",
        "histogram": bins,
    }


def history_chart(prices, settlements, broker, display_ms, funding_indications=None):
    groups = {}
    for p in prices:
        key = p["stream"]
        group = groups.setdefault(
            key,
            {
                "name": p["symbol"] + (" 现货收盘" if p["category"] == "spot" else " 永续收盘"),
                "type": "line",
                "selected": p["category"] != "spot",
                "axis": 0,
                "data": [],
            },
        )
        values = group["data"]
        at = int(p["closeTimeMs"])
        if values and at - values[-1]["value"][0] > display_ms:
            values.append({"value": [values[-1]["value"][0] + 1, None]})
        values.append({"value": [at, p["close"]], "exactPrice": p["close"]})
    chart = list(groups.values())
    if funding_indications:
        chart.append(
            {
                "name": "指标资金费率（%）",
                "type": "bar",
                "axis": 1,
                "selected": True,
                "data": [
                    {
                        "value": [
                            int(time_ms(item["at"])),
                            str(Decimal(item["rate"]) * 100),
                        ]
                    }
                    for item in funding_indications
                ],
            }
        )
    if settlements:
        chart.append(
            {
                "name": "已结算资金费率（%）",
                "type": "bar",
                "axis": 1,
                "selected": True,
                "data": [
                    {
                        "value": [
                            int(r["payload"]["fundingRateTimestamp"]),
                            str(Decimal(r["payload"]["fundingRate"]) * 100),
                        ]
                    }
                    for r in settlements
                ],
            }
        )
    if broker:
        chart.append(
            {
                "name": "MT5 历史 Bid（时钟未验证）",
                "type": "scatter",
                "axis": 0,
                "selected": True,
                "data": [
                    {"value": [int(r["sourceTimeMs"]), r["bid"]], "exactPrice": r["bid"]}
                    for r in broker
                ],
            }
        )
    return chart


def spread_chart(rows):
    series = []
    for key, name in (("midSpread", "中间价差"), ("buySpread", "买价差"), ("sellSpread", "卖价差")):
        points = []
        previous = None
        for row in rows:
            at = int(row["timeMs"])
            if previous is not None and at - previous > 1000:
                points.append({"value": [previous + 1000, None]})
            value = row["ohlc"].get(key, {}).get("close")
            points.append({"value": [at, value], "exactPrice": value})
            previous = at
        series.append(
            {
                "name": name,
                "type": "line",
                "axis": 0,
                "selected": key == "midSpread",
                "data": points,
            }
        )
    return series
