from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from app import research_provider_macro as macro
from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro import MacroResearchProvider

pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


class _Client:
    def __init__(self, payload: Any, **_: Any) -> None:
        self._payload = payload
        self.request: dict[str, Any] | None = None

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> _Response:
        self.request = {"url": url, **kwargs}
        return _Response(self._payload)


def _provider(monkeypatch: pytest.MonkeyPatch, payload: Any) -> MacroResearchProvider:
    monkeypatch.setattr(macro.httpx, "AsyncClient", lambda **kwargs: _Client(payload, **kwargs))
    return MacroResearchProvider(timeout_seconds=7.5, user_agent="research-test")


@pytest.mark.asyncio
async def test_macro_provider_preserves_category_probability_and_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(
        monkeypatch,
        [
            {
                "id": "rate-cut",
                "question": "Will the Fed cut interest rates?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.73", "0.27"]',
                "liquidityNum": "125000",
                "endDate": "2026-09-18T00:00:00Z",
                "slug": "fed-rate-cut",
            },
            {
                "id": "sports",
                "question": "Will a football team win?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.90", "0.10"]',
            },
        ],
    )

    events = await provider.macro_expectation_events()

    assert len(events) == 1
    event = events[0]
    assert event.event_id == "rate-cut"
    assert event.category == "monetary_policy"
    assert event.outcome == "Yes"
    assert event.current_probability_pct == Decimal("73.0")
    assert event.liquidity_label == "125000"
    assert event.source_url == "https://polymarket.com/event/fed-rate-cut"
    assert event.expiry_at is not None
    assert event.expiry_at.isoformat() == "2026-09-18T00:00:00+00:00"


@pytest.mark.asyncio
async def test_macro_provider_ignores_malformed_json_but_keeps_empty_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(
        monkeypatch,
        [
            {
                "id": "broken",
                "question": "Will CPI fall?",
                "outcomes": "not-json",
                "outcomePrices": '["0.5"]',
            }
        ],
    )

    with pytest.raises(ResearchProviderError, match="macro_expectation_events_empty"):
        await provider.macro_expectation_events()


@pytest.mark.asyncio
async def test_macro_provider_preserves_invalid_probability_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(
        monkeypatch,
        [
            {
                "id": "invalid-price",
                "question": "Will GDP rise?",
                "outcomes": ["Yes"],
                "outcomePrices": ["invalid"],
            }
        ],
    )

    with pytest.raises(ValueError):
        await provider.macro_expectation_events()
