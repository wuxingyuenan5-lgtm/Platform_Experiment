"""Scheduled market snapshots. GET routes never fan out to public providers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.research_a_share_repository import (
    finish_refresh,
    read_dataset,
    read_dataset_metadata,
    start_refresh,
    write_dataset,
)
from app.research_provider_market_detail import (
    MARKET_SYMBOLS,
    MarketDetailProvider,
    MarketDetailResponse,
)
from app.research_write_lock import RESEARCH_DB_WRITE_LOCK

_LOCK = asyncio.Lock()
_PROVIDER = MarketDetailProvider(timeout_seconds=15, user_agent="VariableGlobalResearch/1.0")


async def refresh_market_details(*, force: bool = False) -> dict[str, str]:
    if _LOCK.locked():
        return {"status": "busy"}
    results: dict[str, str] = {}
    async with _LOCK:
        for market_id in MARKET_SYMBOLS:
            dataset = f"market_detail_{market_id}"
            metadata = await asyncio.to_thread(read_dataset_metadata, dataset)
            if not force and metadata:
                try:
                    fetched = datetime.fromisoformat(metadata["fetched_at"])
                    if datetime.now(UTC) - fetched < timedelta(minutes=15):
                        results[market_id] = "up_to_date"
                        continue
                except (ValueError, TypeError):
                    pass
            previous = await asyncio.to_thread(read_dataset, dataset)
            run_id = f"market-detail-{uuid4().hex}"
            async with RESEARCH_DB_WRITE_LOCK:
                await asyncio.to_thread(start_refresh, run_id, None)
            error: Exception | None = None
            try:
                snapshot = await _PROVIDER._get_live_market_detail(market_id)
                # Keep a failed symbol's last observation without relabelling its date.
                present = {row.id for row in snapshot.rows}
                if previous:
                    for row in MarketDetailResponse.model_validate(previous).rows:
                        expected_symbol = MARKET_SYMBOLS[market_id].get(row.id)
                        if expected_symbol and row.symbol != expected_symbol.replace("%5E", "^"):
                            continue
                        if row.id not in present:
                            row.status = "stale"
                            snapshot.rows.append(row)
                            snapshot.status = "partial"
            except Exception as exc:
                error = exc
                snapshot = (
                    MarketDetailResponse.model_validate(previous)
                    if previous
                    else MarketDetailResponse(market_id=market_id, status="error")
                )
                snapshot.status = "stale" if snapshot.rows else "error"
                for row in snapshot.rows:
                    row.status = "stale"
            async with RESEARCH_DB_WRITE_LOCK:
                try:
                    from app.research_market_history import archive_snapshot

                    await asyncio.to_thread(archive_snapshot, market_id, snapshot, run_id)
                    await asyncio.to_thread(
                        write_dataset,
                        dataset,
                        snapshot.model_dump(mode="json", by_alias=True),
                        source=" / ".join(sorted({row.source for row in snapshot.rows}))
                        or "unavailable",
                        run_id=run_id,
                        observed_at=snapshot.as_of,
                        status=snapshot.status,
                    )
                except Exception as exc:
                    await asyncio.to_thread(
                        finish_refresh, run_id, "error", error_code=type(exc).__name__
                    )
                    raise
                await asyncio.to_thread(
                    finish_refresh,
                    run_id,
                    "error" if error else snapshot.status,
                    error_code=type(error).__name__ if error else None,
                )
            results[market_id] = snapshot.status
    return results
