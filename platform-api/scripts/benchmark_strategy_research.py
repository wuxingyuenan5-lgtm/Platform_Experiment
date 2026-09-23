"""Explicitly synthetic offline pressure test, never real market coverage."""

import importlib.util
import json
import sqlite3
import sys
import threading
import time
import tracemalloc
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "platform-api"))
from app.config import get_settings  # noqa: E402
from app.database import initialize_database  # noqa: E402
from app.strategy_research_repository import backup, publish  # noqa: E402
from app.strategy_research_series import quantile  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "isolated_market_spool", root / "execution-runtime/app/market_spool.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
out = root / "platform-api/data/research-verification" / ("pressure-" + str(time.time_ns()))
out.mkdir(parents=True)
settings = get_settings()
settings.database_path = str(out / "test.db")
settings.strategy_research_path = str(out / "archive")
settings.strategy_research_min_free_bytes = 0
initialize_database()
spool = module.MarketSpool(out / "spool", min_free_bytes=0, queue_size=20000)
spool.start()
latencies = []
stop = threading.Event()


def read_business():
    while not stop.is_set():
        start = time.perf_counter()
        with sqlite3.connect(settings.database_path) as db:
            db.execute("SELECT count(*) FROM trade_commands").fetchone()
        latencies.append((time.perf_counter() - start) * 1000)
        stop.wait(0.01)


reader = threading.Thread(target=read_business)
reader.start()
tracemalloc.start()
wall = time.perf_counter()
cpu = time.process_time()
try:
    for n in range(10000):
        category = "linear" if n % 2 else "spot"
        accepted = spool.capture(
            "bybit_message",
            f"bybit:{category}:orderbook.50.BTCUSDT",
            "public",
            {
                "topic": "orderbook.50.BTCUSDT",
                "type": "snapshot",
                "data": {"s": "BTCUSDT", "u": n + 1, "a": [["102", "10"]], "b": [["101", "10"]]},
            },
            source_ms=time.time_ns() // 1000000,
            source_layer="synthetic_benchmark",
        )
        if not accepted:
            raise RuntimeError(spool.error)
    deadline = time.monotonic() + 20
    while spool.durable_sequence < accepted and time.monotonic() < deadline:
        time.sleep(0.02)
    capture_elapsed = time.perf_counter() - wall
    cursor = None
    batch_seconds = []
    rows = 0
    while True:
        batch = spool.read(cursor, 1000)
        if not batch["events"]:
            break
        started = time.perf_counter()
        publish(batch)
        batch_seconds.append(time.perf_counter() - started)
        rows += len(batch["events"])
        cursor = batch["nextCursor"]
    backup_result = backup(out / "backup")
finally:
    spool.close()
    stop.set()
    reader.join()
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
report = {
    "source": "synthetic_benchmark_not_market_coverage",
    "inputEvents": rows,
    "captureSeconds": capture_elapsed,
    "elapsedSeconds": time.perf_counter() - wall,
    "cpuSeconds": time.process_time() - cpu,
    "peakPythonBytes": peak,
    "archiveBytes": sum(p.stat().st_size for p in (out / "archive").glob("*.parquet")),
    "batchPublishMs": {
        p: quantile([str(v * 1000) for v in batch_seconds], q)
        for p, q in [("p50", ".5"), ("p95", ".95"), ("p99", ".99")]
    },
    "parallelBusinessReadMs": {
        p: quantile([str(v) for v in latencies], q)
        for p, q in [("p50", ".5"), ("p95", ".95"), ("p99", ".99")]
    },
    "backup": backup_result,
    "realTrading": "not_run",
    "realCoverage": "none",
    "measuredSourceLatency": None,
    "soak24Hours": "not_run",
}
(out / "report.json").write_text(json.dumps(report, indent=2))
print(json.dumps({"output": str(out), "report": report}))
