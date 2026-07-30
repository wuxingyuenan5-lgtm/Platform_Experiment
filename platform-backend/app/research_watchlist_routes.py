from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import Principal, require_permission
from app.config import get_settings
from app.research_watchlist_schemas import (
    ReplaceResearchWatchlistRequest,
    ResearchWatchlistResponse,
)
from app.research_watchlist_service import (
    ResearchWatchlistServiceError,
    get_user_a_share_watchlist,
    replace_user_a_share_watchlist,
)

settings = get_settings()
router = APIRouter(prefix=f"{settings.api_prefix}/me/research", tags=["research-watchlist"])
WatchlistReadPrincipal = Annotated[
    Principal,
    Depends(require_permission("profile.read_self")),
]
WatchlistWritePrincipal = Annotated[
    Principal,
    Depends(require_permission("profile.update_self")),
]


def _raise_service_error(exc: ResearchWatchlistServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/a-share/watchlist", response_model=ResearchWatchlistResponse)
def a_share_watchlist(
    response: Response,
    principal: WatchlistReadPrincipal,
) -> ResearchWatchlistResponse:
    _no_store(response)
    return get_user_a_share_watchlist(principal.user_id)


@router.put("/a-share/watchlist", response_model=ResearchWatchlistResponse)
def put_a_share_watchlist(
    request_body: ReplaceResearchWatchlistRequest,
    response: Response,
    principal: WatchlistWritePrincipal,
) -> ResearchWatchlistResponse:
    try:
        result = replace_user_a_share_watchlist(principal.user_id, request_body)
    except ResearchWatchlistServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result
