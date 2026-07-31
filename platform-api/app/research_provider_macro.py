from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.research_data_schemas import MacroExpectationEvent
from app.research_provider_errors import ResearchProviderError

POLYMARKET_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


class MacroResearchProvider:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent

    async def macro_expectation_events(self, limit: int = 12) -> list[MacroExpectationEvent]:
        params = {"active": "true", "closed": "false", "limit": 200}
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                POLYMARKET_MARKETS_URL,
                params=params,
                headers={"User-Agent": self._user_agent},
            )
            response.raise_for_status()
            rows = response.json()

        events = [event for row in rows if (event := self._event_from_row(row)) is not None]
        events.sort(key=lambda item: (item.category, -item.current_probability_pct))
        if not events:
            raise ResearchProviderError("macro_expectation_events_empty")
        return events[:limit]

    @staticmethod
    def _event_from_row(row: dict[str, Any]) -> MacroExpectationEvent | None:
        title = str(row.get("question") or row.get("title") or "").strip()
        category = _category_for_title(title)
        if category is None:
            return None

        outcomes = _decode_list(row.get("outcomes") or "[]")
        prices = _decode_list(row.get("outcomePrices") or "[]")
        choice_count = min(len(outcomes), len(prices))
        if choice_count == 0:
            return None
        try:
            best_index = max(range(choice_count), key=lambda index: float(prices[index]))
            probability = Decimal(str(float(prices[best_index]) * 100))
        except (TypeError, ValueError):
            return None

        return MacroExpectationEvent(
            event_id=str(row.get("id") or row.get("conditionId") or title),
            category=category,
            title=title,
            outcome=str(outcomes[best_index]),
            current_probability_pct=probability,
            liquidity_label=str(row.get("liquidityNum") or row.get("liquidity") or "") or None,
            expiry_at=_expiry_at(row.get("endDate") or row.get("end_date_iso")),
            source_url=(
                f"https://polymarket.com/event/{row.get('slug')}" if row.get("slug") else None
            ),
        )


def _category_for_title(title: str) -> str | None:
    lowered = title.lower()
    keywords = {
        "monetary_policy": ("fed", "interest rate", "rate cut", "fomc"),
        "macro": ("inflation", "cpi", "recession", "unemployment", "gdp"),
        "geopolitics": ("war", "ceasefire", "iran", "ukraine", "taiwan"),
        "election": ("election", "president", "senate", "congress"),
    }
    return next(
        (
            category
            for category, terms in keywords.items()
            if any(term in lowered for term in terms)
        ),
        None,
    )


def _decode_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        result = json.loads(value)
    except json.JSONDecodeError:
        return []
    return result if isinstance(result, list) else []


def _expiry_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
