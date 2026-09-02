from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app import research_provider_crypto_dashboard as crypto
from app.research_provider_crypto_dashboard import CryptoDashboardProvider

pytestmark = pytest.mark.unit


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "status": "ready",
            "asOf": "2026-09-02",
            "groups": {
                "binanceSpot": [
                    {
                        "seriesId": "binance_btc_spot",
                        "label": "Binance BTCUSDT Spot",
                        "status": "ready",
                        "latestValue": 77439,
                        "unit": "price",
                        "frequency": "daily",
                        "timezone": "UTC",
                        "source": "binance_public_api",
                        "isStale": False,
                        "methodologyVersion": "binance_spot_daily_close_v1",
                        "qualityFlags": ["venue_binance", "mode_venue_not_aggregate"],
                        "observations": [{"date": "2026-09-01", "value": 77439}],
                    }
                ]
            },
        }


class _Client:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        return _Response()


def test_crypto_dashboard_provider_preserves_decimal(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(crypto.httpx, "AsyncClient", lambda **_kwargs: _Client())
    provider = CryptoDashboardProvider(timeout_seconds=5, user_agent="test")
    contract = asyncio.run(provider.get())
    assert str(contract.groups["binanceSpot"][0].latest_value) == "77439"
