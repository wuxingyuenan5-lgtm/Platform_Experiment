from __future__ import annotations

import asyncio
import logging
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
from app.data_audit_calendar import calendar_snapshot
from app.database_connection import read_only_connection
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
_LOGGER = logging.getLogger(__name__)


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
    if local.time() < time(15, 5):
        return False
    try:
        with read_only_connection() as db:
            calendar = calendar_snapshot(db, local.date().isoformat())
    except Exception:
        _LOGGER.exception("A-share trading calendar is unavailable for scheduled refresh")
        return False
    return bool(calendar and local.date().isoformat() in calendar["days"])


async def _collect[T](awaitable: Awaitable[T], seconds: float = 90) -> T:
    return await asyncio.wait_for(awaitable, seconds)


def _quote_date(row: Any) -> str | None:
    observed = row.get("observed_at") if isinstance(row, dict) else row.observed_at
    if isinstance(observed, str):
        observed = datetime.fromisoformat(observed)
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


def _crowding(
    dashboard: Any,
    trade_date: str | None,
    spots: list[Any] | BaseException,
    sector_quotes: list[dict[str, Any]] | BaseException,
    innovation: dict[str, Any] | BaseException,
) -> None:
    # Persist direct sector-board quotes only when all fields and dates align.
    from app.research_data_schemas import ResearchModuleResult, ResearchSourceMeta

    previous = read_dataset("crowding") or {}
    if not trade_date:
        if previous:
            dashboard.crowding = ResearchModuleResult(
                meta=ResearchSourceMeta(
                    source="申万二级行业成交额 / 创新药BK1106",
                    fetched_at=dashboard.generated_at,
                    status="error",
                    message="本次未取得有效的A股交易日",
                ),
                data=None,
            )
        return
    latest = previous.get("latest")
    history = list(previous.get("history", []))
    sectors_complete = False
    sector_message: str | None = None
    if isinstance(sector_quotes, list) and isinstance(spots, list):
        amount_total = sum((row.turnover_yuan for row in spots), Decimal("0"))
        quote_by_code = {str(row.get("code")): row for row in sector_quotes}
        required_codes = {"801102", "801101", "801083", "801081"}
        if amount_total <= 0 or set(quote_by_code) != required_codes:
            sector_message = "四行业板块报价或全A成交额不完整"
        else:
            targets: dict[str, dict[str, Any]] = {}
            for name, code in (
                ("通信设备", "801102"),
                ("计算机设备", "801101"),
                ("元件", "801083"),
                ("半导体", "801081"),
            ):
                quote = quote_by_code[code]
                observed = quote.get("observed_at")
                quote_date = (
                    observed.astimezone(_CHINA).date().isoformat()
                    if isinstance(observed, datetime)
                    else None
                )
                amount = quote.get("amount_yuan")
                turnover = quote.get("turnover_pct")
                if (
                    quote_date != trade_date
                    or not isinstance(amount, Decimal)
                    or amount <= 0
                    or not isinstance(turnover, Decimal)
                    or turnover < 0
                ):
                    sector_message = "四行业板块报价与全A交易日不一致或指标缺失"
                    targets = {}
                    break
                targets[name] = {
                    "code": code,
                    "amount100m": float(amount / Decimal("1e8")),
                    "amountShareOfA": float(amount / amount_total),
                    "turnoverPct": float(turnover),
                }
            if targets:
                values = list(targets.values())
                sectors_complete = len(targets) == 4
                latest = {
                    "date": trade_date,
                    "targets": targets,
                    "combined": {
                        "amount100m": sum(value["amount100m"] for value in values)
                        if sectors_complete
                        else None,
                        "amountShareOfA": sum(value["amountShareOfA"] for value in values)
                        if sectors_complete
                        else None,
                    },
                }
                history = [row for row in history if row.get("date") != trade_date]
                history = sorted([*history, latest], key=lambda row: row["date"])[-2000:]
    elif isinstance(sector_quotes, BaseException):
        sector_message = "四行业板块报价读取失败，保留最近有效数据"

    innovation_history = list(previous.get("innovationHistory", []))
    quote_date = _quote_date(innovation) if isinstance(innovation, dict) else None
    total_amount = (
        sum((row.turnover_yuan for row in spots), Decimal("0"))
        if isinstance(spots, list)
        else Decimal("0")
    )
    if (
        isinstance(innovation, dict)
        and quote_date == trade_date
        and total_amount > 0
        and innovation.get("amount_yuan") is not None
        and innovation.get("turnover_pct") is not None
    ):
        innovation_row = {
            "date": trade_date,
            "amount100m": float(innovation["amount_yuan"] / Decimal("1e8")),
            "amountShareOfA": float(innovation["amount_yuan"] / total_amount),
            "turnoverPct": float(innovation["turnover_pct"]),
            "source": innovation.get("source"),
        }
        innovation_history = [
            row for row in innovation_history if row.get("date") != trade_date
        ]
        innovation_history = sorted(
            [*innovation_history, innovation_row], key=lambda row: row["date"]
        )[-2000:]
    innovation_complete = any(row.get("date") == trade_date for row in innovation_history)
    complete = sectors_complete and innovation_complete
    messages = []
    if not sectors_complete:
        messages.append(sector_message or "四行业成交额、成交额占比或换手率未取得本交易日完整数据")
    if not innovation_complete:
        messages.append("创新药成交额、成交额占比或换手率未取得本交易日数据")
    dashboard.crowding = ResearchModuleResult(
        meta=ResearchSourceMeta(
            source="东方财富四行业板块报价 / 全A成交额 / 东方财富创新药BK1106",
            fetched_at=dashboard.generated_at,
            source_timestamp=datetime.fromisoformat(trade_date).replace(hour=15, tzinfo=_CHINA),
            status="ready" if complete else "partial",
            message="；".join(messages) or None,
        ),
        data={
            "history": history,
            "latest": latest,
            "innovationHistory": innovation_history,
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
        and latest["targetTradeDate"] == today
    ):
        return "up_to_date"
    if _REFRESH_LOCK.locked():
        return "busy"
    async with _REFRESH_LOCK:
        run_id = f"a-share-{uuid4().hex}"
        start_refresh(run_id, None)
        try:
            codes = read_tracked_codes()
            previous = read_stock_pool(codes)
            prior_by_code = {row["code"]: row for row in previous["focusStocks"]}
            # Keep heterogeneous gather groups within its typed tuple overloads.
            (indices, spots, memberships, emotion), (sector_quotes, innovation, histories) = (
                await asyncio.gather(
                    asyncio.gather(
                        _collect(_PROVIDER.index_snapshots(), 180),
                        _collect(_PROVIDER.a_share_spot(), 180),
                        _collect(_PROVIDER.shenwan_memberships()),
                        _collect(_PROVIDER.short_term_emotion()),
                        return_exceptions=True,
                    ),
                    asyncio.gather(
                        _collect(_PROVIDER.sector_crowding_snapshot()),
                        _collect(_PROVIDER.innovation_drug_snapshot()),
                        _collect(_PROVIDER.stock_daily_histories(codes), 240),
                        return_exceptions=True,
                    ),
                )
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
            _crowding(dashboard, trade_date, spots, sector_quotes, innovation)
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
        try:
            result = await refresh_a_share_research()
            if result in {"error", "partial"}:
                status = read_refresh_status() or {}
                _LOGGER.warning(
                    "A-share scheduled refresh result=%s run_id=%s target_trade_date=%s "
                    "error_code=%s message=%s",
                    result,
                    status.get("runId"),
                    status.get("targetTradeDate"),
                    status.get("errorCode"),
                    status.get("message"),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            # A one-off database/provider/runtime error must not kill the in-process
            # scheduler permanently. The next interval retries from persisted state.
            _LOGGER.exception("A-share scheduled refresh cycle crashed; it will retry")
        await asyncio.sleep(max(60.0, interval_seconds))
