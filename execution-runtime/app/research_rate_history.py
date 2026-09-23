"""Bounded funding pagination; progress is saved only after capture fsync."""

import json
import os
import time


def capture_funding_history(client, spool, symbol, days):
    path = spool.root / ("funding-" + symbol + ".json")
    state = json.loads(path.read_text()) if path.exists() else {}
    now_ms = time.time_ns() // 1_000_000
    floor = state.get("floor", now_ms - days * 86400000)
    end = state.get("end", now_ms)
    complete = state.get("complete", False)
    for _ in range(1 if complete else 4):
        arguments = {"category": "linear", "symbol": symbol, "limit": 200}
        if not complete:
            arguments.update(endTime=end, startTime=floor)
        history = client.get_funding_rate_history(**arguments)
        rows = history.get("result", {}).get("list", [])
        if history.get("retCode") != 0:
            raise ValueError("funding history rejected")
        accepted = spool.capture(
            "funding_settlements",
            f"bybit:linear:{symbol}",
            "public",
            history,
            mode="backfill",
            source_layer="rest_paginated",
        )
        if not accepted:
            return
        deadline = time.monotonic() + 5
        while spool.durable_sequence < accepted and not spool.error:
            if time.monotonic() > deadline:
                raise TimeoutError("funding capture is not durable")
            time.sleep(0.02)
        if spool.error:
            raise OSError("funding capture paused")
        if complete:
            return
        oldest = min((int(row["fundingRateTimestamp"]) for row in rows), default=floor)
        finished = not rows or len(rows) < 200 or oldest <= floor
        if oldest > end:
            raise ValueError("funding pagination did not move backwards")
        end = oldest - 1
        temp = path.with_suffix(".pending")
        with temp.open("w") as file:
            file.write(json.dumps({"floor": floor, "end": end, "complete": finished}))
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
        if finished:
            return
