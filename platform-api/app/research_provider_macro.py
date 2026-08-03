from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

import httpx

from app.research_data_schemas import MacroExpectationEvent
from app.research_provider_errors import ResearchProviderError

POLYMARKET_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
MacroCategory = Literal["monetary_policy", "macro", "geopolitics", "election"]


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

        events: list[MacroExpectationEvent] = []
        for row in rows if isinstance(rows, list) else []:
            event = self._event_from_row(row)
            if event is not None:
                events.append(event)
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

        outcomes_raw = row.get("outcomes") or "[]"
        prices_raw = row.get("outcomePrices") or "[]"
        try:
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        except json.JSONDecodeError:
            return None
        if not outcomes or not prices:
            return None

        best_index = max(
            range(min(len(outcomes), len(prices))),
            key=lambda index: float(prices[index]),
        )
        probability = Decimal(str(float(prices[best_index]) * 100))
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


def _category_for_title(title: str) -> MacroCategory | None:
    lowered = title.lower()
    keywords: dict[MacroCategory, tuple[str, ...]] = {
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


def _expiry_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
