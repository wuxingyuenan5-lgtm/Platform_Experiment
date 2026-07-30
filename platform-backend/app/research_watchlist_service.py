from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from pydantic import ValidationError

from app.database import connection
from app.research_watchlist_repository import (
    ResearchWatchlistConcurrentUpdateError,
    ResearchWatchlistRecord,
    get_research_watchlist as get_research_watchlist_record,
    replace_research_watchlist as replace_research_watchlist_record,
)
from app.research_watchlist_schemas import (
    ReplaceResearchWatchlistRequest,
    ResearchWatchlistItem,
    ResearchWatchlistResponse,
)

_STOCK_CODE_PATTERN = re.compile(
    r"^(?:(?:SH|SZ|BJ)[.:-]?)?(\d{6})(?:[.:-]?(?:SH|SZ|BJ))?$",
    re.IGNORECASE,
)


class ResearchWatchlistServiceError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_stock_code(value: str) -> str:
    compact = re.sub(r"\s+", "", value.strip().upper())
    match = _STOCK_CODE_PATTERN.fullmatch(compact)
    return match.group(1) if match else ""


def _normalize_items(items: list[ResearchWatchlistItem]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        code = normalize_stock_code(item.code)
        if not code:
            raise ResearchWatchlistServiceError(
                422,
                "invalid_stock_code",
                f"Invalid A-share stock code: {item.code}",
            )
        if code in seen:
            raise ResearchWatchlistServiceError(
                422,
                "duplicate_stock_code",
                f"Duplicate A-share stock code: {code}",
            )
        seen.add(code)
        name = item.name.strip() or code
        group = item.group.strip() or "默认分组"
        normalized.append({"code": code, "name": name, "group": group})
    return normalized


def _response_from_record(record: ResearchWatchlistRecord | None) -> ResearchWatchlistResponse:
    if record is None:
        return ResearchWatchlistResponse(items=[], rowVersion=0, updatedAt=None)
    try:
        payload = json.loads(record.items_json)
    except json.JSONDecodeError as exc:
        raise ResearchWatchlistServiceError(
            503,
            "watchlist_payload_invalid",
            "Stored research watchlist payload is invalid",
        ) from exc
    if not isinstance(payload, list):
        raise ResearchWatchlistServiceError(
            503,
            "watchlist_payload_invalid",
            "Stored research watchlist payload is invalid",
        )
    try:
        items = [ResearchWatchlistItem.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ResearchWatchlistServiceError(
            503,
            "watchlist_payload_invalid",
            "Stored research watchlist payload is invalid",
        ) from exc
    return ResearchWatchlistResponse(
        items=items,
        rowVersion=record.row_version,
        updatedAt=datetime.fromisoformat(record.updated_at),
    )


def get_research_watchlist(user_id: str) -> ResearchWatchlistResponse:
    with connection() as db:
        record = get_research_watchlist_record(db, user_id=user_id)
    return _response_from_record(record)


def replace_research_watchlist(
    *,
    user_id: str,
    request: ReplaceResearchWatchlistRequest,
) -> ResearchWatchlistResponse:
    items = _normalize_items(request.items)
    try:
        with connection() as db:
            db.execute("BEGIN IMMEDIATE")
            record = replace_research_watchlist_record(
                db,
                user_id=user_id,
                items=items,
                expected_version=request.expected_version,
                now=utc_now_iso(),
            )
    except ResearchWatchlistConcurrentUpdateError as exc:
        raise ResearchWatchlistServiceError(
            409,
            "watchlist_version_conflict",
            "Research watchlist changed in another session",
        ) from exc
    return _response_from_record(record)


__all__ = [
    "ResearchWatchlistServiceError",
    "get_research_watchlist",
    "normalize_stock_code",
    "replace_research_watchlist",
]
