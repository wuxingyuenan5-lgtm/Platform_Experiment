"""Account-owned display configuration, never shared research facts or arbitrary SQL."""

import json
from datetime import UTC, date, datetime
from typing import Annotated, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth import Principal, require_permission
from app.config import get_settings
from app.database_connection import connection

router = APIRouter(prefix=get_settings().api_prefix + "/me/workspace", tags=["personal-workspace"])
Reader = Annotated[Principal, Depends(require_permission("profile.read_self"))]
Writer = Annotated[Principal, Depends(require_permission("profile.update_self"))]


def module_permission(path: str) -> str:
    root = path.split("/", 2)[1] if path.startswith("/") else ""
    permissions = {
        "hedge-board": "research.read",
        "strategy": "strategy.read",
        "risk": "risk.read",
        "financial-ai": "financial_ai.read",
        "finance": "finance.read",
        "data": "data.read",
        "monitor": "monitor.read",
        "reports": "reports.read",
        "news": "news.read",
        "news-calendar": "news.read",
        "account": "profile.read_self",
        "settings": "settings.read",
        "user": "user.read",
        "users": "user.read",
        "audit": "audit:read",
        "notification": "platform:read",
    }
    if root not in permissions or ".." in path or "\\" in path or len(path) > 240:
        raise HTTPException(422, "Unsupported module")
    plain = path.split("?", 1)[0]
    if plain == "/risk/users":
        return "user.read"
    if plain == "/risk/profile":
        return "profile.read_self"
    return permissions[root]


class Card(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    type: Literal["module", "chart"]
    title: str = Field(min_length=1, max_length=100)
    width: Literal[1, 2] = 1
    path: str = ""
    seriesA: str = Field(default="", max_length=100)
    seriesB: str = Field(default="", max_length=100)
    transform: Literal["level", "index", "return"] = "level"
    display: Literal["chart", "table"] = "chart"
    start: date | None = None
    end: date | None = None


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    date: date
    precision: Literal["day", "around", "month"] = "day"
    title: str = Field(min_length=1, max_length=160)
    criterion: str = Field(default="", max_length=1800)
    outcome: str = Field(default="", max_length=1800)
    sourceUrl: str = Field(default="", max_length=1000)
    status: Literal["watching", "confirmed", "cancelled"] = "watching"

    @field_validator("sourceUrl")
    @classmethod
    def safe_url(cls, value):
        if value and (
            urlparse(value).scheme not in {"https", "http"} or not urlparse(value).netloc
        ):
            raise ValueError("Source must be an HTTP(S) URL")
        return value


class Document(BaseModel):
    expectedVersion: int = Field(ge=0)
    cards: list[Card] = Field(default_factory=list, max_length=24)
    events: list[Event] = Field(default_factory=list, max_length=300)


def visible_card(card, principal):
    permission = module_permission(card["path"]) if card["type"] == "module" else "research.read"
    return principal.has_permission(permission)


def read_document(user_id, kind):
    with connection() as db:
        row = db.execute(
            "SELECT payload_json,row_version FROM user_workspace_documents "
            "WHERE user_id=? AND kind=?",
            (user_id, kind),
        ).fetchone()
    return {
        "items": json.loads(row["payload_json"]) if row else [],
        "rowVersion": row["row_version"] if row else 0,
    }


def save_document(user_id, kind, items, expected_version):
    if len({x["id"] for x in items}) != len(items):
        raise HTTPException(422, "Duplicate IDs")
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT row_version FROM user_workspace_documents WHERE user_id=? AND kind=?",
            (user_id, kind),
        ).fetchone()
        version = row[0] if row else 0
        if version != expected_version:
            raise HTTPException(409, "内容已在另一页面更新，请重新载入后保存")
        db.execute(
            "INSERT INTO user_workspace_documents VALUES (?,?,?,?,?) "
            "ON CONFLICT(user_id,kind) DO UPDATE SET payload_json=excluded.payload_json,"
            "row_version=excluded.row_version,updated_at=excluded.updated_at",
            (
                user_id,
                kind,
                json.dumps(items, ensure_ascii=False),
                version + 1,
                datetime.now(UTC).isoformat(),
            ),
        )
    return {"items": items, "rowVersion": version + 1}


@router.get("/{kind}")
def get_workspace(kind: Literal["cards", "events"], principal: Reader):
    result = read_document(principal.user_id, kind)
    if kind == "cards":
        result["items"] = [c for c in result["items"] if visible_card(c, principal)]
    return result


@router.put("/{kind}")
def put_workspace(kind: Literal["cards", "events"], body: Document, principal: Writer):
    items = [x.model_dump(mode="json") for x in (body.cards if kind == "cards" else body.events)]
    if kind == "cards":
        from app.research_chart_catalog import series_catalog

        allowed_series = {s["id"] for s in series_catalog()}
        for card in items:
            if not visible_card(card, principal):
                raise HTTPException(403, "Module not permitted")
            if card["type"] == "chart" and (
                card["seriesA"] not in allowed_series
                or (card["seriesB"] and card["seriesB"] not in allowed_series)
            ):
                raise HTTPException(422, "Unknown series")
            if card["start"] and card["end"] and card["start"] > card["end"]:
                raise HTTPException(422, "Invalid date range")
        # Permission loss hides a card without destroying the owner's saved layout.
        previous = read_document(principal.user_id, kind)
        items += [
            c
            for c in previous["items"]
            if not visible_card(c, principal) and c["id"] not in {x["id"] for x in items}
        ]
    result = save_document(principal.user_id, kind, items, body.expectedVersion)
    if kind == "cards":
        result["items"] = [c for c in result["items"] if visible_card(c, principal)]
    return result
