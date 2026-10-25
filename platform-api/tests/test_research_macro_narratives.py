from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.research_macro_narratives import build_driver, points, rolling_signal, state_evidence

pytestmark = pytest.mark.unit


def history(count=420):
    start = date(2023, 1, 1)
    return {
        (start + timedelta(days=i)).isoformat(): Decimal(100) + Decimal(i * i) / 1000
        for i in range(count)
    }


def test_rolling_scores_do_not_use_future_or_current_change_in_baseline():
    values = history()
    full = rolling_signal(values, "ratio")
    short = rolling_signal(dict(list(values.items())[:300]), "ratio")
    assert short and all(full[day] == value for day, value in short.items())
    first = next(iter(full))
    assert first == list(values)[146]
    assert full[first]["baselineCount"] == 126
    prior_changes = [
        float(values[list(values)[i]] / values[list(values)[i - 20]] - 1) for i in range(20, 146)
    ]
    mean = sum(prior_changes) / 126
    sd = (sum((v - mean) ** 2 for v in prior_changes) / 126) ** 0.5
    assert full[first]["score"] == pytest.approx((full[first]["change"] - mean) / sd)


def test_short_constant_nonpositive_or_discontinuous_histories_are_not_zero_filled():
    assert rolling_signal(history(100), "ratio") == {}
    flat = {d: Decimal(1) for d in history()}
    assert rolling_signal(flat, "difference") == {}
    values = history()
    for day in list(values)[200:310]:
        del values[day]
    assert max(rolling_signal(values, "ratio")) < list(history())[200]


def test_extended_exchange_holiday_does_not_reset_valid_history():
    values = history()
    for day in list(values)[300:308]:
        del values[day]
    result = rolling_signal(values, "ratio")
    assert list(values)[300] in result
    assert result[list(values)[300]]["baselineCount"] >= 126


def test_composites_require_both_legs_and_only_exact_common_dates():
    values = history()
    doc = {
        "status": "ready",
        "observations": [{"date": d, "value": str(v)} for d, v in values.items()],
    }
    definition = ("pair", "pair", "rates", "test", (("a", 1, "ratio"), ("b", -1, "ratio")))
    missing = build_driver(definition, {"a": doc}, date(2024, 3, 1))
    assert not missing["history"] and missing["status"] == "no_data"
    later = {**doc, "observations": doc["observations"][:-1]}
    paired = build_driver(definition, {"a": doc, "b": later}, date(2024, 3, 1))
    assert paired["history"][-1]["date"] == doc["observations"][-2]["date"]
    assert all(row["score"] == 0 for row in paired["history"])
    assert paired["history"][0]["momentum"] is None
    assert paired["history"][5]["momentum"] == 0


def test_invalid_and_forming_observations_are_excluded():
    doc = {
        "observations": [
            {"date": "2026-10-24", "value": "1.1234567890123456789"},
            {"date": "2026-10-25", "value": "999"},
            {"date": "2026-10-23", "value": "NaN"},
        ]
    }
    assert points(doc, date(2026, 10, 25)) == {"2026-10-24": Decimal("1.1234567890123456789")}


def test_narrative_endpoint_requires_research_permission(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app import research_routes
    from app.auth import Principal, require_principal

    app = FastAPI()
    app.include_router(research_routes.router)
    monkeypatch.setattr(
        research_routes, "read_macro_narratives", lambda: {"drivers": [], "status": "no_data"}
    )
    app.dependency_overrides[require_principal] = lambda: Principal("reader", (), "session")
    with TestClient(app) as client:
        assert client.get("/api/v1/research/macro/narratives").status_code == 403
        app.dependency_overrides[require_principal] = lambda: Principal(
            "reader", ("admin",), "session"
        )
        response = client.get("/api/v1/research/macro/narratives")
        assert response.status_code == 200 and response.json()["status"] == "no_data"
        assert response.headers["cache-control"].startswith("private")


def test_monthly_evidence_requires_contiguous_periods_and_retains_missing_dimensions():
    doc = {"observations": [{"date": f"2026-{m:02}-28", "value": m} for m in range(1, 7)]}
    result = state_evidence({"cn_manufacturing_pmi": doc}, "cn", date(2026, 10, 25))
    assert result["evidence"][0]["delta"] == "3"
    assert result["evidence"][-1]["value"] is None
    doc["observations"].pop(2)
    assert (
        state_evidence({"cn_manufacturing_pmi": doc}, "cn", date(2026, 10, 25))["evidence"][0][
            "delta"
        ]
        is None
    )
