"""Isolated browser test host. Adapter fixtures are never imported by app code."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

from a_share_fixture import CODES, AShareFixtureProvider
from fastapi import Depends

from app import auth
from app import research_a_share_refresh as refresh
from app import research_a_share_repository as repository
from app import research_service as service
from app.application import create_application
from app.auth import require_permission
from app.database import connection
from scripts.seed_hedge_board_e2e import main as seed

seed()  # Refuses existing files and paths outside the test root.
provider = AShareFixtureProvider()
refresh._PROVIDER = provider
service._PROVIDER = provider
with connection() as db:
    db.execute(
        "INSERT INTO research_a_share_pool_config VALUES(1,?,1,?)",
        (json.dumps(CODES), datetime.now(UTC).isoformat()),
    )
asyncio.run(refresh.refresh_a_share_research(force=True))
run_id = repository.read_refresh_status()["runId"]
points = provider.history("600519")
repository.write_history_points(
    run_id,
    "market",
    [
        (
            str(point.observed_at),
            "market",
            {
                "up": 2500 + i,
                "down": 2000 - i,
                "flat": 100,
                "limitUp": 30 + i % 15,
                "limitDown": 5 + i % 3,
                "totalAmountYuan": (12000 + i * 10) * 100000000,
                "marketBreadthPct": 10 + i / 5,
            },
        )
        for i, point in enumerate(points[:-1])
    ],
    source="isolated deterministic fixture",
)
crowding = repository.read_dataset("crowding")
crowding["history"] = [{**crowding["latest"], "date": str(point.observed_at)} for point in points]
crowding["innovationHistory"] = [
    {
        "date": str(point.observed_at),
        "turnoverPct": 1.5 + i / 100,
        "amount100m": 300 + i,
        "amountShareOfA": 0.03 + i / 10000,
    }
    for i, point in enumerate(points)
]
repository.write_dataset(
    "crowding",
    crowding,
    source="isolated deterministic fixture",
    run_id=run_id,
    observed_at=str(points[-1].observed_at),
)
repository.write_history_points(
    run_id,
    "hot_stock",
    [(str(point.observed_at), "__day__", {}) for point in points[-10:-1]],
    source="isolated deterministic fixture",
)
production_permission = auth.permission_for_request
auth.permission_for_request = lambda method, path: (
    "research.write" if path == "/api/v1/__test__/provider" else production_permission(method, path)
)
app = create_application()


@app.post("/api/v1/__test__/provider", dependencies=[Depends(require_permission("research.write"))])
async def set_provider(body: dict):
    if body.get("mode") not in {"ready", "partial", "error", "missing_value"}:
        return {"error": "invalid fixture mode"}
    provider.mode = body["mode"]
    provider.delay = 0.1
    for cache, key in (
        (service._LIVE_SECTOR_FLOW_CACHE, "a-share-live-sector-fund-flow"),
        (service._LIVE_TURNOVER_CACHE, "a-share-live-market-turnover"),
    ):
        entry = cache.get(key)
        if entry:
            cache.store(key, entry.value, fetched_at=datetime.now(UTC) - timedelta(minutes=6))
    return {"mode": provider.mode}
