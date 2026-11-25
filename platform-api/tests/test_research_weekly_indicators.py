import asyncio
import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from app import research_weekly_indicators as weekly
from app.research_weekly_catalog import COVERED, INDICATORS, REPORTS


def test_catalog_unique_and_references_cover_both_reports():
    assert len({i["id"] for i in INDICATORS}) == len(INDICATORS)
    for item in INDICATORS:
        assert 1 <= item["page"] <= REPORTS[item["report"]]["pages"]
        assert item["section"] in weekly.SECTIONS
    # Existing exact series must not be added a second time.
    covered = {s for row in COVERED for s in row.get("seriesIds", [])}
    assert covered.isdisjoint({i["id"] for i in INDICATORS})
    assert not any("snapshotValue" in i for i in INDICATORS)


def test_normalization_preserves_zero_null_decimal_and_rejects_conflicts():
    rows = weekly.normalized_points(
        [
            {"date": "2026-10-29", "value": "0"},
            {"date": "2026-10-30", "value": None},
            {"date": "2026-10-28", "value": "1.234567890123456789"},
        ]
    )
    assert rows[0]["value"] == "1.234567890123456789"
    assert rows[1]["value"] == "0" and rows[2]["value"] is None
    with pytest.raises(ValueError, match="conflicting"):
        weekly.normalized_points([rows[0], {**rows[0], "value": "2"}])
    with pytest.raises(ValueError, match="future"):
        weekly.normalized_points([{"date": "2026-11-02", "value": "1"}], today=date(2026, 11, 1))
    with pytest.raises(ValueError, match="invalid"):
        weekly.normalized_points([{"date": "2026-01-01", "value": "NaN"}])


def test_industry_identity_is_verified():
    payload = {
        "success": True,
        "result": {
            "data": [{"INDICATOR_ID": "wrong", "REPORT_DATE": "2026-10-30", "INDICATOR_VALUE": 1}]
        },
    }
    with pytest.raises(ValueError, match="identity"):
        weekly.parse_industry(payload, "EMI00107664")


def test_yoy_uses_exact_prior_year_month_and_does_not_fill():
    result = weekly.monthly_yoy(
        [
            {"date": "2024-01-01", "value": "100"},
            {"date": "2025-01-01", "value": "110"},
            {"date": "2025-02-01", "value": "112"},
        ]
    )
    assert result[0]["value"] is None
    assert Decimal(result[1]["value"]) == 10
    assert result[2]["value"] is None


def test_projection_is_lightweight_and_scales_passengers(monkeypatch):
    def local(path):
        return {
            "sources": {
                "civil_air_passengers": {
                    "status": "ready",
                    "source": "test",
                    "observations": [{"date": "2026-09-01", "value": "64300000"}],
                }
            }
        }

    monkeypatch.setattr(weekly, "local", local)
    summary = weekly.read_supplement("macro-growth", today=date(2026, 11, 4))
    assert all(not item["series"]["observations"] for item in summary["items"])
    detail = weekly.read_supplement("macro-growth", "civil_air_passengers", today=date(2026, 11, 4))
    item = next(i for i in detail["items"] if i["id"] == "civil_air_passengers")
    assert item["unit"] == "万人" and item["series"]["latestValue"] == "6430"
    assert len(item["series"]["observations"]) == 1
    with pytest.raises(ValueError):
        weekly.read_supplement("macro-fx", "civil_air_passengers")


def test_old_data_remains_stale_and_missing_is_not_zero(monkeypatch):
    monkeypatch.setattr(
        weekly,
        "local",
        lambda _: {
            "sources": {
                "bdi": {"status": "ready", "observations": [{"date": "2020-01-01", "value": "1"}]}
            }
        },
    )
    data = weekly.read_supplement("macro-growth", today=date(2026, 11, 4))
    bdi = next(i["series"] for i in data["items"] if i["id"] == "bdi")
    missing = next(i["series"] for i in data["items"] if i["id"] == "ccfi")
    assert bdi["status"] == "stale" and bdi["observationDate"] == "2020-01-01"
    assert missing["status"] == "no_data" and missing["latestValue"] is None


def test_cfets_uses_published_observation_date_and_rejects_limit_response():
    raw = {
        "data": {"message": ""},
        "records": [{"showDate": "2026-10-23", "cfetsIndexRate": "103.41"}],
    }
    assert weekly.parse_extra("cfets", json.dumps(raw).encode())[0] == {
        "date": "2026-10-23",
        "value": "103.41",
    }
    with pytest.raises(ValueError, match="source_limit"):
        weekly.parse_extra("cfets", b'{"data":{"message":"limited"},"records":[]}')


def test_refresh_failure_retains_history_and_does_not_block_other_source(monkeypatch, tmp_path):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(
        weekly, "INDICATORS", [weekly.BY_ID["bdi"], weekly.BY_ID["civil_air_passengers"]]
    )
    weekly.write_local_json(
        weekly.ARTIFACT,
        {
            "sources": {
                "bdi": {"status": "ready", "observations": [{"date": "2026-10-01", "value": "100"}]}
            }
        },
    )
    real_client = httpx.AsyncClient

    def handle(request):
        if request.url.params.get("filter", "").find("EMI00107664") >= 0:
            return httpx.Response(503)
        if request.url.host == "data.cpcadata.com":
            return httpx.Response(
                200,
                json=[
                    {"category": "整体市场", "dataList": [{"month": "9月", "2025年": [1, 2, 3, 4]}]}
                ],
            )
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {
                    "pages": 1,
                    "data": [
                        {
                            "INDICATOR_ID": "EMI00108735",
                            "REPORT_DATE": "2026-09-01",
                            "INDICATOR_VALUE": 64300000,
                        }
                    ],
                },
            },
        )

    monkeypatch.setattr(
        weekly.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle)),
    )
    statuses = asyncio.run(weekly.collect(force=True))
    assert statuses["bdi"] == "error" and statuses["civil_air_passengers"] == "ready"
    stored = weekly.local(weekly.ARTIFACT)
    assert stored["sources"]["bdi"]["observations"][0]["value"] == "100"
    assert stored["sources"]["civil_air_passengers"]["rawSha256"]
