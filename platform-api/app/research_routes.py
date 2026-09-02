from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.auth import Principal, require_permission
from app.config import get_settings
from app.research_data_schemas import (
    AShareDashboardResponse,
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
    DEFAULT_THRESHOLD_YUAN,
    ResearchServiceError,
    get_a_share_dashboard,
    get_stock_snapshot,
)

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
    threshold_yuan: Decimal = Query(
        default=DEFAULT_THRESHOLD_YUAN,
        alias="thresholdYuan",
        gt=0,
    ),
) -> AShareDashboardResponse:
    try:
        result = await get_a_share_dashboard(threshold_yuan=threshold_yuan)
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
