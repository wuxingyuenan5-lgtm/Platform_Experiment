from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI

from app.a_share_research_policy import classify_market_breadth, classify_speculation
from app.config import get_settings
from app.research_a_share_repository import (
    finish_refresh,
    publish_refresh,
    read_dataset,
    read_refresh_status,
    read_stock_pool,
    read_stored_stock_histories,
    read_tracked_codes,
    start_refresh,
    summarize_stock_pool,
)
from app.research_data_schemas import (
    AShareBreadthSnapshot,
    AShareIndexHistoryPoint,
    AShareIndexSnapshot,
)
from app.research_provider_a_share import INDEX_DEFINITIONS
from app.research_service import _PROVIDER, collect_a_share_dashboard

_REFRESH_LOCK = asyncio.Lock()
_CHINA = ZoneInfo("Asia/Shanghai")


def _history_return(points: list[AShareIndexHistoryPoint], sessions: int) -> float | None:
    if len(points) <= sessions:
        return None
    current, base = points[-1].close, points[-1 - sessions].close
    return float(current / base - 1) if base > 0 else None


def _history_ytd(points: list[AShareIndexHistoryPoint]) -> float | None:
    if len(points) < 2:
        return None
    year_start = points[-1].observed_at.replace(month=1, day=1)
    prior = next((point for point in reversed(points) if point.observed_at < year_start), None)
    return float(points[-1].close / prior.close - 1) if prior and prior.close > 0 else None


def _scheduled_refresh_due(now: datetime | None = None) -> bool:
    local = (now or datetime.now(UTC)).astimezone(_CHINA)
    return local.weekday() < 5 and local.time() >= time(15, 5)


async def _collect[T](awaitable: Awaitable[T], seconds: float = 90) -> T:
    return await asyncio.wait_for(awaitable, seconds)


def _quote_date(row: Any) -> str | None:
    observed = row.observed_at
    return observed.astimezone(_CHINA).date().isoformat() if observed else None


def _breadth(spots: Any, emotion: Any) -> AShareBreadthSnapshot | Exception:
    if isinstance(spots, BaseException) or not spots:
        return RuntimeError("全市场行情暂不可用")
    dated = [day for row in spots if (day := _quote_date(row)) is not None]
    trade_date = max(dated) if dated else None
    values = [row.return_pct for row in spots if row.return_pct is not None]
    up, down = sum(value > 0 for value in values), sum(value < 0 for value in values)
    limit_up = limit_down = None
    if (
        not isinstance(emotion, BaseException)
        and emotion.trade_date
        and str(emotion.trade_date) == trade_date
    ):
        limit_up = emotion.limit_up_count
        limit_down = emotion.limit_down_count
    return AShareBreadthSnapshot(
        up=up,
        down=down,
        flat=sum(value == 0 for value in values),
        limit_up=limit_up,
        real_limit_up=limit_up,
        limit_down=limit_down,
        real_limit_down=limit_down,
        breadth_state=classify_market_breadth(up, down),
        speculation_state=classify_speculation(limit_up) if limit_up is not None else "暂无数据",
        trade_date=date.fromisoformat(trade_date) if trade_date else None,
        total_amount_yuan=sum((row.turnover_yuan for row in spots), Decimal("0")),
    )


def _crowding(dashboard: Any, trade_date: str | None) -> None:
    # Continue the existing four-industry series from the same complete market
    # and Shenwan aggregation. The historical innovation-drug series keeps its
    # own observation date; it is never advanced without a source observation.
    from app.research_data_schemas import ResearchModuleResult, ResearchSourceMeta

    previous = read_dataset("crowding") or {}
    aggregation = dashboard.shenwan.data
    if not trade_date or aggregation is None:
        if previous:
            dashboard.crowding = ResearchModuleResult(
                meta=ResearchSourceMeta(
                    source="申万二级行业成交额",
                    fetched_at=dashboard.generated_at,
                    status="error",
                    message="本次行业数据不完整",
                ),
                data=None,
            )
        return
    codes = {"通信设备": "801102", "计算机设备": "801101", "元件": "801083", "半导体": "801081"}
    sectors = {row.sw_l2_code: row for row in aggregation.sw2_all}
    targets = {}
    for name, code in codes.items():
        row = sectors.get(code)
        targets[name] = {
            "code": code,
            "amount100m": float(row.turnover_yuan / Decimal("1e8")) if row else None,
            "amountShareOfA": float(row.market_share_pct / 100) if row else None,
            "turnoverPct": None,
        }
    values = list(targets.values())
    complete = all(value["amount100m"] is not None for value in values)
    latest = {
        "date": trade_date,
        "targets": targets,
        "combined": {
            "amount100m": sum(value["amount100m"] for value in values) if complete else None,
            "amountShareOfA": sum(value["amountShareOfA"] for value in values)
            if complete
            else None,
        },
    }
    history = [row for row in previous.get("history", []) if row.get("date") != trade_date]
    history = sorted([*history, latest], key=lambda row: row["date"])[-2000:]
    dashboard.crowding = ResearchModuleResult(
        meta=ResearchSourceMeta(
            source="申万二级行业成交额 / 全市场成交额",
            fetched_at=dashboard.generated_at,
            source_timestamp=datetime.fromisoformat(trade_date).replace(hour=15, tzinfo=_CHINA),
            status="ready" if complete else "partial",
        ),
        data={
            "history": history,
            "latest": latest,
            "innovationHistory": previous.get("innovationHistory", []),
        },
    )


async def refresh_a_share_research(*, force: bool = False) -> str:
    """Collect once, then atomically publish snapshots, histories and run status."""
    if not force and not _scheduled_refresh_due():
        return "not_due"
    today = datetime.now(_CHINA).date().isoformat()
    latest = read_refresh_status()
    if (
        not force
        and latest
        and latest["status"] == "ready"
        and (
            latest["targetTradeDate"] == today
            or datetime.fromisoformat(latest["startedAt"]).astimezone(_CHINA).date().isoformat()
            == today
        )
    ):
        return "up_to_date"
    if _REFRESH_LOCK.locked():
        return "busy"
    async with _REFRESH_LOCK:
        run_id = uuid4().hex
        start_refresh(run_id, None)
        try:
            codes = read_tracked_codes()
            previous = read_stock_pool(codes)
            prior_by_code = {row["code"]: row for row in previous["focusStocks"]}
            indices, spots, memberships, emotion, histories = await asyncio.gather(
                _collect(_PROVIDER.index_snapshots(), 180),
                _collect(_PROVIDER.a_share_spot(), 180),
                _collect(_PROVIDER.shenwan_memberships()),
                _collect(_PROVIDER.short_term_emotion()),
                _collect(_PROVIDER.stock_daily_histories(codes), 240),
                return_exceptions=True,
            )
            breadth = _breadth(spots, emotion)
            dashboard = await collect_a_share_dashboard(
                collected_results=[indices, breadth, spots, memberships, emotion]
            )
            if isinstance(indices, list):
                current_codes = {row.code for row in indices}
                missing = [
                    (code, name)
                    for code, name, _ in INDEX_DEFINITIONS[:8]
                    if code not in current_codes
                ]
                if missing:
                    old_indices = read_dataset("market_detail") or []
                    dashboard.market_detail.data = [
                        *indices,
                        *[
                            AShareIndexSnapshot.model_validate(row)
                            for row in old_indices
                            if row["code"] not in current_codes
                        ],
                    ]
                    dashboard.market_detail.meta.status = "partial"
                    dashboard.market_detail.meta.message = (
                        "未取得本轮数据，已有值保留原交易日："
                        + "、".join(name for _, name in missing)
                    )
            dashboard.breadth.meta.source = "东方财富全市场行情 / 涨跌停池"
            dated = (
                [day for row in spots if (day := _quote_date(row)) is not None]
                if isinstance(spots, list)
                else []
            )
            trade_date = max(dated) if dated else None
            dashboard.shenwan.meta.source_timestamp = (
                datetime.fromisoformat(trade_date).replace(hour=15, tzinfo=_CHINA)
                if trade_date
                else None
            )
            if isinstance(breadth, AShareBreadthSnapshot) and (
                not trade_date
                or isinstance(emotion, BaseException)
                or str(emotion.trade_date) != trade_date
            ):
                dashboard.breadth.meta.status = "partial"
                dashboard.breadth.meta.message = "涨跌分布与涨跌停池未取得同一交易日的完整数据"
            _crowding(dashboard, trade_date)
            member_by_code = (
                {row.security_code: row for row in memberships}
                if isinstance(memberships, list)
                else {}
            )
            quotes = {row.security_code: row for row in spots} if isinstance(spots, list) else {}
            supplement = await asyncio.gather(
                _collect(
                    _PROVIDER.tracked_stock_spot([code for code in codes if code not in quotes]), 90
                ),
                return_exceptions=True,
            )
            if isinstance(supplement[0], list):
                quotes.update({row.security_code: row for row in supplement[0]})
            histories = histories if isinstance(histories, dict) else {}
            stored_histories = read_stored_stock_histories(
                [code for code in codes if code not in histories]
            )
            stock_rows, stock_history = [], []
            for code in codes:
                quote, prior = (
                    quotes.get(code),
                    prior_by_code.get(code, {"code": code, "name": code}),
                )
                history = sorted(
                    histories.get(code, stored_histories.get(code, [])),
                    key=lambda point: point.observed_at,
                )
                stock_history.extend(
                    (
                        str(point.observed_at),
                        code,
                        {"close": point.close, "turnoverYuan": point.turnover_yuan},
                    )
                    for point in history
                    if code in histories
                )
                if quote is None:
                    stock_rows.append(
                        {
                            **prior,
                            "status": "stale" if prior.get("change") is not None else "no_data",
                        }
                    )
                    continue
                member = member_by_code.get(code)
                observed = _quote_date(quote)
                aligned = bool(history and observed and str(history[-1].observed_at) == observed)
                status = (
                    "ready"
                    if aligned and quote.return_pct is not None and code in histories
                    else "partial"
                )
                if observed and trade_date and observed < trade_date:
                    status = "stale"
                stock_rows.append(
                    {
                        "instrument_id": code,
                        "code": code,
                        "name": quote.security_name,
                        "industry": member.sw_l2_name if member else prior.get("industry"),
                        "price": float(quote.price) if quote.price is not None else None,
                        "currency": quote.currency,
                        "status": status,
                        "observed_at": quote.observed_at.isoformat() if quote.observed_at else None,
                        "history_date": str(history[-1].observed_at) if history else None,
                        "history_source": "collected" if code in histories else "stored",
                        "change": float(quote.return_pct / 100)
                        if quote.return_pct is not None
                        else None,
                        "change_5d": _history_return(history, 5) if aligned else None,
                        "change_20d": _history_return(history, 20) if aligned else None,
                        "ytd": _history_ytd(history) if aligned else None,
                        "amount_yi": float(quote.turnover_yuan / Decimal("1e8")),
                        "turnover": float(quote.turnover_pct)
                        if quote.turnover_pct is not None
                        else None,
                        "mcap_yi": float(quote.market_cap_yuan / Decimal("1e8"))
                        if quote.market_cap_yuan is not None
                        else None,
                        "pe_ttm": float(quote.pe_ttm) if quote.pe_ttm is not None else None,
                        "pb": float(quote.pb) if quote.pb is not None else None,
                        "research_baskets": prior.get("research_baskets", []),
                    }
                )
            pool_ready = all(row["status"] == "ready" for row in stock_rows)
            pool = summarize_stock_pool(
                {
                    "meta": {
                        "generated_at": dashboard.generated_at.isoformat(),
                        "report_date": trade_date,
                        "source": "平台收盘研究数据",
                        "status": "ready" if pool_ready else "partial",
                    },
                    "stocks": stock_rows,
                    "indices": [
                        {
                            "instrument_id": row.code,
                            "code": row.code,
                            "name": row.name,
                            **{
                                key: float(value / 100) if value is not None else None
                                for key, value in (
                                    ("change", row.return_1d_pct),
                                    ("change_5d", row.return_1w_pct),
                                    ("change_20d", row.return_1m_pct),
                                    ("ytd", row.return_ytd_pct),
                                )
                            },
                        }
                        for row in (dashboard.market_detail.data or [])
                    ],
                    "definitions": previous.get("definitions", {}),
                }
            )
            datasets, history_sets = [], []
            if isinstance(spots, list) and spots:
                datasets.append(("stocks", spots, "东方财富全市场行情"))
                # A close date comes from quotes, never the scheduler's wall clock.
                closed = trade_date and all(
                    row.observed_at
                    and (
                        str(row.observed_at.astimezone(_CHINA).date()) < today
                        or row.observed_at.astimezone(_CHINA).time() >= time(15)
                    )
                    for row in spots
                    if _quote_date(row) == trade_date
                )
                if closed:
                    hot = [
                        (
                            trade_date,
                            row.security_code,
                            {
                                "securityCode": row.security_code,
                                "securityName": row.security_name,
                                "returnPct": row.return_pct,
                                "turnoverYuan": row.turnover_yuan,
                                "industry": member_by_code[row.security_code].sw_l2_name
                                if row.security_code in member_by_code
                                else None,
                            },
                        )
                        for row in spots
                        if _quote_date(row) == trade_date
                        and row.turnover_yuan > Decimal("10000000000")
                    ]
                    history_sets.append(
                        ("hot_stock", hot, "东方财富全市场行情 / 成交额严格大于100亿元")
                    )
            if isinstance(memberships, list) and memberships:
                datasets.append(("memberships", memberships, "申万行业分类"))
            history_sets.append(("stock", stock_history, "腾讯复权日线"))
            modules = [
                dashboard.market_detail,
                dashboard.breadth,
                dashboard.shenwan,
                dashboard.emotion,
            ]
            if dashboard.crowding:
                modules.append(dashboard.crowding)
            status = (
                "ready"
                if pool_ready
                and trade_date
                and all(module.meta.status == "ready" for module in modules)
                else "partial"
            )
            if not any(module.data for module in modules) and not quotes:
                raise RuntimeError("本次采集未获得有效市场数据")
            missing = sum(row["status"] != "ready" for row in stock_rows)
            publish_refresh(
                run_id,
                dashboard,
                pool=pool,
                datasets=datasets,
                histories=history_sets,
                trade_date=trade_date,
                status=status,
                message=f"股票池{len(stock_rows)}只，{missing}只数据不完整" if missing else None,
            )
            return status
        except asyncio.CancelledError:
            finish_refresh(
                run_id,
                "error",
                error_code="refresh_interrupted",
                message="更新被中断，保留上次完整发布",
            )
            raise
        except Exception as exc:
            finish_refresh(run_id, "error", error_code=type(exc).__name__, message=str(exc)[:500])
            return "error"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
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
    while True:
        await refresh_a_share_research()
        await asyncio.sleep(max(60.0, interval_seconds))
