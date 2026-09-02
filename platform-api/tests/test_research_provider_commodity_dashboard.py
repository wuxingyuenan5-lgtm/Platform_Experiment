from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app import research_provider_commodity_dashboard as commodity
from app.research_provider_commodity_dashboard import CommodityDashboardProvider

pytestmark = pytest.mark.unit


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "status": "ready",
            "asOf": "2026-08-25",
            "groups": {
                "cftcGoldNet": [
                    {
                        "seriesId": "cftc_gold_managed_money_net",
                        "label": "CFTC Gold Managed Money Net",
                        "status": "ready",
                        "latestValue": 125,
                        "unit": "contracts",
                        "frequency": "weekly",
                        "timezone": "America/New_York",
                        "source": "cftc_pre",
                        "isStale": False,
                        "methodologyVersion": "cftc_disaggregated_futures_only_v1",
                        "qualityFlags": [],
                        "observations": [{"date": "2026-08-25", "value": 125}],
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


def test_commodity_dashboard_provider_preserves_decimal(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(commodity.httpx, "AsyncClient", lambda **_kwargs: _Client())
    provider = CommodityDashboardProvider(timeout_seconds=5, user_agent="test")
    contract = asyncio.run(provider.get())
    assert str(contract.groups["cftcGoldNet"][0].latest_value) == "125"
