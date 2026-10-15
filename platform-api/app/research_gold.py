"""Read-only gold research artifacts and bounded analyst pagination."""
from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
import json

from app.research_local_data import hedge_board_data_root
from app.research_provider_errors import ResearchProviderError


@lru_cache(maxsize=6)
def _load(path: str, modified: int):
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schemaVersion") != "1.0":
        raise ResearchProviderError("gold_research_schema_mismatch")
    return payload


def read_gold(name: str):
    if name not in ("gold-positioning", "gold-report", "analyst-views"):
        raise ResearchProviderError("unknown_gold_artifact")
    try:
        path = hedge_board_data_root() / "public/v1/commodity" / f"{name}.json"
        payload = _load(str(path), path.stat().st_mtime_ns)
        result = dict(payload)
        retrieved = payload.get("retrievedAt")
        if retrieved and (datetime.now(UTC)-datetime.fromisoformat(retrieved.replace("Z", "+00:00"))).total_seconds() > 36*3600:
            result["status"] = "stale"
        return result
    except (OSError, ValueError, TypeError) as exc:
        raise ResearchProviderError("gold_research_unavailable") from exc


def analyst_page(*, author="", stance="", query="", page=1, page_size=12):
    payload = read_gold("analyst-views")
    if payload.get("status") == "unavailable":
        raise ResearchProviderError("analyst_views_unavailable")
    terms = query.casefold().split()
    rows = []
    for article in payload.get("articles", []):
        if author and article.get("analystId") != author:
            continue
        views = article.get("views", [])
        if stance and not any(view.get("stance") == stance for view in views):
            if not (stance == "unspecified" and not views):
                continue
        text = " ".join(str(article.get(key) or "") for key in ("title", "headlineChinese", "summary")) + " " + " ".join(str(v.get("assetName", "")) for v in views)
        if any(term not in text.casefold() for term in terms):
            continue
        rows.append(article)
    return {**payload, "analysts": payload.get("analysts", []), "articles": rows[(page-1)*page_size:page*page_size], "total": len(rows), "page": page, "pageSize": page_size}
