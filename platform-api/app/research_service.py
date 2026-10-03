from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast
from zoneinfo import ZoneInfo

from app.a_share_research_policy import aggregate_shenwan_level2
from app.research_a_share_repository import (
    read_dashboard,
    read_dataset,
    read_dataset_metadata,
    read_hot_stock_history,
)
from app.research_cache import LastKnownGoodResearchCache
from app.research_data_schemas import (
    AShareBreadthSnapshot,
    AShareDashboardResponse,
    AShareIndexSnapshot,
    AShareLiveSectorFundFlow,
    AShareLiveSectorFundFlowResponse,
    AShareMarketTurnoverResponse,
    AShareMarketTurnoverRow,
    AShareResearchAggregation,
    AShareTurnoverStock,
    MacroExpectationEvent,
    MacroExpectationResponse,
    ResearchDataStatus,
    ResearchModuleResult,
    ResearchSourceMeta,
    ShenwanMembership,
    ShortTermEmotionSnapshot,
    StockSnapshotResponse,
)
from app.research_macro_history import MacroProbabilityHistoryStore
from app.research_providers import FreeResearchProvider

DEFAULT_THRESHOLD_YUAN = Decimal("10000000000")
PCT_QUANT = Decimal("0.01")
PROVIDER_TIMEOUT_SECONDS = 25.0

_PROVIDER = FreeResearchProvider()
_DASHBOARD_CACHE = LastKnownGoodResearchCache[AShareDashboardResponse](
    ttl=timedelta(minutes=5),
    is_meaningful=lambda value: bool(value.market_detail.data or value.breadth.data),
)
_LIVE_SECTOR_FLOW_CACHE = LastKnownGoodResearchCache[AShareLiveSectorFundFlowResponse](
    ttl=timedelta(minutes=5),
    is_meaningful=lambda value: bool(value.rows),
)
_LIVE_TURNOVER_CACHE = LastKnownGoodResearchCache[AShareMarketTurnoverResponse](
    ttl=timedelta(minutes=5),
    is_meaningful=lambda value: bool(value.rows),
)
_MEMBERSHIP_CACHE = LastKnownGoodResearchCache[list[ShenwanMembership]](
    ttl=timedelta(hours=24),
    is_meaningful=bool,
)
_STOCK_CACHE = LastKnownGoodResearchCache[StockSnapshotResponse](
    ttl=timedelta(minutes=15),
    is_meaningful=lambda value: bool(value.modules),
)
_MACRO_CACHE = LastKnownGoodResearchCache[MacroExpectationResponse](
    ttl=timedelta(minutes=15),
    is_meaningful=lambda value: bool(value.events.data),
)
_DASHBOARD_LOCK = asyncio.Lock()
_LIVE_SECTOR_FLOW_LOCK = asyncio.Lock()
_LIVE_TURNOVER_LOCK = asyncio.Lock()
_MEMBERSHIP_LOCK = asyncio.Lock()
_STOCK_LOCKS: dict[str, asyncio.Lock] = {}
_MACRO_LOCK = asyncio.Lock()


class ResearchServiceError(RuntimeError):
    def __init__(self, code: str, detail: str, *, status_code: int = 503) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(UTC)


async def _provider_call[T](awaitable: Awaitable[T]) -> T:
    try:
        return await asyncio.wait_for(
            awaitable,
            timeout=PROVIDER_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        raise ResearchServiceError(
            "provider_timeout",
            f"研究数据源超过{PROVIDER_TIMEOUT_SECONDS:g}秒未返回",
        ) from exc


def _require_model[T](value: Any, expected: type[T], source: str) -> T:
    if not isinstance(value, expected):
        raise ResearchServiceError(
            "provider_invalid_payload",
            f"{source}返回了无效{expected.__name__}合同",
        )
    return value


def _require_model_list[ModelT](
    value: Any,
    expected: type[ModelT],
    source: str,
) -> list[ModelT]:
    if not isinstance(value, list) or any(not isinstance(item, expected) for item in value):
        raise ResearchServiceError(
            "provider_invalid_payload",
            f"{source}返回了无效{expected.__name__}列表合同",
        )
    return cast(list[ModelT], value)


def _require_mapping(value: Any, source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ResearchServiceError(
            "provider_invalid_payload",
            f"{source}返回了无效对象合同",
        )
    return cast(dict[str, Any], value)


def _validated_result[ResultT](
    value: Any,
    validator: Callable[[Any], ResultT],
) -> ResultT | BaseException:
    if isinstance(value, BaseException):
        return value
    try:
        return validator(value)
    except BaseException as exc:
        return exc


def _source_timestamp(data: Any) -> datetime | None:
    trade_date = getattr(data, "trade_date", None)
    if isinstance(trade_date, date):
        return datetime.combine(trade_date, time(15), ZoneInfo("Asia/Shanghai"))
    if isinstance(data, list):
        dates = [point.observed_at for item in data for point in getattr(item, "history", [])]
        if dates:
            return datetime.combine(max(dates), time(15), ZoneInfo("Asia/Shanghai"))
    return None


def _module(
    *,
    source: str,
    data: Any,
    status: ResearchDataStatus | None = None,
    error_code: str | None = None,
    message: str | None = None,
    fetched_at: datetime | None = None,
    is_stale: bool = False,
) -> ResearchModuleResult:
    observed_at = fetched_at or _now()
    inferred_status: ResearchDataStatus = status or ("ready" if _meaningful(data) else "no_data")
    return ResearchModuleResult(
        meta=ResearchSourceMeta(
            source=source,
            source_timestamp=_source_timestamp(data),
            fetched_at=observed_at,
            status=inferred_status,
            is_stale=is_stale,
            error_code=error_code,
            message=message,
        ),
        data=data,
    )


def _error_module(source: str, exc: BaseException) -> ResearchModuleResult:
    error_code = exc.code if isinstance(exc, ResearchServiceError) else type(exc).__name__
    message = (
        exc.detail if isinstance(exc, ResearchServiceError) else "该数据源暂时不可用，请稍后更新"
    )
    return _module(
        source=source,
        data=None,
        status="error",
        error_code=error_code,
        message=message[:500] or "数据源暂时不可用",
    )


def _meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes, list, tuple, dict, set)):
        return bool(value)
    return True


async def _memberships() -> list[ShenwanMembership]:
    cached = _MEMBERSHIP_CACHE.get_fresh("shenwan")
    if cached is not None:
        return cached.value
    async with _MEMBERSHIP_LOCK:
        cached = _MEMBERSHIP_CACHE.get_fresh("shenwan")
        if cached is not None:
            return cached.value
        try:
            value = _require_model_list(
                await _provider_call(_PROVIDER.shenwan_memberships()),
                ShenwanMembership,
                "申万行业分类",
            )
        except Exception:
            stale = _MEMBERSHIP_CACHE.get("shenwan")
            if stale is not None:
                return stale.value
            raise
        _MEMBERSHIP_CACHE.store("shenwan", value)
        return value


async def get_a_share_dashboard(
    *,
    threshold_yuan: Decimal = DEFAULT_THRESHOLD_YUAN,
    collected_results: list[Any] | None = None,
) -> AShareDashboardResponse:
    if threshold_yuan <= 0:
        raise ResearchServiceError(
            "invalid_turnover_threshold",
            "成交额阈值必须大于0",
            status_code=422,
        )
    cache_key = f"dashboard:{threshold_yuan.normalize()}"
    cached = _DASHBOARD_CACHE.get_fresh(cache_key)
    if cached is not None and collected_results is None:
        return cached.value

    async with _DASHBOARD_LOCK:
        cached = _DASHBOARD_CACHE.get_fresh(cache_key)
        if cached is not None and collected_results is None:
            return cached.value
        results = (
            collected_results
            if collected_results is not None
            else await asyncio.gather(
                _provider_call(_PROVIDER.index_snapshots()),
                _provider_call(_PROVIDER.market_activity()),
                _provider_call(_PROVIDER.a_share_spot()),
                _memberships(),
                _provider_call(_PROVIDER.short_term_emotion()),
                return_exceptions=True,
            )
        )
        raw_indices, raw_breadth, raw_stocks, raw_memberships, raw_emotion = results
        indices = _validated_result(
            raw_indices,
            lambda value: _require_model_list(
                value,
                AShareIndexSnapshot,
                "Platform 公开指数日线适配",
            ),
        )
        breadth = _validated_result(
            raw_breadth,
            lambda value: _require_model(
                value,
                AShareBreadthSnapshot,
                "乐咕乐股赚钱效应（AKShare适配）",
            ),
        )
        stocks = _validated_result(
            raw_stocks,
            lambda value: _require_model_list(
                value,
                AShareTurnoverStock,
                "东方财富A股行情（AKShare适配）",
            ),
        )
        memberships = _validated_result(
            raw_memberships,
            lambda value: _require_model_list(
                value,
                ShenwanMembership,
                "申万宏源行业分类",
            ),
        )
        emotion = _validated_result(
            raw_emotion,
            lambda value: _require_model(
                value,
                ShortTermEmotionSnapshot,
                "东方财富涨停板行情中心",
            ),
        )

        # The complete all-A snapshot owns advance/decline breadth, while the
        # official Eastmoney limit pools own board counts. Join only two
        # observations from the same collection run; never infer limits from
        # rounded daily returns.
        if (
            isinstance(breadth, AShareBreadthSnapshot)
            and isinstance(emotion, ShortTermEmotionSnapshot)
            and breadth.trade_date == emotion.trade_date
            and breadth.trade_date is not None
        ):
            breadth = breadth.model_copy(
                update={
                    "limit_up": emotion.limit_up_count,
                    "real_limit_up": emotion.limit_up_count,
                    "limit_down": emotion.limit_down_count,
                    "real_limit_down": emotion.limit_down_count,
                    "trade_date": emotion.trade_date or breadth.trade_date,
                }
            )

        market_module = (
            _error_module("Platform 公开指数日线适配", indices)
            if isinstance(indices, BaseException)
            else _module(source="Platform 公开指数日线适配", data=indices)
        )
        breadth_module = (
            _error_module("乐咕乐股赚钱效应（AKShare适配）", breadth)
            if isinstance(breadth, BaseException)
            else _module(source="乐咕乐股赚钱效应（AKShare适配）", data=breadth)
        )
        emotion_module = (
            _error_module("东方财富涨停板行情中心", emotion)
            if isinstance(emotion, BaseException)
            else _module(source="东方财富涨停板行情中心", data=emotion)
        )

        shenwan_data: AShareResearchAggregation | None = None
        shenwan_error: BaseException | None = None
        if isinstance(stocks, BaseException):
            shenwan_error = stocks
        elif isinstance(memberships, BaseException):
            shenwan_error = memberships
        else:
            try:
                shenwan_data = aggregate_shenwan_level2(
                    stocks=stocks,
                    memberships=memberships,
                    threshold_yuan=threshold_yuan,
                    top_n=10,
                )
            except Exception as exc:
                shenwan_error = exc
        shenwan_module = (
            _error_module(
                "申万宏源行业分类 / 东方财富A股行情（AKShare适配）",
                shenwan_error,
            )
            if shenwan_error is not None
            else _module(
                source="申万宏源行业分类 / 东方财富A股行情（AKShare适配）",
                data=shenwan_data,
            )
        )
        response = AShareDashboardResponse(
            generated_at=_now(),
            market_detail=market_module,
            breadth=breadth_module,
            shenwan=shenwan_module,
            emotion=emotion_module,
        )
        if collected_results is not None:
            return response
        if _DASHBOARD_CACHE.store(cache_key, response):
            return response
        stale = _DASHBOARD_CACHE.get(cache_key)
        if stale is not None:
            return _mark_dashboard_stale(stale.value)
        return response


# Explicit name for the only provider-facing path. API routes use
# ``get_persisted_a_share_dashboard`` below and never call this collector.
collect_a_share_dashboard = get_a_share_dashboard


async def get_live_a_share_sector_fund_flow() -> AShareLiveSectorFundFlowResponse:
    """Return a five-minute live industry-flow projection without touching SQLite."""
    cache_key = "a-share-live-sector-fund-flow"
    cached = _LIVE_SECTOR_FLOW_CACHE.get_fresh(cache_key)
    if cached is not None:
        return cached.value.model_copy(deep=True)
    async with _LIVE_SECTOR_FLOW_LOCK:
        cached = _LIVE_SECTOR_FLOW_CACHE.get_fresh(cache_key)
        if cached is not None:
            return cached.value.model_copy(deep=True)
        try:
            raw_rows = await _provider_call(_PROVIDER.a_share_sector_fund_flow())
            rows = [AShareLiveSectorFundFlow.model_validate(row) for row in raw_rows]
            if not rows:
                raise ResearchServiceError("live_sector_flow_empty", "实时板块资金流未返回有效数据")
            result = AShareLiveSectorFundFlowResponse(
                fetched_at=_now(),
                source="东方财富板块资金流（实时）",
                rows=rows,
            )
            _LIVE_SECTOR_FLOW_CACHE.store(cache_key, result)
            return result
        except ResearchServiceError:
            stale = _LIVE_SECTOR_FLOW_CACHE.get(cache_key)
            if stale is not None:
                return stale.value.model_copy(
                    deep=True,
                    update={
                        "status": "stale",
                        "is_stale": True,
                        "message": "更新暂不可用，显示上次有效数据",
                    },
                )
            raise
        except Exception as exc:
            stale = _LIVE_SECTOR_FLOW_CACHE.get(cache_key)
            if stale is not None:
                return stale.value.model_copy(
                    deep=True,
                    update={
                        "status": "stale",
                        "is_stale": True,
                        "message": "更新暂不可用，显示上次有效数据",
                    },
                )
            raise ResearchServiceError(
                "live_sector_flow_unavailable",
                "实时板块资金流暂不可用",
            ) from exc


async def get_live_a_share_market_turnover() -> AShareMarketTurnoverResponse:
    """A five-minute, backend-owned Top20 board plus daily >100bn count."""
    cache_key = "a-share-live-market-turnover"
    cached = _LIVE_TURNOVER_CACHE.get_fresh(cache_key)
    if cached is not None:
        return cached.value.model_copy(deep=True)
    async with _LIVE_TURNOVER_LOCK:
        cached = _LIVE_TURNOVER_CACHE.get_fresh(cache_key)
        if cached is not None:
            return cached.value.model_copy(deep=True)
        try:
            rows = await _provider_call(_PROVIDER.a_share_market_turnover())
            persisted = await asyncio.to_thread(read_dataset, "stocks")
            history = await asyncio.to_thread(read_hot_stock_history, days=None, matrix_days=None)
            daily_meta = await asyncio.to_thread(read_dataset_metadata, "stocks")
            high_count: int | None = None
            high_rows = []
            latest_history_date = history["dates"][-1] if history["dates"] else None
            latest_history_rows = [
                item
                for item in history["rows"]
                if latest_history_date and item.get("observedAt") == latest_history_date
            ]
            if latest_history_rows:
                high_rows = latest_history_rows
                high_count = len(latest_history_rows)
            if isinstance(persisted, list):
                snapshot_high_rows = [
                    item
                    for item in persisted
                    if isinstance(item, dict)
                    and str(item.get("securityCode", item.get("security_code", ""))).isdigit()
                    and len(str(item.get("securityCode", item.get("security_code", "")))) == 6
                    and Decimal(str(item.get("turnoverYuan", item.get("turnover_yuan", 0)) or 0))
                    > DEFAULT_THRESHOLD_YUAN
                ]
                if not latest_history_rows:
                    high_rows = snapshot_high_rows
                    high_count = len(snapshot_high_rows)
            result = AShareMarketTurnoverResponse(
                fetched_at=_now(),
                source="东方财富A股实时行情",
                high_turnover_count=high_count,
                daily_observed_at=latest_history_date
                or (daily_meta.get("observed_at") if daily_meta else None),
                high_turnover_rows=[
                    AShareMarketTurnoverRow.model_validate(
                        {
                            "securityCode": item.get("securityCode", item.get("security_code")),
                            "securityName": item.get("securityName", item.get("security_name")),
                            "returnPct": item.get("returnPct", item.get("return_pct")),
                            "turnoverYuan": item.get("turnoverYuan", item.get("turnover_yuan")),
                        }
                    )
                    for item in sorted(
                        high_rows,
                        key=lambda item: Decimal(
                            str(item.get("turnoverYuan", item.get("turnover_yuan", 0)) or 0)
                        ),
                        reverse=True,
                    )
                ],
                history_dates=history["dates"],
                history_counts=history["counts"],
                history_industries=history["industries"],
                historical_rows=history["rows"],
                rows=rows,
            )
            _LIVE_TURNOVER_CACHE.store(cache_key, result)
            return result
        except ResearchServiceError:
            stale = _LIVE_TURNOVER_CACHE.get(cache_key)
            if stale is not None:
                return stale.value.model_copy(
                    deep=True,
                    update={
                        "status": "stale",
                        "is_stale": True,
                        "message": "更新暂不可用，显示上次有效数据",
                    },
                )
            raise
        except Exception as exc:
            stale = _LIVE_TURNOVER_CACHE.get(cache_key)
            if stale is not None:
                return stale.value.model_copy(
                    deep=True,
                    update={
                        "status": "stale",
                        "is_stale": True,
                        "message": "更新暂不可用，显示上次有效数据",
                    },
                )
            raise ResearchServiceError(
                "live_market_turnover_unavailable", "实时成交额榜暂不可用"
            ) from exc


async def get_persisted_a_share_dashboard() -> AShareDashboardResponse:
    """Read the last completed A-share snapshot; never invokes an upstream provider."""
    snapshot = await asyncio.to_thread(read_dashboard)
    if snapshot is not None:
        return snapshot
    now = _now()
    no_data = _module(
        source="platform-research-snapshot",
        data=None,
        status="no_data",
        message="后台研究刷新尚未生成可用快照",
        fetched_at=now,
    )
    return AShareDashboardResponse(
        generated_at=now,
        market_detail=no_data,
        breadth=no_data.model_copy(deep=True),
        shenwan=no_data.model_copy(deep=True),
        emotion=no_data.model_copy(deep=True),
        market_history=[],
    )


def _mark_dashboard_stale(value: AShareDashboardResponse) -> AShareDashboardResponse:
    copied = value.model_copy(deep=True)
    copied.generated_at = _now()
    for module in (
        copied.market_detail,
        copied.breadth,
        copied.shenwan,
        copied.emotion,
    ):
        module.meta.status = "stale"
        module.meta.is_stale = True
        module.meta.message = "当前刷新失败，展示上一份有效数据"
    return copied


def _stock_lock(code: str) -> asyncio.Lock:
    return _STOCK_LOCKS.setdefault(code, asyncio.Lock())


async def get_stock_snapshot(code: str) -> StockSnapshotResponse:
    normalized = code.strip()
    if not re.fullmatch(r"\d{6}", normalized):
        raise ResearchServiceError(
            "invalid_security_code",
            "A股代码必须为6位数字",
            status_code=422,
        )
    cached = _STOCK_CACHE.get_fresh(normalized)
    if cached is not None:
        return cached.value

    async with _stock_lock(normalized):
        cached = _STOCK_CACHE.get_fresh(normalized)
        if cached is not None:
            return cached.value
        try:
            quote = _require_mapping(
                await _provider_call(_PROVIDER.stock_quote(normalized)),
                "腾讯财经",
            )
        except Exception as exc:
            stale = _STOCK_CACHE.get(normalized)
            if stale is not None:
                return _mark_stock_stale(stale.value)
            raise ResearchServiceError(
                "stock_quote_unavailable",
                f"未能读取{normalized}的基础行情: {exc}",
            ) from exc

        price = quote.get("price")
        calls: tuple[tuple[str, str, Awaitable[Any]], ...] = (
            (
                "consensus",
                "同花顺一致预期（AKShare适配）",
                _PROVIDER.stock_forecast(normalized, price),
            ),
            (
                "financials",
                "同花顺财务摘要（AKShare适配）",
                _PROVIDER.stock_financials(normalized),
            ),
            (
                "valuationPercentile",
                "百度股市通估值历史（AKShare适配）",
                _PROVIDER.stock_valuation_percentile(normalized),
            ),
            ("reports", "东方财富研报中心", _PROVIDER.stock_reports(normalized)),
            (
                "announcements",
                "东方财富公告中心",
                _PROVIDER.stock_announcements(normalized),
            ),
            ("news", "东方财富个股新闻（AKShare适配）", _PROVIDER.stock_news(normalized)),
            ("margin", "东方财富数据中心", _PROVIDER.stock_margin(normalized)),
            ("holders", "东方财富数据中心", _PROVIDER.stock_holders(normalized)),
            ("fundFlow", "东方财富资金流", _PROVIDER.stock_fund_flow(normalized)),
            ("dividends", "东方财富数据中心", _PROVIDER.stock_dividends(normalized)),
            (
                "blockTrades",
                "东方财富数据中心",
                _PROVIDER.stock_block_trades(normalized),
            ),
            ("dragonTiger", "东方财富龙虎榜", _PROVIDER.stock_dragon_tiger(normalized)),
            ("lockup", "东方财富限售解禁", _PROVIDER.stock_lockup(normalized)),
            (
                "investorQa",
                "巨潮资讯互动易",
                _PROVIDER.stock_investor_qa(normalized),
            ),
            ("shenwan", "申万宏源行业分类（AKShare适配）", _stock_membership(normalized)),
        )
        results = await asyncio.gather(
            *(_provider_call(item[2]) for item in calls),
            return_exceptions=True,
        )
        modules: dict[str, ResearchModuleResult] = {
            "quoteValuation": _module(source="腾讯财经", data=quote)
        }
        for (key, source, _), result in zip(calls, results, strict=True):
            modules[key] = (
                _error_module(source, result)
                if isinstance(result, BaseException)
                else _module(source=source, data=result)
            )
        available = sum(
            1
            for module in modules.values()
            if module.meta.status == "ready" and _meaningful(module.data)
        )
        completeness = (Decimal(available) / Decimal(len(modules)) * Decimal("100")).quantize(
            PCT_QUANT, rounding=ROUND_HALF_UP
        )
        response = StockSnapshotResponse(
            security_code=normalized,
            security_name=str(quote.get("name") or "") or None,
            generated_at=_now(),
            completeness_pct=completeness,
            modules=modules,
        )
        _STOCK_CACHE.store(normalized, response)
        return response


async def _stock_membership(code: str) -> dict[str, Any]:
    values = await _memberships()
    item = next(
        (membership for membership in values if membership.security_code == code),
        None,
    )
    return item.model_dump(by_alias=True) if item is not None else {}


def _mark_stock_stale(value: StockSnapshotResponse) -> StockSnapshotResponse:
    copied = value.model_copy(deep=True)
    copied.generated_at = _now()
    for module in copied.modules.values():
        module.meta.status = "stale"
        module.meta.is_stale = True
        module.meta.message = "当前刷新失败，展示上一份有效数据"
    return copied


_MACRO_HISTORY = MacroProbabilityHistoryStore()


async def get_macro_expectations() -> MacroExpectationResponse:
    cached = _MACRO_CACHE.get_fresh("macro")
    if cached is not None:
        return cached.value
    async with _MACRO_LOCK:
        cached = _MACRO_CACHE.get_fresh("macro")
        if cached is not None:
            return cached.value
        try:
            events = _require_model_list(
                await _provider_call(_PROVIDER.macro_expectation_events()),
                MacroExpectationEvent,
                "Polymarket公开市场接口",
            )
            events = await _MACRO_HISTORY.update(events)
            response = MacroExpectationResponse(
                generated_at=_now(),
                events=_module(source="Polymarket公开市场接口", data=events),
            )
            _MACRO_CACHE.store("macro", response)
            return response
        except Exception as exc:
            stale = _MACRO_CACHE.get("macro")
            if stale is not None:
                copied = stale.value.model_copy(deep=True)
                copied.generated_at = _now()
                copied.events.meta.status = "stale"
                copied.events.meta.is_stale = True
                copied.events.meta.message = "当前刷新失败，展示上一份有效概率记录"
                return copied
            return MacroExpectationResponse(
                generated_at=_now(),
                events=_error_module("Polymarket公开市场接口", exc),
            )
