"""Backfill the Platform A-share pool's daily close history from public K-lines.

The pool definition is read from Platform SQLite.  This script never calls the
reference application and only commits when every instrument with a supported
public symbol has returned a usable series.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.database import initialize_database
from app.research_a_share_repository import (
    finish_refresh,
    read_stock_pool,
    start_refresh,
    write_history_points,
)
from app.research_provider_a_share import AShareResearchProvider
from app.research_providers import USER_AGENT, _akshare


async def _collect(codes: list[str]) -> dict[str, list[object]]:
    provider = AShareResearchProvider(
        timeout_seconds=12.0,
        user_agent=USER_AGENT,
        akshare_loader=_akshare,
    )
    return await provider.stock_daily_histories(codes)


def main() -> None:
    initialize_database()
    pool = read_stock_pool() or {}
    codes = list(
        dict.fromkeys(
            str(row.get("code") or "").strip()
            for row in pool.get("stocks") or []
            if str(row.get("code") or "").strip()
        )
    )
    if not codes:
        raise SystemExit("no Platform stock-pool definition exists; import a pool before backfill")
    histories = asyncio.run(_collect(codes))
    missing = sorted(set(codes) - set(histories))
    if missing:
        raise SystemExit(f"stock history incomplete; no rows written: {', '.join(missing[:20])}")

    run_id = f"a-share-stock-history-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    start_refresh(run_id, None)
    rows: list[tuple[str, str, dict[str, object]]] = []
    for code, points in histories.items():
        for point in points:
            rows.append(
                (
                    point.observed_at.isoformat(),
                    code,
                    {"close": point.close, "turnoverYuan": point.turnover_yuan},
                )
            )
    try:
        write_history_points(
            run_id,
            "stock",
            rows,
            source="tencent-public-adjusted-daily-kline",
        )
        finish_refresh(
            run_id, "ready", message=f"historical stock close backfill: {len(rows)} rows"
        )
    except Exception as exc:
        finish_refresh(run_id, "error", error_code=type(exc).__name__, message=str(exc)[:500])
        raise
    print(f"backfilled codes={len(histories)} rows={len(rows)}")


if __name__ == "__main__":
    main()
