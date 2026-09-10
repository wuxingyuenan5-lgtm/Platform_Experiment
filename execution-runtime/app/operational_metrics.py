"""Local Prometheus instrumentation; no venue reads or journal mutation on scrape."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from prometheus_client.core import GaugeMetricFamily

from app.config import get_settings

VENUE_REQUEST_SECONDS = Histogram(
    "vg_runtime_venue_request_seconds",
    "One SDK or Worker attempt including failures",
    ("venue", "operation", "outcome"),
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 15, 60),
)
WORKER_STARTS = Counter("vg_runtime_mt5_worker_starts", "MT5 process starts", ("account",))
WORKER_READY = Gauge(
    "vg_runtime_mt5_worker_ready", "Identity-verified Worker process is alive", ("account",)
)


class JournalCollector:
    def describe(self):
        return []

    def collect(self):
        available = GaugeMetricFamily(
            "vg_runtime_metrics_journal_available", "Existing Runtime journal can be read"
        )
        try:
            path = Path(get_settings().journal_path).resolve()
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
                rows = db.execute(
                    "SELECT status, COUNT(*), MIN(created_at) FROM runtime_commands "
                    "WHERE status IN ('processing','result_unknown') GROUP BY status"
                ).fetchall()
        except (sqlite3.Error, OSError):
            available.add_metric([], 0)
            yield available
            return
        available.add_metric([], 1)
        yield available
        count = GaugeMetricFamily(
            "vg_runtime_pending_commands", "Persisted unresolved commands", labels=["state"]
        )
        oldest = GaugeMetricFamily(
            "vg_runtime_pending_commands_oldest_seconds",
            "Age since command claim",
            labels=["state"],
        )
        by_state = {state: (total, created) for state, total, created in rows}
        now = datetime.now(UTC)
        for state in ("processing", "result_unknown"):
            total, created = by_state.get(state, (0, None))
            age = 0.0
            if created:
                stamp = datetime.fromisoformat(created)
                age = max(0, (now - stamp).total_seconds()) if stamp.tzinfo else float("nan")
            count.add_metric([state], total)
            oldest.add_metric([state], age)
        yield count
        yield oldest


REGISTRY.register(JournalCollector())
router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    # Runtime has no browser-session authority; keep this operational export local.
    if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=403, detail="Runtime metrics require a loopback client")
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})
