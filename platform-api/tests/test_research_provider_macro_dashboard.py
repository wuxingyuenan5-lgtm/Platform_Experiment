from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app import research_provider_macro_dashboard as dashboard
from app.research_provider_macro_dashboard import MacroDashboardProvider

pytestmark = pytest.mark.unit


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "status": "ready",
            "asOf": "2026-09-01",
            "groups": {
                "growthProduction": [
                    {
                        "seriesId": "us_real_gdp_yoy",
                        "label": "U.S. Real GDP YoY",
                        "status": "ready",
                        "latestValue": 2.1,
                        "unit": "percent",
                        "frequency": "quarterly",
                        "timezone": "America/New_York",
                        "source": "fred",
                        "sourceSeriesId": "GDPC1",
                        "observationDate": "2026-04-01",
                        "asOf": "2026-04-01",
                        "retrievedAt": "2026-09-02T00:00:00Z",
                        "isStale": False,
                        "methodologyVersion": "fred_public_csv_v1",
                        "qualityFlags": [],
                        "observations": [{"date": "2026-04-01", "value": 2.1}],
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


def test_macro_dashboard_provider_preserves_decimal_history(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(dashboard.httpx, "AsyncClient", lambda **_kwargs: _Client())
    provider = MacroDashboardProvider(timeout_seconds=5, user_agent="test")

    contract = asyncio.run(provider.get())

    series = contract.groups["growthProduction"][0]
    assert str(series.latest_value) == "2.1"
    assert str(series.observations[0].value) == "2.1"
