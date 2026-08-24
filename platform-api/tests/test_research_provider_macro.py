from __future__ import annotations

import asyncio
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

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def get(self, _url: str, **_kwargs: Any) -> _Response:
        return _Response(self._payload)


def _provider(monkeypatch: pytest.MonkeyPatch, payload: Any) -> MacroResearchProvider:
    monkeypatch.setattr(
        macro.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(payload, **kwargs),
    )
    return MacroResearchProvider(timeout_seconds=7.5, user_agent="research-test")


def test_macro_provider_reads_platform_data_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(
        monkeypatch,
        {
            "schemaVersion": "1.0",
            "status": "ready",
            "source": "Polymarket whitelist; CME FedWatch API not_configured",
            "updatedAt": "2026-08-24T06:18:00Z",
            "events": [
                {
                    "id": "us-recession-by-end-2026",
                    "label": "US recession by end of 2026?",
                    "category": "macro",
                    "probability": 8,
                    "history": [
                        {
                            "observedAt": "2026-08-24T06:01:00Z",
                            "probability": 8,
                        }
                    ],
                }
            ],
        },
    )

    contract = asyncio.run(provider.macro_expectation_contract())

    assert contract.status == "ready"
    assert contract.events[0].id == "us-recession-by-end-2026"
    assert contract.events[0].probability == 8.0
    assert contract.events[0].history[0].probability == 8.0


def test_macro_provider_rejects_ready_empty_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(
        monkeypatch,
        {
            "schemaVersion": "1.0",
            "status": "ready",
            "source": "platform-data",
            "updatedAt": "2026-08-24T06:18:00Z",
            "events": [],
        },
    )

    with pytest.raises(
        ResearchProviderError,
        match="macro_expectation_feed_ready_without_events",
    ):
        asyncio.run(provider.macro_expectation_contract())


def test_macro_provider_accepts_not_configured_without_fake_probability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(
        monkeypatch,
        {
            "schemaVersion": "1.0",
            "status": "not_configured",
            "source": "CME FedWatch API",
            "updatedAt": "2026-08-24T06:18:00Z",
            "events": [],
        },
    )

    contract = asyncio.run(provider.macro_expectation_contract())

    assert contract.status == "not_configured"
    assert contract.events == []


def test_legacy_adapter_uses_only_configured_feed_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(
        monkeypatch,
        {
            "schemaVersion": "1.0",
            "status": "ready",
            "source": "platform-data",
            "updatedAt": "2026-08-24T06:18:00Z",
            "events": [
                {
                    "id": "negative-gdp-growth-2026",
                    "label": "Negative GDP growth in 2026?",
                    "category": "macro",
                    "probability": 4,
                    "history": [
                        {
                            "observedAt": "2026-08-24T04:48:00Z",
                            "probability": 4,
                        }
                    ],
                }
            ],
        },
    )

    events = asyncio.run(provider.macro_expectation_events())

    assert len(events) == 1
    assert events[0].event_id == "negative-gdp-growth-2026"
    assert events[0].current_probability_pct == Decimal("4")
