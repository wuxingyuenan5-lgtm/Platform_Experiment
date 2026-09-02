from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app import research_provider_market_detail as market_detail
from app.research_provider_errors import ResearchProviderError
from app.research_provider_market_detail import MarketDetailProvider

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


def _payload() -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "marketId": "macro",
        "status": "ready",
        "asOf": "2026-08-31",
        "retrievedAt": "2026-09-01T06:37:19Z",
        "rows": [
            {
                "id": "macro-us10y",
                "name": "美国 10Y",
                "symbol": "US10Y",
                "status": "ready",
                "unit": "percent",
                "changeUnit": "basis_points",
                "frequency": "daily_business_day",
                "timezone": "America/New_York",
                "observationDate": "2026-08-31",
                "asOf": "2026-08-31",
                "source": "us_treasury",
                "methodologyVersion": "market_detail_windows_v1",
                "qualityFlags": ["insufficient_52w_history"],
                "close": 4.75,
                "change1d": 2,
                "change1w": 5,
                "change1m": 0,
                "changeQtd": 31,
                "changeYtd": None,
                "change1y": None,
                "high52w": None,
                "distance52wHigh": None,
                "spark30d": [4.7, 4.75],
            }
        ],
    }


def test_provider_preserves_decimal_and_unavailable_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(market_detail, "read_local_json", lambda _path: _payload())
    provider = MarketDetailProvider(timeout_seconds=5, user_agent="test")

    contract = asyncio.run(provider.get("macro"))

    assert str(contract.rows[0].close) == "4.75"
    assert str(contract.rows[0].change_1d) == "2"
    assert contract.rows[0].change_ytd is None


def test_provider_does_not_enable_deferred_market():
    provider = MarketDetailProvider(timeout_seconds=5, user_agent="test")

    with pytest.raises(ResearchProviderError, match="market_detail_not_enabled"):
        asyncio.run(provider.get("us"))
