"""Collect Platform-owned daily history for the eight A-share dashboard indexes.

The collector talks directly to the public Tencent and Eastmoney quote hosts;
it never imports or calls the Vibe application.  It is safe to run repeatedly:
rows are keyed by date and index code and are upserted in one transaction.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from app.database import connection, initialize_database
from app.research_provider_a_share import AShareResearchProvider
from app.research_providers import USER_AGENT


async def collect() -> list[object]:
    provider = AShareResearchProvider(
        timeout_seconds=12.0,
        user_agent=USER_AGENT,
        akshare_loader=lambda: __import__("akshare"),
    )
    return await provider.index_snapshots()


def main() -> None:
    snapshots = asyncio.run(collect())
    missing = sorted(
        {"000300", "000852", "399006", "000688", "931071", "931238", "932082", "H30590"}
        - {item.code for item in snapshots}
    )
    if missing:
        raise SystemExit(f"index history incomplete; no rows written for: {', '.join(missing)}")

    initialize_database()
    run_id = f"a-share-index-history-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            "INSERT INTO research_a_share_refresh_runs"
            "(run_id,started_at,finished_at,status,message) VALUES (?,?,?,?,?)",
            (run_id, now, now, "ready", "explicit Platform index-history collection"),
        )
        for snapshot in snapshots:
            source = (
                "tencent-public-kline"
                if snapshot.code in {"000300", "000852", "399006", "000688"}
                else "eastmoney-public-index-kline"
            )
            for point in snapshot.history:
                payload = point.model_dump(mode="json", by_alias=True)
                db.execute(
                    """INSERT INTO research_a_share_history
                    (dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)
                    VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code)
                    DO UPDATE SET payload_json=excluded.payload_json,source=excluded.source,
                    fetched_at=excluded.fetched_at,refresh_run_id=excluded.refresh_run_id""",
                    (
                        "index",
                        point.observed_at.isoformat(),
                        snapshot.code,
                        json.dumps(payload, ensure_ascii=False),
                        source,
                        now,
                        run_id,
                    ),
                )
    print("collected " + ", ".join(f"{item.code}={len(item.history)}" for item in snapshots))


if __name__ == "__main__":
    main()
