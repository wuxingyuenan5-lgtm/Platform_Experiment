"""海外研究数据（FedWatch / ETF Flow / Deribit IV）定时刷新 worker。

调度沿用 A 股的 lifespan + 周期轮询模式：FedWatch 全天按 1 小时幂等窗口刷新，
其他日度数据在北京时间 06:00 后按中国日幂等。单个数据源
失败不阻塞其他源（return_exceptions 隔离），失败保留上一次有效数据。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time, timedelta
from typing import cast
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI

from app.config import get_settings
from app.research_a_share_repository import finish_refresh, start_refresh
from app.research_cumulative_volatility import refresh_cumulative_volatility
from app.research_equity_observatory import run_periodic as run_equity_periodic
from app.research_etf_tracking import run_periodic as run_etf_periodic
from app.research_fedwatch import METHODOLOGY
from app.research_macro_expectations_refresh import refresh_macro_expectations
from app.research_market_detail_refresh import refresh_market_details
from app.research_overseas_repository import (
    _read_shared_daily_prices,
    read_latest_fetched_at,
    read_latest_series,
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
from app.research_write_lock import RESEARCH_DB_WRITE_LOCK

_CHINA = ZoneInfo("Asia/Shanghai")
_REFRESH_LOCK = asyncio.Lock()

_SOURCE_FEDWATCH = "CME FedWatch (30-Day Fed Funds Futures)"
_SOURCE_ETF = {
    "btc": "Farside UK BTC Spot ETF Flows; shared Bybit spot UTC daily close conversion",
    "eth": "Farside UK ETH Spot ETF Flows; shared Bybit spot UTC daily close conversion",
}
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


def _already_refreshed_within(
    dataset: str,
    window: timedelta,
    *,
    now: datetime | None = None,
) -> bool:
    """Use fetch age for live datasets instead of the daily overseas gate."""
    fetched = read_latest_fetched_at(dataset)
    if not fetched:
        return False
    try:
        dt = datetime.fromisoformat(fetched)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    age = (now or datetime.now(UTC)) - dt.astimezone(UTC)
    return timedelta(0) <= age < window


def _hourly_observed_at() -> str:
    """Bucket FedWatch snapshots by UTC hour for idempotent hourly storage."""
    return datetime.now(UTC).replace(minute=0, second=0, microsecond=0).isoformat()


async def _collect_fedwatch(force: bool) -> tuple[str, str]:
    """抓取并落库 FedWatch，返回 (status, message)。"""
    dataset = "macro_fedwatch"
    if (
        not force
        and _already_refreshed_within(dataset, timedelta(hours=1))
        and read_latest_series(dataset).get("__meta__", {}).get("methodology") == METHODOLOGY
    ):
        return "up_to_date", ""
    run_id = uuid4().hex
    observed_at = _hourly_observed_at()
    async with RESEARCH_DB_WRITE_LOCK:
        await asyncio.to_thread(start_refresh, run_id, None)
    try:
        fedwatch = await asyncio.to_thread(fetch_fedwatch)
        series = {
            "__meta__": {
                "effr": fedwatch["effr"],
                "currentTarget": fedwatch["currentTarget"],
                "observedAt": observed_at,
                "settlementSource": fedwatch.get("settlementSource"),
                "zqPricing": fedwatch["zqPricing"],
                **{
                    key: fedwatch.get(key)
                    for key in (
                        "methodology",
                        "probabilityUnit",
                        "quoteAsOf",
                        "contractQuoteTimes",
                        "missingMeetings",
                    )
                },
            }
        }
        for meeting in fedwatch["meetings"]:
            series[meeting["date"]] = {
                "probabilities": meeting["probabilities"],
                "contract": meeting.get("contract"),
            }
        async with RESEARCH_DB_WRITE_LOCK:
            await asyncio.to_thread(
                write_overseas_series, run_id, dataset, observed_at, series, source=_SOURCE_FEDWATCH
            )
            status = "partial" if fedwatch.get("missingMeetings") else "ready"
            await asyncio.to_thread(finish_refresh, run_id, status)
        return status, ""
    except BaseException as exc:
        async with RESEARCH_DB_WRITE_LOCK:
            await asyncio.to_thread(
                finish_refresh,
                run_id,
                "error",
                error_code=type(exc).__name__,
                message=str(exc)[:500],
            )
        raise


async def _collect_etf_flow(force: bool, asset: str = "btc") -> tuple[str, str]:
    """抓取并落库 BTC/ETH ETF 资金流（源站可提供历史，逐日逐 ticker 落点）。"""
    asset_key = asset.lower().strip()
    if asset_key not in {"btc", "eth"}:
        raise ValueError(f"unsupported_etf_asset:{asset}")
    # Keep the established BTC dataset identity for existing history and
    # consumers; ETH gets its own sibling dataset.
    dataset = "crypto_etf_flow" if asset_key == "btc" else "crypto_eth_etf_flow"
    if not force and _already_refreshed_today(dataset):
        return "up_to_date", ""
    run_id = uuid4().hex
    async with RESEARCH_DB_WRITE_LOCK:
        await asyncio.to_thread(start_refresh, run_id, None)
    try:
        # Farside pages expose the historical table. Rewriting this bounded
        # history on each daily refresh also backfills dates missing before
        # the long-window contract was enabled.
        data = await asyncio.to_thread(fetch_etf_flow, 3650, asset_key)
        prices = await asyncio.to_thread(
            _read_shared_daily_prices, asset_key, [day["date"] for day in data["days"]]
        )
        # Never publish a mixed-unit series: a partial price map would make
        # some rows BTC/ETH and the remaining rows USD while the card exposes
        # only one unit label. Wait for a complete daily-close window instead.
        if prices and not all(day["date"] in prices for day in data["days"]):
            prices = {}
        tickers = data["tickers"]
        latest = data["days"][-1]["date"]
        meta = {"tickers": tickers, "unit": "US$m"}
        if prices:
            meta.update(
                {"coinUnit": asset_key.upper(), "priceSource": "Bybit spot UTC daily close (USDT)"}
            )
        points: list[tuple[str, str, dict]] = [(latest, "__meta__", meta)]
        for day in data["days"]:
            for ticker in tickers:
                usd_flow = day["flows"].get(ticker)
                price = prices.get(day["date"])
                coin_flow = (
                    float(usd_flow) * 1_000_000 / price
                    if usd_flow is not None and price and price > 0
                    else None
                )
                points.append((day["date"], ticker, {"flow": usd_flow, "coinFlow": coin_flow}))
        async with RESEARCH_DB_WRITE_LOCK:
            await asyncio.to_thread(
                write_overseas_points, run_id, dataset, points, source=_SOURCE_ETF[asset_key]
            )
            await asyncio.to_thread(finish_refresh, run_id, "ready")
        return "ready", ""
    except BaseException as exc:
        async with RESEARCH_DB_WRITE_LOCK:
            await asyncio.to_thread(
                finish_refresh,
                run_id,
                "error",
                error_code=type(exc).__name__,
                message=str(exc)[:500],
            )
        raise


async def _collect_deribit_iv(force: bool) -> tuple[str, str]:
    """抓取并落库 Deribit BTC ATM IV（两个落点）：
    - crypto_iv_term：旧版全 1W/2W/1M/2M/3M/6M/9M 期限结构（向后兼容，前端按需）
    - crypto_iv_snapshot：1M/3M/6M/1Y 4 时段快照（按日累积历史，用于区间最低/最高/历史最低/折线）
    """
    dataset_term = "crypto_iv_term"
    dataset_snap = "crypto_iv_snapshot"
    today = _today()
    already_done = _already_refreshed_today(dataset_term) and _already_refreshed_today(dataset_snap)
    if not force and already_done:
        return "up_to_date", ""
    run_id = uuid4().hex
    async with RESEARCH_DB_WRITE_LOCK:
        await asyncio.to_thread(start_refresh, run_id, None)
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
        async with RESEARCH_DB_WRITE_LOCK:
            await asyncio.to_thread(
                write_overseas_series, run_id, dataset_term, today, series, source=_SOURCE_IV
            )
        # 2. 抓 1M/3M/6M/1Y 快照（按日累积）
        snap = await asyncio.to_thread(fetch_btc_iv_snapshot)
        async with RESEARCH_DB_WRITE_LOCK:
            await asyncio.to_thread(write_iv_snapshot, run_id, today, snap, source=_SOURCE_IV)
            await asyncio.to_thread(finish_refresh, run_id, "ready")
        return "ready", ""
    except BaseException as exc:
        async with RESEARCH_DB_WRITE_LOCK:
            await asyncio.to_thread(
                finish_refresh,
                run_id,
                "error",
                error_code=type(exc).__name__,
                message=str(exc)[:500],
            )
        raise


async def refresh_overseas(*, force: bool = False) -> str:
    """抓取海外数据源并落库；返回 ready/up_to_date/busy/error。"""
    if not force and not _overseas_refresh_due():
        # FedWatch is a live futures curve and must keep its hourly cadence
        # through the US session (which falls before 06:00 China time). The
        # daily ETF/IV datasets remain on the China-calendar gate below.
        if _REFRESH_LOCK.locked():
            return "busy"
        async with _REFRESH_LOCK:
            try:
                status, _ = await _collect_fedwatch(False)
                return status
            except BaseException:
                return "error"
    if _REFRESH_LOCK.locked():
        return "busy"

    async with _REFRESH_LOCK:
        results = await asyncio.gather(
            _collect_fedwatch(force),
            _collect_etf_flow(force, "btc"),
            _collect_etf_flow(force, "eth"),
            _collect_deribit_iv(force),
            _refresh_cumulative_with_lock(force),
            return_exceptions=True,
        )
        # Volatility is an enrichment source; its failure must not hide the
        # established overseas datasets.
        primary = [results[0], results[1], results[2], results[3]]
        if any(isinstance(r, BaseException) for r in primary):
            return "error"
        primary_statuses = [cast(tuple[str, str], result) for result in primary]
        if all(result[0] == "up_to_date" for result in primary_statuses):
            return "up_to_date"
        return "ready"


async def _refresh_cumulative_with_lock(force: bool) -> str:
    async with RESEARCH_DB_WRITE_LOCK:
        return await asyncio.to_thread(refresh_cumulative_volatility, force=force)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if not settings.research_refresh_enabled:
        yield
        return
    task = asyncio.create_task(_run_periodic(max(60.0, settings.research_refresh_interval_seconds)))
    market_task = asyncio.create_task(_run_market_periodic())
    equity_task = asyncio.create_task(run_equity_periodic())
    etf_task = asyncio.create_task(run_etf_periodic())
    try:
        yield
    finally:
        task.cancel()
        market_task.cancel()
        equity_task.cancel()
        etf_task.cancel()
        await asyncio.gather(task, market_task, equity_task, etf_task, return_exceptions=True)


async def _run_market_periodic() -> None:
    while True:
        try:
            await refresh_market_details()
        except Exception:
            logging.getLogger(__name__).exception("Market detail refresh failed")
        await asyncio.sleep(300)


async def _run_periodic(interval_seconds: float) -> None:
    while True:
        await refresh_overseas()
        # Prediction-market probabilities are short-lived observations.  They
        # are refreshed on the same bounded five-minute loop as intraday data,
        # while the page continues to read the local artifact only.
        try:
            await asyncio.to_thread(refresh_macro_expectations)
        except Exception:
            pass
        try:
            from app.research_polymarket_fomc import refresh_fomc
            await asyncio.to_thread(refresh_fomc)
        except Exception:
            logging.getLogger(__name__).exception("FOMC refresh failed")
        # Intraday candles are a separate five-minute production cadence. The
        # daily overseas sources still remain gated/idempotent inside
        # refresh_overseas(), so this does not refetch them on every tick.
        if not _overseas_refresh_due():
            try:
                await _refresh_cumulative_with_lock(False)
            except Exception:
                # The cumulative series is an enrichment source; its failure
                # must not stop the worker from checking the daily datasets.
                pass
        await asyncio.sleep(min(interval_seconds, 300.0))
