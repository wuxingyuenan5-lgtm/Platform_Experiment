from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.auth import Principal, require_permission
from app.config import get_settings
from app.research_data_schemas import (
    AShareDashboardResponse,
    AShareLiveSectorFundFlowResponse,
    AShareMarketTurnoverResponse,
    StockSnapshotResponse,
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
from app.research_service import (
    ResearchServiceError,
    get_live_a_share_sector_fund_flow,
    get_live_a_share_market_turnover,
    get_persisted_a_share_dashboard,
    get_stock_snapshot,
)
from app.research_a_share_repository import read_refresh_status, read_stock_pool, read_stock_pool_focus, update_stock_pool_membership, write_stock_pool_focus
from app.research_a_share_refresh import refresh_a_share_research


class StockPoolFocusRequest(BaseModel):
    codes: list[str] = Field(default_factory=list, max_length=200)


class StockPoolBatchRequest(BaseModel):
    codes: list[str] = Field(default_factory=list, max_length=50)

settings = get_settings()
router = APIRouter(prefix=f"{settings.api_prefix}/research", tags=["research"])
ResearchPrincipal = Annotated[Principal, Depends(require_permission("platform:read"))]
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


def _raise_service_error(exc: ResearchServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _cache_header(response: Response, seconds: int) -> None:
    response.headers["Cache-Control"] = f"private, max-age={seconds}, stale-if-error=3600"


@router.get("/a-share/dashboard", response_model=AShareDashboardResponse)
async def a_share_dashboard(
    response: Response,
    _: ResearchPrincipal,
) -> AShareDashboardResponse:
    try:
        result = await get_persisted_a_share_dashboard()
    except ResearchServiceError as exc:
        _raise_service_error(exc)
    _cache_header(response, 60)
    return result


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
async def a_share_live_market_turnover(response: Response, _: ResearchPrincipal) -> AShareMarketTurnoverResponse:
    try:
        result = await get_live_a_share_market_turnover()
    except ResearchServiceError as exc:
        _raise_service_error(exc)
    # Keep the five-minute last-known-good cache on the server.  Browser-side
    # max-age would otherwise preserve an older count across a user reload.
    _cache_header(response, 0)
    return result


@router.get("/a-share/stock-pool", tags=["research"])
async def a_share_stock_pool(_: ResearchPrincipal) -> dict[str, object]:
    return {"data": await asyncio.to_thread(read_stock_pool)}


@router.get("/a-share/refresh-status", tags=["research"])
async def a_share_refresh_status(_: ResearchPrincipal) -> dict[str, object]:
    return {"data": await asyncio.to_thread(read_refresh_status)}


@router.post("/a-share/refresh", tags=["research"])
async def trigger_a_share_refresh(
    _: Annotated[Principal, Depends(require_permission("platform:write"))],
) -> dict[str, object]:
    return {"data": {"status": await refresh_a_share_research(force=True)}}


@router.get("/a-share/stock-pool/focus", tags=["research"])
async def a_share_stock_pool_focus(_: ResearchPrincipal) -> dict[str, object]:
    return {"data": {"codes": await asyncio.to_thread(read_stock_pool_focus)}}


@router.post("/a-share/stock-pool/focus", tags=["research"])
async def put_a_share_stock_pool_focus(
    request_body: StockPoolFocusRequest,
    _: Annotated[Principal, Depends(require_permission("profile.update_self"))],
) -> dict[str, object]:
    codes = sorted({code.strip() for code in request_body.codes if code.strip()})
    await asyncio.to_thread(write_stock_pool_focus, codes)
    return {"data": {"codes": codes}}


@router.post("/a-share/stock-pool/add-batch", tags=["research"])
async def add_a_share_stock_pool_batch(
    request_body: StockPoolBatchRequest,
    _: Annotated[Principal, Depends(require_permission("profile.update_self"))],
) -> dict[str, object]:
    codes = sorted({code.strip() for code in request_body.codes if code.strip()})
    count = await asyncio.to_thread(update_stock_pool_membership, add_codes=codes)
    return {"data": {"ok": True, "added": codes, "failed": [], "count": count}}


@router.delete("/a-share/stock-pool/remove", tags=["research"])
async def remove_a_share_stock_pool(
    _: Annotated[Principal, Depends(require_permission("profile.update_self"))],
    instrument_id: str = Query(...),
) -> dict[str, object]:
    count = await asyncio.to_thread(update_stock_pool_membership, remove_code=instrument_id)
    return {"data": {"ok": True, "count": count}}


@router.post("/a-share/stock-pool/sync", tags=["research"])
async def sync_a_share_stock_pool(_: ResearchPrincipal) -> dict[str, object]:
    return {"data": {"ok": True, "commit": "platform-refresh"}}


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


@router.get("/crypto/dashboard-v1", response_model=MacroDashboardResponse)
async def crypto_dashboard_v1(
    response: Response, _: ResearchPrincipal
) -> MacroDashboardResponse:
    try:
        result = await _crypto_dashboard_provider.get()
    except ResearchProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "crypto_dashboard_unavailable", "message": str(exc)},
        ) from exc
    _cache_header(response, 300)
    return result
