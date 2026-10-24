"""Independent HK stock-pool producer; never waits for or publishes CN data."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.database_connection import connection
from app.research_a_share_refresh import _build_stock_rows, _collect, _quote_date
from app.research_a_share_repository import (
    finish_refresh,
    read_refresh_status,
    read_stock_pool,
    read_tracked_codes,
    start_refresh,
    write_history_points,
    write_stock_pool,
)
from app.research_hk_calendar import hk_last_session
from app.research_service import _PROVIDER
from app.research_write_lock import RESEARCH_DB_WRITE_LOCK

_LOCK = asyncio.Lock()
_HK = ZoneInfo("Asia/Hong_Kong")
_LOGGER = logging.getLogger(__name__)


def _publish(run_id, pool, history, status, message):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        write_stock_pool(run_id, pool, market="HK", db=db)
        write_history_points(run_id, "stock", history, source="腾讯复权日线", db=db)
        # Same transaction as the HK rows; CN run metadata is never touched.
        db.execute(
            "UPDATE research_a_share_refresh_runs SET finished_at=?,status=?,message=? "
            "WHERE run_id=?",
            (datetime.now(UTC).isoformat(), status, message, run_id),
        )


async def refresh_hk_share_research(*, force=False):
    now = datetime.now(_HK)
    session = hk_last_session(now.date())
    if session is None:
        return "not_due"
    if not force and (session != now.date() or now.time() < time(16, 15)):
        return "not_due"
    latest = await asyncio.to_thread(read_refresh_status, "HK")
    target = session.isoformat()
    if not force and latest and latest["status"] == "ready" and latest["targetTradeDate"] == target:
        return "up_to_date"
    if _LOCK.locked():
        return "busy"
    async with _LOCK:
        codes = [code for code in await asyncio.to_thread(read_tracked_codes) if len(code) == 5]
        if not codes:
            return "up_to_date"
        run_id = f"hk-share-{uuid4().hex}"
        async with RESEARCH_DB_WRITE_LOCK:
            await asyncio.to_thread(start_refresh, run_id, target)
        try:
            previous = await asyncio.to_thread(read_stock_pool, codes)
            quotes, histories = await asyncio.gather(
                _collect(_PROVIDER.tracked_stock_spot(codes), 90),
                _collect(_PROVIDER.stock_daily_histories(codes), 240),
                return_exceptions=True,
            )
            quotes = quotes if isinstance(quotes, list) else []
            by_code = {row.security_code: row for row in quotes}
            if not quotes and not isinstance(histories, dict):
                raise RuntimeError("港股行情及历史采集均失败")
            rows, history = await asyncio.to_thread(
                _build_stock_rows,
                codes,
                by_code,
                histories,
                {row["code"]: row for row in previous["focusStocks"]},
                {},
                target,
            )
            closed = session < now.date() or now.time() >= time(16, 15)
            missing = sum(
                row["status"] != "ready"
                or row.get("history_date") != target
                or row.get("code") not in by_code
                or _quote_date(by_code[row["code"]]) != target
                or by_code[row["code"]].observed_at.astimezone(_HK).time() < time(16)
                for row in rows
            )
            status = "ready" if closed and not missing else "partial"
            message = f"港股股票池{len(rows)}只，{missing}只数据不完整" if missing else None
            pool = {
                "stocks": rows,
                "meta": {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "report_date": target,
                    "source": "平台港股收盘研究数据",
                    "status": status,
                },
            }
            async with RESEARCH_DB_WRITE_LOCK:
                await asyncio.to_thread(_publish, run_id, pool, history, status, message)
            return status
        except asyncio.CancelledError:
            async with RESEARCH_DB_WRITE_LOCK:
                await asyncio.to_thread(
                    finish_refresh,
                    run_id,
                    "error",
                    error_code="refresh_interrupted",
                    message="港股更新被中断",
                )
            raise
        except Exception as exc:
            async with RESEARCH_DB_WRITE_LOCK:
                await asyncio.to_thread(
                    finish_refresh,
                    run_id,
                    "error",
                    error_code=type(exc).__name__,
                    message=str(exc)[:500],
                )
            _LOGGER.exception("HK scheduled refresh failed; CN publication is unaffected")
            return "error"


async def _run_periodic(interval_seconds):
    while True:
        try:
            await refresh_hk_share_research()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("HK refresh cycle failed; it will retry independently")
        await asyncio.sleep(max(60.0, interval_seconds))


@asynccontextmanager
async def lifespan(_):
    settings = get_settings()
    if not settings.research_refresh_enabled:
        yield
        return
    task = asyncio.create_task(_run_periodic(settings.research_refresh_interval_seconds))
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
