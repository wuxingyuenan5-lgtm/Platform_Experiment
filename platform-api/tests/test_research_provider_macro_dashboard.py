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
    monkeypatch.setattr(dashboard, "read_local_json", lambda _path: _Response().json())
    provider = MacroDashboardProvider(timeout_seconds=5, user_agent="test")

    contract = asyncio.run(provider.get())

    series = contract.groups["growthProduction"][0]
    assert str(series.latest_value) == "2.1"
    assert str(series.observations[0].value) == "2.1"


def test_reader_rechecks_age_without_marking_current_quarter_stale():
    from datetime import UTC, datetime

    contract = dashboard.MacroDashboardResponse.model_validate(_Response().json())
    quarterly = contract.groups["growthProduction"][0]
    daily = quarterly.model_copy(deep=True, update={"frequency": "daily_business_day"})
    missing = daily.model_copy(deep=True, update={"status": "no_data", "latest_value": None})
    contract.groups["daily"] = [daily, missing]
    contract.apply_freshness(datetime(2026, 9, 2, tzinfo=UTC))
    assert quarterly.status == "ready"
    assert daily.status == "stale" and daily.is_stale
    assert missing.status == "no_data" and missing.latest_value is None
    assert contract.status == "partial"
    contract.apply_freshness(datetime(2027, 9, 2, tzinfo=UTC))
    assert quarterly.status == "stale"
    assert daily.quality_flags.count("stale_latest_observation") == 1


def test_valid_but_stopped_producer_is_not_ready(monkeypatch):
    document = _Response().json()
    series = document["groups"]["growthProduction"][0]
    series.update(frequency="daily_business_day", observationDate="2020-01-01")
    monkeypatch.setattr(dashboard, "read_local_json", lambda _: document)
    result = asyncio.run(MacroDashboardProvider(timeout_seconds=1, user_agent="test").get())
    assert result.groups["growthProduction"][0].status == "stale"
