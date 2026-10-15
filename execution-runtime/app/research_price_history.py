"""Bounded public closed-candle history with a durable restart cursor."""

import json
import os
import time

INTERVAL_MS = 60 * 1000
DAILY_SPOT_STREAMS = (("spot", "BTCUSDT", "trade"), ("spot", "ETHUSDT", "trade"))
# ETF history starts in 2024; daily resolution avoids extending minute backfills.
DAILY_HISTORY_DAYS = 1200

STREAMS = (
    ("linear", "BTCUSDT", "trade"),
    ("spot", "BTCUSDT", "trade"),
    ("linear", "XAUTUSDT", "trade"),
    ("linear", "BTCUSDT", "mark"),
    ("linear", "XAUTUSDT", "mark"),
)


def checkpoint(path, state):
    temp = path.with_suffix(".pending")
    with temp.open("w") as f:
        json.dump(state, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def durable(spool, sequence):
    if not sequence:
        raise OSError("history capture refused")
    deadline = time.monotonic() + 10
    while spool.durable_sequence < sequence:
        if spool.error:
            raise OSError("history spool paused")
        if time.monotonic() > deadline:
            raise TimeoutError("history capture fsync timeout")
        time.sleep(0.02)


def capture_prices(client, spool, category, symbol, price_type, days=30, *, interval="1"):
    interval_ms = {"1": INTERVAL_MS, "D": 86400000}[interval]
    resolution = "1m" if interval == "1" else "1d"
    # Resolution is part of cursor identity; a prior overview cannot skip finer history.
    path = spool.root / f"price-{category}-{symbol}-{price_type}-{resolution}.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    server = client.get_server_time()
    if server.get("retCode") != 0:
        raise ValueError("history clock unavailable")
    now_ms = int(server["result"]["timeNano"]) // 1000000
    last_closed = now_ms // interval_ms * interval_ms - interval_ms
    requested_floor = last_closed - days * 86400000 + interval_ms
    floor = int(state.get("floor", requested_floor))
    if requested_floor < floor:
        # A longer retention setting must backfill backwards from the newly
        # requested floor. Reusing the old forward cursor would incorrectly
        # report the stream as complete and leave the archive at its old age.
        floor = requested_floor
        state = {
            **state,
            "floor": floor,
            "through": floor - interval_ms,
            "complete": False,
        }
    # Initial history moves forward, so the same cursor naturally catches up later.
    after = state.get("through", floor - interval_ms)
    if after >= last_closed:
        return state
    start = after + interval_ms
    end = min(last_closed, start + 999 * interval_ms)
    method = client.get_mark_price_kline if price_type == "mark" else client.get_kline
    response = method(
        category=category, symbol=symbol, interval=interval, start=start, end=end, limit=1000
    )
    if response.get("retCode") != 0:
        raise ValueError("historical prices rejected")
    rows = response.get("result", {}).get("list", [])
    try:
        outside_window = any(not start <= int(row[0]) <= end for row in rows)
    except (ValueError, TypeError, IndexError):
        outside_window = True
    sequence = spool.capture(
        "price_history",
        f"bybit:{category}:{symbol}:{price_type}:{resolution}",
        "public",
        {
            "category": category,
            "symbol": symbol,
            "priceType": price_type,
            "intervalMs": str(interval_ms),
            "requestedFromMs": str(start),
            "requestedThroughMs": str(end),
            "response": response,
        },
        mode="backfill",
        source_layer="rest_closed_candle",
        quality=["source_window_invalid"] if outside_window else [],
    )
    durable(spool, sequence)
    if outside_window:
        # Retain the rejected source payload; retry this window without advancing.
        raise ValueError("history returned outside requested closed interval")
    state = {
        "floor": floor,
        "through": end,
        "complete": end >= last_closed,
        "returnedRows": len(rows),
        "intervalMs": interval_ms,
        "totalRows": state.get("totalRows", 0) + len(rows),
        "emptyWindows": state.get("emptyWindows", 0) + (not rows),
        "lastReceivedAtMs": str(time.time_ns() // 1000000),
    }
    checkpoint(path, state)
    return state
