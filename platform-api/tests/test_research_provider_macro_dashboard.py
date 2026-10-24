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


def test_expired_curve_history_does_not_mark_current_dashboard_stale():
    from datetime import UTC, datetime

    contract = dashboard.MacroDashboardResponse.model_validate(_Response().json())
    current = contract.groups['growthProduction'][0]
    archived = current.model_copy(deep=True, update={
        'frequency': 'exchange_trading_day', 'status': 'stale', 'is_stale': True,
        'observation_date': '2020-01-01',
    })
    contract.groups['shfeGoldCurveHistory'] = [archived]
    contract.apply_freshness(datetime(2026, 9, 2, tzinfo=UTC))
    assert contract.status == 'ready'
    current.frequency = 'exchange_trading_day'
    contract.apply_freshness(datetime(2026, 9, 2, tzinfo=UTC))
    assert current.status == 'stale'
    assert contract.status == 'partial'


def test_valid_but_stopped_producer_is_not_ready(monkeypatch):
    document = _Response().json()
    series = document["groups"]["growthProduction"][0]
    series.update(frequency="daily_business_day", observationDate="2020-01-01")
    monkeypatch.setattr(dashboard, "read_local_json", lambda _: document)
    result = asyncio.run(MacroDashboardProvider(timeout_seconds=1, user_agent="test").get())
    assert result.groups["growthProduction"][0].status == "stale"


def test_corporate_yields_read_local_artifact_with_decimal_and_missing_values(tmp_path, monkeypatch):
    import json

    document = _Response().json()
    template = document["groups"]["growthProduction"][0]
    document["groups"] = {"corporateYields": [
        {**template, "seriesId": identity, "sourceSeriesId": source,
         "frequency": "daily", "unit": "percent", "latestValue": "5.65",
         "observations": [{"date": "2026-05-31", "value": "5.6500"},
                          {"date": "2026-06-01", "value": None}]}
        for identity, source in [
            ("us_aaa_corporate_yield", "BAMLC0A1CAAAEY"),
            ("us_bbb_corporate_yield", "BAMLC0A4CBBBEY"),
            ("us_ccc_lower_corporate_yield", "BAMLH0A3HYCEY"),
        ]
    ]}
    path = tmp_path / "public/v1/macro/dashboard.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    contract = asyncio.run(MacroDashboardProvider(timeout_seconds=1, user_agent="test").get())
    rows = contract.groups["corporateYields"]
    assert len(rows) == 3
    assert rows[2].source_series_id == "BAMLH0A3HYCEY"
    assert str(rows[0].observations[0].value) == "5.6500"
    assert rows[0].observations[1].value is None
    assert rows[0].status == "stale"
