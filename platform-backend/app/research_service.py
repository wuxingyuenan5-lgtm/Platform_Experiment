from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from app.a_share_research_policy import aggregate_shenwan_level2
from app.research_cache import LastKnownGoodResearchCache
from app.research_data_schemas import (
    AShareDashboardResponse,
    AShareResearchAggregation,
    MacroExpectationEvent,
    MacroExpectationResponse,
    MacroProbabilityPoint,
    ResearchModuleResult,
    ResearchSourceMeta,
    ShenwanMembership,
    StockSnapshotResponse,
)
from app.research_providers import FreeResearchProvider

DEFAULT_THRESHOLD_YUAN = Decimal("10000000000")
PCT_QUANT = Decimal("0.01")

_PROVIDER = FreeResearchProvider()
_DASHBOARD_CACHE = LastKnownGoodResearchCache[AShareDashboardResponse](
    ttl=timedelta(minutes=5),
    is_meaningful=lambda value: bool(value.market_detail.data or value.breadth.data),
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


def _module(
    *,
    source: str,
    data: Any,
    status: str | None = None,
    error_code: str | None = None,
    message: str | None = None,
    fetched_at: datetime | None = None,
    is_stale: bool = False,
) -> ResearchModuleResult:
    observed_at = fetched_at or _now()
    inferred_status = status
    if inferred_status is None:
        inferred_status = "ready" if _meaningful(data) else "no_data"
    return ResearchModuleResult(
        meta=ResearchSourceMeta(
            source=source,
            fetched_at=observed_at,
            status=inferred_status,
            is_stale=is_stale,
            error_code=error_code,
            message=message,
        ),
        data=data,
    )


def _error_module(source: str, exc: BaseException) -> ResearchModuleResult:
    return _module(
        source=source,
        data=None,
        status="error",
        error_code=type(exc).__name__,
        message=str(exc)[:500] or "数据源暂时不可用",
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
            value = await _PROVIDER.shenwan_memberships()
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
) -> AShareDashboardResponse:
    if threshold_yuan <= 0:
        raise ResearchServiceError(
            "invalid_turnover_threshold",
            "成交额阈值必须大于0",
            status_code=422,
        )
    cache_key = f"dashboard:{threshold_yuan.normalize()}"
    cached = _DASHBOARD_CACHE.get_fresh(cache_key)
    if cached is not None:
        return cached.value

    async with _DASHBOARD_LOCK:
        cached = _DASHBOARD_CACHE.get_fresh(cache_key)
        if cached is not None:
            return cached.value
        results = await asyncio.gather(
            _PROVIDER.index_snapshots(),
            _PROVIDER.market_activity(),
            _PROVIDER.a_share_spot(),
            _memberships(),
            _PROVIDER.short_term_emotion(),
            return_exceptions=True,
        )
        indices, breadth, stocks, memberships, emotion = results
        market_module = (
            _error_module("东方财富指数历史行情（AKShare适配）", indices)
            if isinstance(indices, BaseException)
            else _module(source="东方财富指数历史行情（AKShare适配）", data=indices)
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
            except Exception as exc:  # one aggregation error must not break other modules
                shenwan_error = exc
        shenwan_module = (
            _error_module("申万宏源行业分类 / 东方财富A股行情（AKShare适配）", shenwan_error)
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
        if _DASHBOARD_CACHE.store(cache_key, response):
            return response
        stale = _DASHBOARD_CACHE.get(cache_key)
        if stale is not None:
            return _mark_dashboard_stale(stale.value)
        return response


def _mark_dashboard_stale(value: AShareDashboardResponse) -> AShareDashboardResponse:
    copied = value.model_copy(deep=True)
    copied.generated_at = _now()
    for module in (copied.market_detail, copied.breadth, copied.shenwan, copied.emotion):
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
            quote = await _PROVIDER.stock_quote(normalized)
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
            ("consensus", "同花顺一致预期（AKShare适配）", _PROVIDER.stock_forecast(normalized, price)),
            ("financials", "同花顺财务摘要（AKShare适配）", _PROVIDER.stock_financials(normalized)),
            ("valuationPercentile", "百度股市通估值历史（AKShare适配）", _PROVIDER.stock_valuation_percentile(normalized)),
            ("reports", "东方财富研报中心", _PROVIDER.stock_reports(normalized)),
            ("announcements", "东方财富公告中心", _PROVIDER.stock_announcements(normalized)),
            ("news", "东方财富个股新闻（AKShare适配）", _PROVIDER.stock_news(normalized)),
            ("margin", "东方财富数据中心", _PROVIDER.stock_margin(normalized)),
            ("holders", "东方财富数据中心", _PROVIDER.stock_holders(normalized)),
            ("fundFlow", "东方财富资金流", _PROVIDER.stock_fund_flow(normalized)),
            ("dividends", "东方财富数据中心", _PROVIDER.stock_dividends(normalized)),
            ("blockTrades", "东方财富数据中心", _PROVIDER.stock_block_trades(normalized)),
            ("dragonTiger", "东方财富龙虎榜", _PROVIDER.stock_dragon_tiger(normalized)),
            ("lockup", "东方财富限售解禁", _PROVIDER.stock_lockup(normalized)),
            ("investorQa", "巨潮资讯互动易", _PROVIDER.stock_investor_qa(normalized)),
            ("shenwan", "申万宏源行业分类（AKShare适配）", _stock_membership(normalized)),
        )
        results = await asyncio.gather(*(item[2] for item in calls), return_exceptions=True)
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
        completeness = (
            Decimal(available) / Decimal(len(modules)) * Decimal("100")
        ).quantize(PCT_QUANT, rounding=ROUND_HALF_UP)
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
    item = next((membership for membership in values if membership.security_code == code), None)
    return item.model_dump(by_alias=True) if item is not None else {}


def _mark_stock_stale(value: StockSnapshotResponse) -> StockSnapshotResponse:
    copied = value.model_copy(deep=True)
    copied.generated_at = _now()
    for module in copied.modules.values():
        module.meta.status = "stale"
        module.meta.is_stale = True
        module.meta.message = "当前刷新失败，展示上一份有效数据"
    return copied


class MacroProbabilityHistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        configured = os.environ.get("RESEARCH_MACRO_HISTORY_PATH")
        self._path = path or Path(configured or "data/research/macro_probability_history.json")
        self._lock = asyncio.Lock()

    async def update(self, events: list[MacroExpectationEvent]) -> list[MacroExpectationEvent]:
        async with self._lock:
            history = await asyncio.to_thread(self._read)
            observed_at = _now()
            cutoff = observed_at - timedelta(days=90)
            for event in events:
                points = history.setdefault(event.event_id, [])
                points.append(
                    {
                        "observedAt": observed_at.isoformat(),
                        "probabilityPct": str(event.current_probability_pct),
                    }
                )
                deduplicated: dict[str, dict[str, str]] = {}
                for point in points:
                    point_time = str(point.get("observedAt") or "")
                    try:
                        parsed = datetime.fromisoformat(point_time.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if parsed >= cutoff:
                        deduplicated[parsed.replace(second=0, microsecond=0).isoformat()] = point
                history[event.event_id] = list(deduplicated.values())
                normalized_points = [
                    MacroProbabilityPoint(
                        observed_at=datetime.fromisoformat(
                            str(point["observedAt"]).replace("Z", "+00:00")
                        ),
                        probability_pct=Decimal(str(point["probabilityPct"])),
                    )
                    for point in history[event.event_id]
                ]
                normalized_points.sort(key=lambda item: item.observed_at)
                event.history = normalized_points
                event.change_1d_pct_points = _history_change(normalized_points, timedelta(days=1))
                event.change_7d_pct_points = _history_change(normalized_points, timedelta(days=7))
            await asyncio.to_thread(self._write, history)
            return events

    def _read(self) -> dict[str, list[dict[str, str]]]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write(self, value: dict[str, list[dict[str, str]]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._path)


_MACRO_HISTORY = MacroProbabilityHistoryStore()


def _history_change(
    points: list[MacroProbabilityPoint],
    distance: timedelta,
) -> Decimal | None:
    if len(points) < 2:
        return None
    target = points[-1].observed_at - distance
    candidates = [point for point in points[:-1] if point.observed_at <= target]
    if not candidates:
        return None
    return points[-1].probability_pct - candidates[-1].probability_pct


async def get_macro_expectations() -> MacroExpectationResponse:
    cached = _MACRO_CACHE.get_fresh("macro")
    if cached is not None:
        return cached.value
    async with _MACRO_LOCK:
        cached = _MACRO_CACHE.get_fresh("macro")
        if cached is not None:
            return cached.value
        try:
            events = await _PROVIDER.macro_expectation_events()
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
