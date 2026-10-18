from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, field_validator

from app.auth import Principal, require_permission
from app.config import get_settings
from app.research_a_share_refresh import refresh_a_share_research
from app.research_a_share_repository import (
    read_index_history,
    read_market_amount_page,
    read_refresh_status,
    read_stock_detail,
    read_stock_pool,
    update_stock_pool_membership,
)
from app.research_cross_asset import read_cross_asset
from app.research_cumulative_volatility import read_cumulative_volatility
from app.research_data_schemas import (
    AShareDashboardResponse,
    AShareLiveSectorFundFlowResponse,
    AShareMarketTurnoverResponse,
    StockSnapshotResponse,
)
from app.research_equity_observatory import read_equity_observatory
from app.research_gold import analyst_page, read_gold
from app.research_overseas_refresh import refresh_overseas
from app.research_overseas_repository import (
    read_dataset_health,
    read_etf_flow,
    read_iv_snapshot_history,
    read_iv_snapshot_latest,
    read_latest_observed_at,
    read_latest_series,
)
from app.research_provider_commodity_dashboard import CommodityDashboardProvider
from app.research_provider_crypto_dashboard import CryptoDashboardProvider
from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro import (
    MacroExpectationFeedResponse,
    MacroResearchProvider,
)
from app.research_provider_macro_dashboard import MacroDashboardProvider, MacroDashboardResponse
from app.research_provider_market_detail import MarketDetailProvider, MarketDetailResponse
from app.research_provider_overseas import fetch_deribit_dvol
from app.research_service import (
    ResearchServiceError,
    get_live_a_share_market_turnover,
    get_live_a_share_sector_fund_flow,
    get_persisted_a_share_dashboard,
    get_stock_snapshot,
)
from app.research_watchlist_schemas import ReplaceResearchWatchlistRequest, ResearchWatchlistItem
from app.research_watchlist_service import (
    ResearchWatchlistServiceError,
    get_research_watchlist,
    normalize_stock_code,
    replace_research_watchlist,
)


class StockPoolFocusRequest(BaseModel):
    codes: list[str] = Field(default_factory=list, max_length=200)
    expected_version: int = Field(alias="expectedVersion", ge=0)

    @field_validator("codes")
    @classmethod
    def normalize_codes(cls, values: list[str]) -> list[str]:
        codes = [normalize_stock_code(value) for value in values]
        if any(not code for code in codes):
            raise ValueError("请输入有效的6位A股或5位港股代码")
        return list(dict.fromkeys(codes))


class StockPoolBatchRequest(BaseModel):
    codes: list[str] = Field(min_length=1, max_length=50)

    _normalize_codes = field_validator("codes")(StockPoolFocusRequest.normalize_codes.__func__)


settings = get_settings()
router = APIRouter(prefix=f"{settings.api_prefix}/research", tags=["research"])
ResearchPrincipal = Annotated[Principal, Depends(require_permission("research.read"))]
_macro_expectation_provider = MacroResearchProvider(
    timeout_seconds=20.0,
    user_agent="Platform-API macro-expectations",
)
_market_detail_provider = MarketDetailProvider(
    timeout_seconds=20.0,
    user_agent="Platform-API hedge-board-market-detail",
)
_macro_dashboard_provider = MacroDashboardProvider(
    timeout_seconds=12.0,
    user_agent="Platform-API hedge-board-macro-dashboard",
)
_commodity_dashboard_provider = CommodityDashboardProvider(
    timeout_seconds=12.0,
    user_agent="Platform-API hedge-board-commodity-dashboard",
)
_crypto_dashboard_provider = CryptoDashboardProvider(
    timeout_seconds=12.0,
    user_agent="Platform-API hedge-board-crypto-dashboard",
)


def _raise_service_error(exc: ResearchServiceError | ResearchWatchlistServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _cache_header(response: Response, seconds: int) -> None:
    response.headers["Cache-Control"] = f"private, max-age={seconds}, stale-if-error=3600"


@router.get("/cross-asset")
def cross_asset(_: ResearchPrincipal, days: int = Query(default=90, ge=30, le=180)):
    return jsonable_encoder(read_cross_asset(days), custom_encoder={Decimal: str})


@router.get("/equity-observatory/{market}")
def equity_observatory(market: str, _: ResearchPrincipal, response: Response):
    if market not in {"cn", "us"}:
        raise HTTPException(422, detail="Unsupported equity market")
    response.headers["Cache-Control"] = "no-store"
    return jsonable_encoder(read_equity_observatory(market), custom_encoder={Decimal: str})


@router.get("/a-share/dashboard", response_model=AShareDashboardResponse)
async def a_share_dashboard(
    response: Response,
    _: ResearchPrincipal,
) -> AShareDashboardResponse:
    try:
        result = await get_persisted_a_share_dashboard()
    except ResearchServiceError as exc:
        _raise_service_error(exc)
    _cache_header(response, 0)
    return result


@router.get("/a-share/market-history")
async def a_share_market_history(
    _: ResearchPrincipal,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
) -> dict[str, object]:
    return await asyncio.to_thread(read_market_amount_page, page, page_size)


@router.get("/a-share/stocks/{code}/snapshot", response_model=StockSnapshotResponse)
async def stock_snapshot(
    code: str,
    response: Response,
    _: ResearchPrincipal,
) -> StockSnapshotResponse:
    try:
        result = await get_stock_snapshot(code)
    except ResearchServiceError as exc:
        _raise_service_error(exc)
    _cache_header(response, 300)
    return result


@router.get("/a-share/live-sector-flow", response_model=AShareLiveSectorFundFlowResponse)
async def a_share_live_sector_flow(
    response: Response,
    _: ResearchPrincipal,
) -> AShareLiveSectorFundFlowResponse:
    try:
        result = await get_live_a_share_sector_fund_flow()
    except ResearchServiceError as exc:
        _raise_service_error(exc)
    _cache_header(response, 300)
    return result


@router.get("/a-share/live-market-turnover", response_model=AShareMarketTurnoverResponse)
async def a_share_live_market_turnover(
    response: Response, _: ResearchPrincipal
) -> AShareMarketTurnoverResponse:
    try:
        result = await get_live_a_share_market_turnover()
    except ResearchServiceError as exc:
        _raise_service_error(exc)
    # Keep the five-minute last-known-good cache on the server.  Browser-side
    # max-age would otherwise preserve an older count across a user reload.
    _cache_header(response, 0)
    return result


@router.get("/a-share/stock-pool", tags=["research"])
async def a_share_stock_pool(response: Response, principal: ResearchPrincipal) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    focus = await asyncio.to_thread(get_research_watchlist, principal.user_id)
    return {"data": await asyncio.to_thread(read_stock_pool, [item.code for item in focus.items])}


@router.get("/a-share/indices/{code}/history")
async def a_share_index_history(
    code: str, response: Response, _: ResearchPrincipal
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    return {"data": await asyncio.to_thread(read_index_history, code)}


@router.get("/a-share/stocks/{code}/history")
async def a_share_stock_history(
    code: str, response: Response, _: ResearchPrincipal
) -> dict[str, object]:
    normalized = normalize_stock_code(code)
    if not normalized:
        raise HTTPException(422, detail={"code": "invalid_stock_code", "message": "证券代码无效"})
    response.headers["Cache-Control"] = "no-store"
    return {"data": await asyncio.to_thread(read_stock_detail, normalized)}


@router.get("/a-share/refresh-status", tags=["research"])
async def a_share_refresh_status(_: ResearchPrincipal) -> dict[str, object]:
    return {"data": await asyncio.to_thread(read_refresh_status)}


@router.post("/a-share/refresh", tags=["research"])
async def trigger_a_share_refresh(
    _: Annotated[Principal, Depends(require_permission("research.write"))],
) -> dict[str, object]:
    status = await refresh_a_share_research(force=True)
    if status == "error":
        raise HTTPException(
            503,
            detail={"code": "research_refresh_failed", "message": "更新未完成，已保留上次有效数据"},
        )
    return {"data": {"status": status, "run": await asyncio.to_thread(read_refresh_status)}}


@router.get("/a-share/stock-pool/focus", tags=["research"])
async def a_share_stock_pool_focus(
    response: Response, principal: ResearchPrincipal
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    result = await asyncio.to_thread(get_research_watchlist, principal.user_id)
    return {
        "data": {"codes": [item.code for item in result.items], "rowVersion": result.row_version}
    }


@router.post("/a-share/stock-pool/focus", tags=["research"])
async def put_a_share_stock_pool_focus(
    request_body: StockPoolFocusRequest,
    principal: Annotated[Principal, Depends(require_permission("profile.update_self"))],
) -> dict[str, object]:
    try:
        result = await asyncio.to_thread(
            replace_research_watchlist,
            user_id=principal.user_id,
            request=ReplaceResearchWatchlistRequest(
                expectedVersion=request_body.expected_version,
                items=[
                    ResearchWatchlistItem(code=code, name=code, group="近期关注")
                    for code in request_body.codes
                ],
            ),
        )
    except ResearchWatchlistServiceError as exc:
        _raise_service_error(exc)
    return {
        "data": {"codes": [item.code for item in result.items], "rowVersion": result.row_version}
    }


@router.post("/a-share/stock-pool/add-batch", tags=["research"])
async def add_a_share_stock_pool_batch(
    request_body: StockPoolBatchRequest,
    _: Annotated[Principal, Depends(require_permission("research.write"))],
) -> dict[str, object]:
    codes = request_body.codes
    try:
        count = await asyncio.to_thread(update_stock_pool_membership, add_codes=codes)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "stock_pool_limit", "message": str(exc)}) from exc
    return {"data": {"ok": True, "added": codes, "failed": [], "count": count}}


@router.delete("/a-share/stock-pool/remove", tags=["research"])
async def remove_a_share_stock_pool(
    _: Annotated[Principal, Depends(require_permission("research.write"))],
    instrument_id: str = Query(...),
) -> dict[str, object]:
    code = normalize_stock_code(instrument_id)
    if not code:
        raise HTTPException(422, detail={"code": "invalid_stock_code", "message": "证券代码无效"})
    count = await asyncio.to_thread(update_stock_pool_membership, remove_code=code)
    return {"data": {"ok": True, "count": count}}


@router.get("/macro/expectations", response_model=MacroExpectationFeedResponse)
async def macro_expectations(
    response: Response,
    _: ResearchPrincipal,
) -> MacroExpectationFeedResponse:
    try:
        result = await _macro_expectation_provider.macro_expectation_contract()
    except ResearchProviderError:
        result = MacroExpectationFeedResponse(
            status="error",
            source="platform-data",
            updated_at=datetime.now(UTC),
            events=[],
        )
    _cache_header(response, 300)
    return result


@router.get("/market-detail/{market_id}", response_model=MarketDetailResponse)
async def market_detail(
    market_id: str,
    response: Response,
    _: ResearchPrincipal,
) -> MarketDetailResponse:
    try:
        result = await _market_detail_provider.get(market_id)
    except ResearchProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "market_detail_unavailable", "message": str(exc)},
        ) from exc
    _cache_header(response, 300)
    return result


@router.get("/macro/dashboard-v1", response_model=MacroDashboardResponse)
async def macro_dashboard_v1(response: Response, _: ResearchPrincipal) -> MacroDashboardResponse:
    try:
        result = await _macro_dashboard_provider.get()
    except ResearchProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "macro_dashboard_unavailable", "message": str(exc)},
        ) from exc
    _cache_header(response, 300)
    return result


@router.get("/commodity/dashboard-v1", response_model=MacroDashboardResponse)
async def commodity_dashboard_v1(
    response: Response, _: ResearchPrincipal
) -> MacroDashboardResponse:
    try:
        result = await _commodity_dashboard_provider.get()
    except ResearchProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "commodity_dashboard_unavailable", "message": str(exc)},
        ) from exc
    _cache_header(response, 300)
    return result


@router.get("/commodity/gold-positioning")
def gold_positioning(_: ResearchPrincipal):
    try:
        return read_gold("gold-positioning")
    except ResearchProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/commodity/gold-report")
def gold_report(_: ResearchPrincipal):
    try:
        return read_gold("gold-report")
    except ResearchProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/commodity/analyst-views")
def gold_analysts(
    _: ResearchPrincipal,
    author: str = Query("", max_length=80),
    stance: str = Query("", max_length=30),
    query: str = Query("", max_length=150),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
):
    try:
        return analyst_page(
            author=author, stance=stance, query=query, page=page, page_size=page_size
        )
    except ResearchProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/crypto/dashboard-v1", response_model=MacroDashboardResponse)
async def crypto_dashboard_v1(response: Response, _: ResearchPrincipal) -> MacroDashboardResponse:
    try:
        result = await _crypto_dashboard_provider.get()
    except ResearchProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "crypto_dashboard_unavailable", "message": str(exc)},
        ) from exc
    _cache_header(response, 300)
    return result


@router.get("/macro/fedwatch", tags=["research"])
async def macro_fedwatch(response: Response, _: ResearchPrincipal) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    series = await asyncio.to_thread(read_latest_series, "macro_fedwatch")
    meta = series.pop("__meta__", {})
    meetings = [
        {
            "date": code,
            "probabilities": payload.get("probabilities", {}),
            "contract": payload.get("contract"),
        }
        for code, payload in sorted(series.items())
    ]
    health = await asyncio.to_thread(read_dataset_health, "macro_fedwatch")
    return {
        "data": {
            "effr": meta.get("effr"),
            "currentTarget": meta.get("currentTarget"),
            "observedAt": meta.get("observedAt")
            or await asyncio.to_thread(read_latest_observed_at, "macro_fedwatch"),
            "settlementSource": meta.get("settlementSource"),
            "zqPricing": meta.get("zqPricing", []),
            "meetings": meetings,
            "status": health["status"],
            "lastError": health["lastError"],
        }
    }


@router.get("/crypto/etf-flow", tags=["research"])
async def crypto_etf_flow(response: Response, _: ResearchPrincipal) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    data = await asyncio.to_thread(read_etf_flow, 3650, "btc")
    health = await asyncio.to_thread(read_dataset_health, "crypto_etf_flow")
    return {"data": {**data, "status": health["status"], "lastError": health["lastError"]}}


@router.get("/crypto/eth-etf-flow", tags=["research"])
async def crypto_eth_etf_flow(response: Response, _: ResearchPrincipal) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    data = await asyncio.to_thread(read_etf_flow, 3650, "eth")
    health = await asyncio.to_thread(read_dataset_health, "crypto_eth_etf_flow")
    return {"data": {**data, "status": health["status"], "lastError": health["lastError"]}}


@router.get("/cumulative-volatility", tags=["research"])
async def cumulative_volatility(
    response: Response,
    _: ResearchPrincipal,
    asset: str = Query("btc", pattern="^(btc|gold)$"),
    days: int = Query(365, ge=1, le=365),
    interval: str = Query("15m", pattern="^(15m|1h|4h)$"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> dict[str, object]:
    """读取共享 Bybit 行情经后端计算的 UTC 盘口累计波动与价格叠加。"""
    response.headers["Cache-Control"] = "no-store"
    try:
        data = await asyncio.to_thread(
            read_cumulative_volatility, asset, days, interval, start=start, end=end
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": data}


@router.get("/crypto/iv-term", tags=["research"])
async def crypto_iv_term(response: Response, _: ResearchPrincipal) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    series = await asyncio.to_thread(read_latest_series, "crypto_iv_term")
    meta = series.pop("__meta__", {})
    term = [
        {**payload, "expiry": code}
        for code, payload in sorted(series.items(), key=lambda kv: kv[1].get("daysToExpiry", 0))
    ]
    health = await asyncio.to_thread(read_dataset_health, "crypto_iv_term")
    return {
        "data": {
            "index": meta.get("index"),
            "observedAt": await asyncio.to_thread(read_latest_observed_at, "crypto_iv_term"),
            "term": term,
            "status": health["status"],
            "lastError": health["lastError"],
        }
    }


@router.get("/crypto/iv-snapshot", tags=["research"])
async def crypto_iv_snapshot(response: Response, _: ResearchPrincipal) -> dict[str, object]:
    """1M/3M/6M/1Y 4 时段当前快照（BTC 指数价 + DVOL + 每时段 IV）。"""
    response.headers["Cache-Control"] = "no-store"
    data = await asyncio.to_thread(read_iv_snapshot_latest)
    health = await asyncio.to_thread(read_dataset_health, "crypto_iv_snapshot")
    return {"data": {**data, "status": health["status"], "lastError": health["lastError"]}}


@router.get("/crypto/iv-history", tags=["research"])
async def crypto_iv_history(
    response: Response,
    _: ResearchPrincipal,
    tenor: str = Query(..., pattern="^(1M|3M|6M|1Y)$"),
    days: int = Query(365, ge=1, le=730),
) -> dict[str, object]:
    """读单一时段累积历史快照（最多 2 年）。"""
    response.headers["Cache-Control"] = "no-store"
    history = await asyncio.to_thread(read_iv_snapshot_history, tenor, days)
    health = await asyncio.to_thread(read_dataset_health, "crypto_iv_snapshot")
    if history:
        ivs = [p["iv"] for p in history if p.get("iv") is not None]
        stats = {
            "current": ivs[-1] if ivs else None,
            "rangeLow": min(ivs) if ivs else None,
            "rangeHigh": max(ivs) if ivs else None,
            "historyLow": min(ivs) if ivs else None,
            "historyHigh": max(ivs) if ivs else None,
            "count": len(ivs),
        }
    else:
        stats = {
            "current": None,
            "rangeLow": None,
            "rangeHigh": None,
            "historyLow": None,
            "historyHigh": None,
            "count": 0,
        }
    return {
        "data": {
            "tenor": tenor,
            "history": history,
            "stats": stats,
            "status": health["status"],
            "lastError": health["lastError"],
        }
    }


@router.get("/crypto/iv-dvol", tags=["research"])
async def crypto_iv_dvol(
    response: Response,
    _: ResearchPrincipal,
    days: int = Query(90, ge=7, le=365),
) -> dict[str, object]:
    """Deribit BTC DVOL 历史走势（30日 IV 年化），用于 IV 面板「历史走势」图。

    不落库：实时拉取 Deribit 公开接口，命中限速时返回 stale 状态但仍尝试返回最新缓存。
    """
    response.headers["Cache-Control"] = "no-store"
    try:
        data = await asyncio.to_thread(fetch_deribit_dvol, days)
    except ResearchProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "deribit_dvol_unavailable", "message": str(exc)},
        ) from exc
    return {"data": data}


@router.post("/overseas/refresh", tags=["research"])
async def trigger_overseas_refresh(
    _: Annotated[Principal, Depends(require_permission("research.write"))],
) -> dict[str, object]:
    """手动触发海外公开研究数据刷新（需 ``research.write``）。

    失败语义：刷新失败**保留最后一次有效数据**，不返回伪造值。整体失败时返回
    503 并携带各源状态；部分源失败时返回 200 但 ``status=partial``，由前端
    按源展示 stale 标记。
    """
    status = await refresh_overseas(force=True)
    health = {
        dataset: await asyncio.to_thread(read_dataset_health, dataset)
        for dataset in (
            "macro_fedwatch",
            "crypto_etf_flow",
            "crypto_eth_etf_flow",
            "crypto_iv_snapshot",
        )
    }
    if status == "error":
        raise HTTPException(
            503,
            detail={
                "code": "overseas_refresh_failed",
                "message": "更新未完成，已保留上次有效数据",
                "sources": health,
            },
        )
    return {"data": {"status": status, "sources": health}}
