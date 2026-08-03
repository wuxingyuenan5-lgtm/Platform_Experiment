from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Principal, require_permission
from app.config import get_settings
from app.research_watchlist_schemas import (
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
