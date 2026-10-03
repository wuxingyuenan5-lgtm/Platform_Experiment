from __future__ import annotations

from typing import Annotated, Literal, NoReturn

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Principal, require_permission
from app.config import get_settings
from app.research_market_layout_repository import read_layout, replace_layout
from app.research_watchlist_repository import ResearchWatchlistConcurrentUpdateError
from app.research_watchlist_schemas import (
    MarketLayoutResponse,
    ReplaceMarketLayoutRequest,
    ReplaceResearchWatchlistRequest,
    ResearchWatchlistResponse,
)
from app.research_watchlist_service import (
    ResearchWatchlistServiceError,
    get_research_watchlist,
    replace_research_watchlist,
)

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix)


def _raise_service_error(exc: ResearchWatchlistServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


@router.get(
    "/me/research-watchlist",
    response_model=ResearchWatchlistResponse,
    tags=["personal-research"],
)
def self_research_watchlist(
    principal: Annotated[Principal, Depends(require_permission("profile.read_self"))],
) -> ResearchWatchlistResponse:
    try:
        return get_research_watchlist(principal.user_id)
    except ResearchWatchlistServiceError as exc:
        _raise_service_error(exc)


@router.put(
    "/me/research-watchlist",
    response_model=ResearchWatchlistResponse,
    tags=["personal-research"],
)
def put_self_research_watchlist(
    request_body: ReplaceResearchWatchlistRequest,
    principal: Annotated[Principal, Depends(require_permission("profile.update_self"))],
) -> ResearchWatchlistResponse:
    try:
        return replace_research_watchlist(user_id=principal.user_id, request=request_body)
    except ResearchWatchlistServiceError as exc:
        _raise_service_error(exc)


__all__ = ["router"]

MarketId = Literal["macro", "gold", "crypto", "us", "global", "aShare"]


@router.get("/me/research-market-layout/{market_id}", response_model=MarketLayoutResponse)
def self_market_layout(
    market_id: MarketId,
    principal: Annotated[Principal, Depends(require_permission("profile.read_self"))],
) -> dict:
    return read_layout(principal.user_id, market_id)


@router.put("/me/research-market-layout/{market_id}", response_model=MarketLayoutResponse)
def put_self_market_layout(
    market_id: MarketId,
    request_body: ReplaceMarketLayoutRequest,
    principal: Annotated[Principal, Depends(require_permission("profile.update_self"))],
) -> dict:
    try:
        return replace_layout(
            principal.user_id,
            market_id,
            [group.model_dump(by_alias=True) for group in request_body.groups]
            if request_body.groups is not None
            else None,
            request_body.expected_version,
        )
    except ResearchWatchlistConcurrentUpdateError as exc:
        raise HTTPException(
            409,
            detail={
                "code": "market_layout_version_conflict",
                "message": "标的列表已更新，请重新检查",
            },
        ) from exc
