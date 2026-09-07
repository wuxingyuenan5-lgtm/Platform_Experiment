from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI

from app.config import get_settings
from app.research_a_share_repository import (
    finish_refresh,
    read_refresh_status,
    read_stock_pool,
    start_refresh,
    write_dashboard,
    write_dataset,
    write_history_points,
    write_stock_pool,
)
from app.research_service import _PROVIDER, collect_a_share_dashboard

_REFRESH_LOCK = asyncio.Lock()


def _history_return(points: list[object], sessions: int) -> float | None:
    if len(points) <= sessions:
        return None
    current = Decimal(str(points[-1].close))
    base = Decimal(str(points[-1 - sessions].close))
    return float((current / base) - 1) if base > 0 else None


def _history_ytd(points: list[object]) -> float | None:
    if len(points) < 2:
        return None
    latest = points[-1]
    year_start = latest.observed_at.replace(month=1, day=1)
    prior = next((point for point in reversed(points) if point.observed_at < year_start), None)
    if prior is None or prior.close <= 0:
        return None
    return float((latest.close / prior.close) - 1)


def _scheduled_refresh_due(now: datetime | None = None) -> bool:
    local = (now or datetime.now(UTC)).astimezone(ZoneInfo("Asia/Shanghai"))
    return local.weekday() < 5 and local.time() >= time(15, 5)


async def refresh_a_share_research(*, force: bool = False) -> str:
    """Collect one close-ready A-share snapshot into Platform-owned storage."""
    if not force and not _scheduled_refresh_due():
        return "not_due"
    local_date = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    latest = read_refresh_status()
    if (
        not force
        and latest is not None
        and latest.get("targetTradeDate") == local_date
        and latest.get("status") == "ready"
    ):
        return "up_to_date"
    if _REFRESH_LOCK.locked():
        return "busy"
    async with _REFRESH_LOCK:
        run_id = uuid4().hex
        start_refresh(run_id, local_date)
        try:
            dashboard = await collect_a_share_dashboard()
            write_dashboard(run_id, dashboard)
            indices = dashboard.market_detail.data or []
            # The stock-pool read model is populated in the same background run;
            # it is never assembled by a browser request.
            spots, memberships = await asyncio.gather(
                _PROVIDER.a_share_spot(), _PROVIDER.shenwan_memberships(), return_exceptions=True
            )
            membership_by_code = (
                {item.security_code: item for item in memberships}
                if not isinstance(memberships, BaseException)
                else {}
            )
            previous_pool = read_stock_pool() or {}
            previous_rows = list(previous_pool.get("stocks") or [])
            tracked_by_code = {
                str(row.get("code") or "").strip(): row
                for row in previous_rows
                if str(row.get("code") or "").strip()
            }
            # Historical bootstrap seeds this definition. If it has not been
            # installed yet, the most liquid A-share names form a temporary
            # seed; it is replaced by the explicit pool definition on the
            # next refresh and is never invented by the browser.
            if not tracked_by_code and not isinstance(spots, BaseException):
                tracked_by_code = {
                    row.security_code: {"code": row.security_code, "name": row.security_name}
                    for row in sorted(spots, key=lambda item: item.turnover_yuan, reverse=True)[:162]
                }
            spot_by_code = (
                {item.security_code: item for item in spots}
                if not isinstance(spots, BaseException)
                else {}
            )
            fallback_quotes = await _PROVIDER._a_share.tracked_stock_spot(
                [code for code in tracked_by_code if code not in spot_by_code]
            )
            spot_by_code.update({item.security_code: item for item in fallback_quotes})
            histories = await _PROVIDER._a_share.stock_daily_histories(list(tracked_by_code))
            stock_rows = []
            stock_history_points: list[tuple[str, str, dict[str, object]]] = []
            if spot_by_code:
                for code, prior in tracked_by_code.items():
                    row = spot_by_code.get(code)
                    if row is None:
                        continue
                    membership = membership_by_code.get(code)
                    history = histories.get(code, [])
                    for point in history:
                        stock_history_points.append(
                            (
                                point.observed_at.isoformat(),
                                code,
                                {"close": point.close, "turnoverYuan": point.turnover_yuan},
                            )
                        )
                    stock_rows.append(
                        {
                            "instrument_id": str(prior.get("instrument_id") or code),
                            "code": code,
                            "exchange": prior.get("exchange"),
                            "name": row.security_name,
                            "industry": membership.sw_l2_name if membership else prior.get("industry"),
                            "change": float(row.return_pct or 0) / 100,
                            "change_5d": _history_return(history, 5),
                            "change_20d": _history_return(history, 20),
                            "ytd": _history_ytd(history),
                            "amount_yi": float(row.turnover_yuan) / 1e8,
                            "turnover": prior.get("turnover"),
                            "mcap_yi": prior.get("mcap_yi"),
                            "pe_ttm": prior.get("pe_ttm"),
                            "pb": prior.get("pb"),
                            "research_baskets": prior.get("research_baskets", []),
                        }
                    )
                write_dataset(
                    "stocks",
                    list(spot_by_code.values()),
                    source="东方财富全市场快照 / 腾讯股票池补充行情",
                    run_id=run_id,
                )
                hot_stock_points = [
                    (
                        local_date,
                        item.security_code,
                        {
                            "securityCode": item.security_code,
                            "securityName": item.security_name,
                            "returnPct": item.return_pct,
                            "turnoverYuan": item.turnover_yuan,
                            "industry": membership_by_code.get(item.security_code).sw_l2_name if membership_by_code.get(item.security_code) else None,
                        },
                    )
                    for item in spots
                    if item.turnover_yuan > Decimal("10000000000")
                ]
                if hot_stock_points:
                    write_history_points(
                        run_id, "hot_stock", hot_stock_points,
                        source="东方财富全市场快照 / 严格成交额大于100亿元",
                    )
            if not isinstance(memberships, BaseException):
                write_dataset("memberships", memberships, source="申万分类适配器", run_id=run_id)
            if stock_history_points:
                write_history_points(
                    run_id,
                    "stock",
                    stock_history_points,
                    source="tencent-public-adjusted-daily-kline",
                )
            stock_rows.sort(key=lambda row: row["amount_yi"] or 0, reverse=True)
            leaders = {
                key: {
                    "up": sorted(stock_rows, key=lambda row: row.get(key) if row.get(key) is not None else -float("inf"), reverse=True)[:8],
                    "down": sorted(stock_rows, key=lambda row: row.get(key) if row.get(key) is not None else float("inf"))[:8],
                }
                for key in ("change", "change_5d", "change_20d")
            }
            pool_complete = (
                bool(tracked_by_code)
                and len(stock_rows) == len(tracked_by_code)
                and all(len(histories.get(code, [])) >= 2 for code in tracked_by_code)
            )
            if pool_complete:
                write_stock_pool(
                    run_id,
                    {
                    "meta": {
                        "generated_at": dashboard.generated_at.isoformat(),
                        "report_date": dashboard.generated_at.date().isoformat(),
                        "source": "platform-a-share-daily-production",
                    },
                    "summary": {"tracked_count": len(stock_rows), "breadth": {"up": sum(1 for row in stock_rows if row["change"] > 0), "down": sum(1 for row in stock_rows if row["change"] < 0), "flat": sum(1 for row in stock_rows if row["change"] == 0)}},
                    "stocks": stock_rows,
                    "indices": [
                        {
                            "instrument_id": row.code,
                            "code": row.code,
                            "name": row.name,
                            "change": (float(row.return_1d_pct) / 100) if row.return_1d_pct is not None else None,
                            "change_5d": (float(row.return_1w_pct) / 100) if row.return_1w_pct is not None else None,
                            "change_20d": (float(row.return_1m_pct) / 100) if row.return_1m_pct is not None else None,
                            "ytd": (float(row.return_ytd_pct) / 100) if row.return_ytd_pct is not None else None,
                        }
                        for row in indices
                    ],
                    "heatmap": stock_rows,
                    "leaders": {"today": leaders["change"], "5d": leaders["change"], "20d": leaders["change"]},
                    "definitions": previous_pool.get("definitions", {"focus_codes": [], "research_baskets": []}),
                    },
                )
            statuses = [
                dashboard.market_detail.meta.status,
                dashboard.breadth.meta.status,
                dashboard.shenwan.meta.status,
                dashboard.emotion.meta.status,
            ]
            status = "ready" if all(item == "ready" for item in statuses) and pool_complete else "partial"
            finish_refresh(run_id, status)
            return status
        except Exception as exc:
            finish_refresh(run_id, "error", error_code=type(exc).__name__, message=str(exc)[:500])
            return "error"


async def _refresh_loop() -> AsyncIterator[None]:
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


async def _run_periodic(interval_seconds: float) -> None:
    await refresh_a_share_research()
    while True:
        await asyncio.sleep(max(60.0, interval_seconds))
        await refresh_a_share_research()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async for value in _refresh_loop():
        yield value
