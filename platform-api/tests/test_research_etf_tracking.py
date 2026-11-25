from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from app import research_etf_tracking as etf


def test_single_projection_keeps_primary_charts_and_skips_removed_group_reads(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    members = [
        {"code": code, "name": code, "display_group": "宽基/沪深300", "dashboard_eligible": True}
        for code in ["510310", "510300"]
    ]
    etf.write("universe", {"data": members})
    for member in members:
        etf.write(
            "etfs/" + member["code"],
            {
                "status": "ready",
                "data": {
                    "series": [
                        {"date": "2026-11-03", "etf_qfq_close": "4.123", "qfq_total_units_yi": "8"}
                    ],
                    "disclosures": [],
                },
            },
        )
    full = etf.detail("510310")
    original = etf.read
    reads = []

    def read(name):
        reads.append(name)
        return original(name)

    monkeypatch.setattr(etf, "read", read)
    single = etf.detail("510310", include_group=False)
    assert "etfs/510300" not in reads
    assert single["members"] == [] and single["group"] == []
    for key in ["meta", "series", "disclosures", "margin", "groupMargin", "groupLabel"]:
        assert single[key] == full[key]
    assert full["members"]


def test_flow_decimal_null_and_close_basis():
    rows = etf.enriched(
        {
            "series": [
                {"date": "2026-01-01", "etf_qfq_close": "4.12", "qfq_delta_units_yi": "0.1"},
                {
                    "date": "2026-01-02",
                    "etf_qfq_close": "4.2",
                    "etf_qfq_avg_price_est": "4.15",
                    "qfq_delta_units_yi": "-0.25",
                },
                {"date": "2026-01-03", "etf_qfq_close": "4.2", "qfq_delta_units_yi": None},
            ]
        },
        [{"date": "2026-01-02", "turnover_yi": "100"}],
    )
    assert rows[0]["flow_yi"] == "0.412" and rows[0]["flow_price_basis"] == "close"
    assert rows[1]["flow_yi"] == "-1.0375"
    assert Decimal(rows[1]["flow_to_index_pct"]) == Decimal("-1.0375")
    assert rows[2]["flow_yi"] is None and rows[0]["flow_to_index_pct"] is None


def test_percentile_has_no_future_leakage():
    rows = [
        {
            "date": (date(2025, 1, 1) + timedelta(days=i)).isoformat(),
            "etf_qfq_turnover_est_yi": i + 1,
        }
        for i in range(61)
    ]
    past = etf.enriched({"series": rows[:60]})
    all_rows = etf.enriched({"series": rows})
    assert past == all_rows[:60]
    assert past[58]["etf_qfq_turnover_est_yi_percentile"] is None
    assert Decimal(past[59]["etf_qfq_turnover_est_yi_percentile"]) == 100


def test_html_200_does_not_replace_good_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    old = {
        "data": {"meta": {"code": "510310"}, "series": [{"date": "2026-01-01"}]},
        "fetchedAt": "before",
    }
    etf.write("etfs/510310", old)
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html>fallback</html>"))
    ) as client:
        result = etf.fetch(client, "etfs/510310")
    assert result["status"] == "stale" and result["data"] == old["data"]
    assert result["fetchedAt"] == "before"


def test_identity_dates_and_schema_are_validated():
    with pytest.raises(ValueError):
        etf.validate(
            "etfs/510310", {"meta": {"code": "510300"}, "series": [{"date": "2026-01-01"}]}
        )
    with pytest.raises(ValueError):
        etf.validate("margin/hs300", {"meta": {}, "rows": [{"date": "2026-01-01"}] * 2})
    with pytest.raises(ValueError):
        etf.validate("universe", [{"code": "../bad"}])


def test_regressed_source_keeps_latest(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    old_data = {"meta": {"code": "510310"}, "series": [{"date": "2026-10-19"}]}
    etf.write("etfs/510310", {"data": old_data, "fetchedAt": "before"})
    payload = {"meta": {"code": "510310"}, "series": [{"date": "2026-10-16"}]}
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        result = etf.fetch(client, "etfs/510310")
    assert result["status"] == "stale" and result["data"] == old_data


def test_partial_group_is_not_silently_summed(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    etf.write(
        "universe",
        {
            "data": [
                {"code": c, "display_group": "test", "dashboard_eligible": True}
                for c in ("510310", "510300")
            ]
        },
    )
    etf.write(
        "etfs/510310", {"data": {"series": [{"date": "2026-01-01", "qfq_total_units_yi": "10"}]}}
    )
    group = etf.detail("510310")["group"][0]
    assert group["qfq_total_units_yi"] is None
    assert group["qfq_total_units_yi_covered"] == 1 and group["expected"] == 2


def test_routes_auth_validation_and_no_network(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.auth import Principal, require_principal
    from app.research_routes import router

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(
        etf, "fetch", lambda *_a, **_k: pytest.fail("GET read model attempted network")
    )
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/v1/research/a-share/etf-tracking"
    assert client.get(url).status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    response = client.get(url)
    assert response.status_code == 200 and response.json()["items"] == []
    assert response.headers["cache-control"] == "no-store"
    assert client.get(url + "/invalid").status_code == 422
    assert client.get(url + "/510310").status_code == 404
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get(url).status_code == 403


def test_observation_category_does_not_mix_different_indices(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    etf.write(
        "universe",
        {
            "data": [
                {
                    "code": "512890",
                    "display_group": "observation",
                    "index_turnover_key": "dividend_low_vol",
                    "dashboard_eligible": True,
                },
                {
                    "code": "515180",
                    "display_group": "observation",
                    "index_turnover_key": "dividend",
                    "dashboard_eligible": True,
                },
            ]
        },
    )
    for code, shares in [("512890", "10"), ("515180", "20")]:
        etf.write(
            "etfs/" + code,
            {"data": {"series": [{"date": "2026-01-01", "qfq_total_units_yi": shares}]}},
        )
    group = etf.detail("512890")["group"][0]
    assert group["expected"] == 1 and group["qfq_total_units_yi"] == "10"


def test_group_weighted_returns_members_and_missing_amount(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    etf.write(
        "universe",
        {
            "data": [
                {"code": code, "display_group": "test", "dashboard_eligible": True}
                for code in ("510310", "510300")
            ]
        },
    )
    for code, price, amount in [("510310", "11", "30"), ("510300", "9", "10")]:
        etf.write(
            "etfs/" + code,
            {
                "status": "ready",
                "data": {
                    "series": [
                        {
                            "date": "2026-01-01",
                            "etf_qfq_close": "10",
                            "etf_qfq_turnover_est_yi": amount,
                        },
                        {
                            "date": "2026-01-02",
                            "etf_qfq_close": price,
                            "etf_qfq_turnover_est_yi": amount,
                            "qfq_delta_units_yi": "1",
                        },
                        {
                            "date": "2026-01-03",
                            "etf_qfq_close": price,
                            "etf_qfq_turnover_est_yi": None if code == "510300" else amount,
                        },
                    ]
                },
            },
        )
    result = etf.detail("510310")
    assert len(result["members"]) == 2
    assert Decimal(result["group"][1]["return_pct"]) == Decimal("5")
    assert Decimal(result["group"][1]["flow_yi"]) == Decimal("20")
    assert Decimal(result["group"][1]["qfq_delta_units_yi"]) == Decimal("2")
    assert result["group"][2]["return_pct"] is None
    assert result["group"][2]["etf_qfq_turnover_est_yi"] is None
    assert result["members"][0]["series"][1]["return_pct"] == "10.0"


@pytest.mark.parametrize("latest,expected_calls", [("2026-11-03",1),("2026-11-04",0)])
def test_new_closed_session_bypasses_recent_success_but_pending_source_keeps_backoff(monkeypatch, latest, expected_calls):
    from datetime import UTC, datetime
    from app import research_etf_native as native
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None): return datetime(2026,11,4,14,tzinfo=UTC)
    monkeypatch.setattr(etf,"datetime",Clock)
    docs={"refresh":{"attemptedAt":"2026-11-04T13:55:00+00:00","status":"partial"},"universe":{"data":[{"code":"510310","name":"ETF"}]}}
    monkeypatch.setattr(etf,"read",lambda name:docs.get(name,{}))
    monkeypatch.setattr(etf,"write",lambda name,value:docs.update({name:value}))
    monkeypatch.setattr(native,"closed_session_target",lambda _:"2026-11-04")
    monkeypatch.setattr(native,"read",lambda _: {"sessions":[latest]})
    calls=[]
    def collect(*_):
        calls.append(True)
        return {"sessions":["2026-11-04"],"retrievedAt":Clock.now().isoformat(),"catalog":[{"code":"510310","name":"ETF"}],"failures":[]}
    monkeypatch.setattr(native,"refresh",collect)
    monkeypatch.setattr(native,"publish_tracking",lambda *_:[])
    etf.refresh()
    assert len(calls)==expected_calls


@pytest.mark.parametrize(
    "status,minutes,expected_pending",
    [("partial", 9, None), ("partial", 10, True), ("error", 10, True),
     ("ready", 10, None), ("ready", 360, False)],
)
def test_pending_daily_retry_is_ten_minutes_and_complete_maintenance_is_six_hours(
    monkeypatch, status, minutes, expected_pending
):
    from datetime import UTC, datetime
    from app import research_etf_native as native

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 4, 8, tzinfo=UTC) + timedelta(minutes=minutes)

    monkeypatch.setattr(etf, "datetime", Clock)
    docs = {
        "refresh": {"attemptedAt": "2026-11-04T08:00:00+00:00", "status": status},
        "universe": {"data": [{"code": "510310", "name": "ETF"}]},
    }
    monkeypatch.setattr(etf, "read", lambda name: docs.get(name, {}))
    monkeypatch.setattr(etf, "write", lambda name, value: docs.update({name: value}))
    monkeypatch.setattr(native, "closed_session_target", lambda _: "2026-11-04")
    monkeypatch.setattr(native, "read", lambda _: {"sessions": ["2026-11-04"]})
    calls = []

    def collect(*args, **kwargs):
        calls.append(kwargs.get("pending_only", False))
        return {"sessions": ["2026-11-04"], "retrievedAt": Clock.now().isoformat(),
                "catalog": [{"code": "510310", "name": "ETF"}], "failures": []}

    monkeypatch.setattr(native, "refresh", collect)
    monkeypatch.setattr(native, "publish_tracking", lambda *args, **kwargs: [])
    etf.refresh()
    assert calls == ([] if expected_pending is None else [expected_pending])
    if calls:
        assert docs["refresh"]["status"] == "ready"
        etf.refresh()
        assert len(calls) == 1


def test_periodic_check_aligns_with_1510_and_ten_minute_retry_due_time():
    from datetime import UTC, datetime

    assert etf._next_check_seconds(datetime(2026, 11, 4, 7, 9, 40, tzinfo=UTC), {}) == 20
    assert etf._next_check_seconds(datetime(2026, 11, 4, 8, 7, tzinfo=UTC), {
        "status": "partial", "attemptedAt": "2026-11-04T08:00:00+00:00"
    }) == 180
    assert etf._next_check_seconds(datetime(2026, 11, 4, 8, 7, tzinfo=UTC), {
        "status": "ready", "attemptedAt": "2026-11-04T08:00:00+00:00"
    }) == 300


def test_1510_new_target_bypasses_a_one_minute_old_attempt_and_old_source_date_is_not_ready(monkeypatch):
    from datetime import UTC, datetime
    from app import research_etf_native as native

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 4, 7, 10, tzinfo=UTC)

    monkeypatch.setattr(etf, "datetime", Clock)
    docs = {
        "refresh": {"attemptedAt": "2026-11-04T07:09:00+00:00", "targetDate": "2026-11-03", "status": "ready"},
        "universe": {"data": [{"code": "510310", "name": "ETF"}]},
    }
    monkeypatch.setattr(etf, "read", lambda name: docs.get(name, {}))
    monkeypatch.setattr(etf, "write", lambda name, value: docs.update({name: value}))
    monkeypatch.setattr(native, "closed_session_target", lambda _: "2026-11-04")
    monkeypatch.setattr(native, "read", lambda _: {"sessions": ["2026-11-03"]})
    calls = []

    def collect(*args, **kwargs):
        calls.append(kwargs)
        return {"sessions": ["2026-11-03"], "retrievedAt": Clock.now().isoformat(),
                "catalog": [{"code": "510310", "name": "ETF"}], "failures": []}

    monkeypatch.setattr(native, "refresh", collect)
    monkeypatch.setattr(native, "publish_tracking", lambda *args, **kwargs: [])
    assert etf.refresh() == "partial"
    assert docs["refresh"]["targetDate"] == "2026-11-04"
    assert len(calls) == 1 and calls[0] == {}
    assert etf.refresh() == "up_to_date"
    assert len(calls) == 1  # retries of the same lagging target still respect ten minutes
