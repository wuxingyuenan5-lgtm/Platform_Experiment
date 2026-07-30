from __future__ import annotations

from app.database import connection
from app.research_watchlist_repository import (
    ConcurrentWatchlistUpdateError,
    WatchlistItemRecord,
    WatchlistRecord,
    get_watchlist,
    replace_watchlist,
)
from app.research_watchlist_schemas import (
    ReplaceResearchWatchlistRequest,
    ResearchWatchlistItem,
    ResearchWatchlistResponse,
)

A_SHARE_MARKET = "a_share"


class ResearchWatchlistServiceError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def _response(record: WatchlistRecord) -> ResearchWatchlistResponse:
    return ResearchWatchlistResponse(
        market="a_share",
        version=record.version,
        updatedAt=record.updated_at,
        items=[
            ResearchWatchlistItem(
                securityCode=item.security_code,
                securityName=item.security_name,
                group=item.group,
            )
            for item in record.items
        ],
    )


def get_user_a_share_watchlist(user_id: str) -> ResearchWatchlistResponse:
    with connection() as db:
        return _response(get_watchlist(db, user_id=user_id, market=A_SHARE_MARKET))


def replace_user_a_share_watchlist(
    user_id: str,
    request: ReplaceResearchWatchlistRequest,
) -> ResearchWatchlistResponse:
    records = tuple(
        WatchlistItemRecord(
            security_code=item.security_code,
            security_name=item.security_name.strip(),
            group=item.group.strip(),
        )
        for item in request.items
    )
    try:
        with connection() as db:
            stored = replace_watchlist(
                db,
                user_id=user_id,
                market=A_SHARE_MARKET,
                expected_version=request.expected_version,
                items=records,
            )
    except ConcurrentWatchlistUpdateError as exc:
        raise ResearchWatchlistServiceError(
            409,
            "watchlist_version_conflict",
            "自选股已在其他页面或设备更新，请刷新后重试",
        ) from exc
    return _response(stored)
