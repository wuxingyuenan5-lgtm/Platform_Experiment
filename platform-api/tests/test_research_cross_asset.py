from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.research_cross_asset import compare, correlation

pytestmark = pytest.mark.unit


def test_compare_intersects_dates_never_fills_and_keeps_price_precision():
    today = date(2026, 10, 15)
    points = [
        {"date": (today - timedelta(days=20 - i)).isoformat(), "value": str(100 + i)}
        for i in range(20)
    ]
    # An unpaired spike must not leak into the common-date return calculation.
    left = {"id": "spy", "label": "SPY", "status": "ready", "history": points}
    right = {"id": "btc", "label": "BTC", "status": "ready", "history": points[1:]}
    result = compare([left, right, {"id": "gld", "label": "GLD", "history": []}], 30, today)
    assert result["dates"][0] == points[1]["date"]
    assert len(result["dates"]) == 19
    assert result["assets"][0]["normalized"][0] == 100
    assert result["assets"][0]["returnPct"] == (Decimal(119) / 101 - 1) * 100
    assert abs(result["assets"][0]["correlation20"] - 1) < Decimal("1e-25")
    assert result["assets"][0]["downsideMeanPct"] is None
    assert result["status"] == "partial" and result["unavailable"] == ["GLD"]


def test_correlation_degenerate_and_negative():
    assert correlation([Decimal(1)] * 20, [Decimal(2)] * 20) is None
    assert correlation([Decimal(i) for i in range(9)], [Decimal(i) for i in range(9)]) is None
    assert correlation([Decimal(i) for i in range(20)], [Decimal(-i) for i in range(20)]) == -1


def test_current_day_and_invalid_price_are_excluded():
    result = compare(
        [
            {
                "id": "spy",
                "label": "SPY",
                "history": [
                    {"date": "2026-10-14", "value": "10"},
                    {"date": "2026-10-15", "value": "20"},
                    {"date": "2026-10-13", "value": None},
                    {"date": "2026-10-12", "value": "NaN"},
                ],
            }
        ],
        30,
        date(2026, 10, 15),
    )
    assert result["status"] == "no_data"


def test_route_enforces_research_permission_range_and_decimal_encoding(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app import research_routes
    from app.auth import Principal, require_principal

    app = FastAPI()
    app.include_router(research_routes.router)
    monkeypatch.setattr(
        research_routes,
        "read_cross_asset",
        lambda days: {"days": days, "value": Decimal("0.1234567890123456789")},
    )
    app.dependency_overrides[require_principal] = lambda: Principal("reader", (), "session")
    with TestClient(app) as client:
        assert client.get("/api/v1/research/cross-asset").status_code == 403
        app.dependency_overrides[require_principal] = lambda: Principal(
            "reader", ("admin",), "session"
        )
        assert client.get("/api/v1/research/cross-asset?days=29").status_code == 422
        result = client.get("/api/v1/research/cross-asset?days=180")
        assert result.status_code == 200
        assert result.json() == {"days": 180, "value": "0.1234567890123456789"}
