"""海外研究数据（FedWatch / ETF Flow / Deribit IV）定时刷新 worker。

调度沿用 A 股的 lifespan + 周期轮询模式：美股收盘后（北京时间 06:00 起）
每天刷新一次，幂等判断按 dataset 独立（各源同一天只刷一次）。单个数据源
失败不阻塞其他源（return_exceptions 隔离），失败保留上一次有效数据。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI

from app.config import get_settings
from app.research_a_share_repository import finish_refresh, start_refresh
from app.research_overseas_repository import (
    read_latest_fetched_at,
    write_iv_snapshot,
    write_overseas_points,
    write_overseas_series,
)
from app.research_provider_overseas import (
    fetch_btc_iv_snapshot,
    fetch_deribit_iv,
    fetch_etf_flow,
    fetch_fedwatch,
)

_CHINA = ZoneInfo("Asia/Shanghai")
_REFRESH_LOCK = asyncio.Lock()

_SOURCE_FEDWATCH = "CME FedWatch (30-Day Fed Funds Futures)"
_SOURCE_ETF = "Farside UK BTC Spot ETF Flows (US$m)"
_SOURCE_IV = "Deribit BTC Options ATM IV"


def _overseas_refresh_due(now: datetime | None = None) -> bool:
    local = (now or datetime.now(UTC)).astimezone(_CHINA)
    return local.time() >= time(6, 0)


def _today() -> str:
    return datetime.now(_CHINA).date().isoformat()


def _already_refreshed_today(dataset: str) -> bool:
    fetched = read_latest_fetched_at(dataset)
    if not fetched:
        return False
    try:
        dt = datetime.fromisoformat(fetched)
    except ValueError:
        return False
    return dt.astimezone(_CHINA).date() == datetime.now(_CHINA).date()


async def _collect_fedwatch(force: bool) -> tuple[str, str]:
    """抓取并落库 FedWatch，返回 (status, message)。"""
    dataset = "macro_fedwatch"
    if not force and _already_refreshed_today(dataset):
        return "up_to_date", ""
    run_id = uuid4().hex
    today = _today()
    start_refresh(run_id, None)
    try:
        fedwatch = await asyncio.to_thread(fetch_fedwatch)
        series = {
            "__meta__": {
                "effr": fedwatch["effr"],
                "currentTarget": fedwatch["currentTarget"],
                "observedAt": fedwatch["observedAt"],
                "zqPricing": fedwatch["zqPricing"],
            }
        }
        for meeting in fedwatch["meetings"]:
            series[meeting["date"]] = {
                "probabilities": meeting["probabilities"],
                "contract": meeting.get("contract"),
            }
        await asyncio.to_thread(
            write_overseas_series, run_id, dataset, today, series, source=_SOURCE_FEDWATCH
        )
        finish_refresh(run_id, "ready")
        return "ready", ""
    except BaseException as exc:
        finish_refresh(run_id, "error", error_code=type(exc).__name__, message=str(exc)[:500])
        raise


async def _collect_etf_flow(force: bool) -> tuple[str, str]:
    """抓取并落库 BTC ETF 资金流（最近 14 日，逐日逐 ticker 落点）。"""
    dataset = "crypto_etf_flow"
    if not force and _already_refreshed_today(dataset):
        return "up_to_date", ""
    run_id = uuid4().hex
    start_refresh(run_id, None)
    try:
        data = await asyncio.to_thread(fetch_etf_flow, 14)
        tickers = data["tickers"]
        latest = data["days"][-1]["date"]
        points: list[tuple[str, str, dict]] = [
            (latest, "__meta__", {"tickers": tickers, "unit": "US$m"})
        ]
        for day in data["days"]:
            for ticker in tickers:
                points.append(
                    (day["date"], ticker, {"flow": day["flows"].get(ticker)})
                )
        await asyncio.to_thread(
            write_overseas_points, run_id, dataset, points, source=_SOURCE_ETF
        )
        finish_refresh(run_id, "ready")
        return "ready", ""
    except BaseException as exc:
        finish_refresh(run_id, "error", error_code=type(exc).__name__, message=str(exc)[:500])
        raise


async def _collect_deribit_iv(force: bool) -> tuple[str, str]:
    """抓取并落库 Deribit BTC ATM IV（两个落点）：
    - crypto_iv_term：旧版全 1W/2W/1M/2M/3M/6M/9M 期限结构（向后兼容，前端按需）
    - crypto_iv_snapshot：1M/3M/6M/1Y 4 时段快照（按日累积历史，用于区间最低/最高/历史最低/折线）
    """
    dataset_term = "crypto_iv_term"
    dataset_snap = "crypto_iv_snapshot"
    today = _today()
    already_done = _already_refreshed_today(dataset_term) or _already_refreshed_today(dataset_snap)
    if not force and already_done:
        return "up_to_date", ""
    run_id = uuid4().hex
    start_refresh(run_id, None)
    try:
        # 1. 抓 IV 期限结构（用旧 fetcher，标准化 1W/2W/1M/2M/3M/6M/9M 桶）
        term_data = await asyncio.to_thread(fetch_deribit_iv)
        series = {"__meta__": {"index": term_data["index"]}}
        for point in term_data["term"]:
            series[point["expiry"]] = {
                "daysToExpiry": point["daysToExpiry"],
                "tenor": point["tenor"],
                "iv": point["iv"],
            }
        await asyncio.to_thread(
            write_overseas_series, run_id, dataset_term, today, series, source=_SOURCE_IV
        )
        # 2. 抓 1M/3M/6M/1Y 快照（按日累积）
        snap = await asyncio.to_thread(fetch_btc_iv_snapshot)
        await asyncio.to_thread(
            write_iv_snapshot, run_id, today, snap, source=_SOURCE_IV
        )
        finish_refresh(run_id, "ready")
        return "ready", ""
    except BaseException as exc:
        finish_refresh(run_id, "error", error_code=type(exc).__name__, message=str(exc)[:500])
        raise


async def refresh_overseas(*, force: bool = False) -> str:
    """抓取全部海外数据源并落库；返回 ready/up_to_date/not_due/busy/error。"""
    if not force and not _overseas_refresh_due():
        return "not_due"
    if _REFRESH_LOCK.locked():
        return "busy"

    async with _REFRESH_LOCK:
        results = await asyncio.gather(
            _collect_fedwatch(force),
            _collect_etf_flow(force),
            _collect_deribit_iv(force),
            return_exceptions=True,
        )
        if any(isinstance(r, BaseException) for r in results):
            return "error"
        if all(r[0] == "up_to_date" for r in results if not isinstance(r, BaseException)):
            return "up_to_date"
        return "ready"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if not settings.research_refresh_enabled:
        yield
        return
    task = asyncio.create_task(
        _run_periodic(max(60.0, settings.research_refresh_interval_seconds))
    )
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def _run_periodic(interval_seconds: float) -> None:
    while True:
        await refresh_overseas()
        await asyncio.sleep(interval_seconds)
