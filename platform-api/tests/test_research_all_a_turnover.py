from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import research_all_a_turnover as turnover


def stamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=turnover.CHINA)


def quotes(at="2026-11-05T10:00:00", state=2):
    return [
        {
            "f12": code,
            "f6": str((i + 1) * 100000000),
            "f5": 100,
            "f124": int(stamp(at).timestamp()),
            "f292": state,
        }
        for i, code in enumerate(["600001", "000001", "920001"])
    ]


def test_aggregate_includes_all_markets_and_retains_explicit_suspension():
    rows = quotes()
    rows += [
        {**rows[0], "f12": "600002", "f292": 6, "f5": "-", "f6": "-"},
        {**rows[0], "f12": "600003", "f292": 7, "f6": "-"},
        {**rows[0], "f12": "688999", "f292": 9, "f6": "-"},
        {**rows[0], "f12": "810011", "f6": "-"},
    ]
    point = turnover.aggregate(rows, stamp("2026-11-05T10:15:00"))
    assert Decimal(point["amountYi"]) == 6
    assert point["securityCount"] == 4 and point["suspendedCount"] == 1
    assert point["slot"] == "10:00"  # source time, not retrieval time


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda r: r[0].update(f6="-"), "missing_stock_amount"),
        (
            lambda r: r[0].update(f124=int(stamp("2026-11-04T10:00:00").timestamp())),
            "mixed_quote_dates",
        ),
        (lambda r: r[0].update(f124=int(stamp("2026-11-05T09:55:00").timestamp())), "unaligned"),
        (lambda r: r.append(r[0]), "duplicate"),
        (lambda r: r.pop(), "incomplete_market"),
    ],
)
def test_incomplete_or_misaligned_quote_does_not_become_all_a(change, reason):
    rows = quotes()
    change(rows)
    with pytest.raises(ValueError, match=reason):
        turnover.aggregate(rows, stamp("2026-11-05T10:15:00"))


def test_final_snapshot_requires_close_window_and_confirmed_quotes():
    rows = quotes("2026-11-05T15:03:00", 5)
    with pytest.raises(ValueError, match="close_window"):
        turnover.aggregate(rows, stamp("2026-11-05T15:40:00"), final=True)
    assert turnover.aggregate(rows, stamp("2026-11-05T16:15:00"), final=True)["slot"] == "close"
    for state in (2, 18):
        rows[0]["f292"] = state
        with pytest.raises(ValueError, match="close_not_confirmed"):
            turnover.aggregate(rows, stamp("2026-11-05T16:15:00"), final=True)


def fixture():
    days = [(stamp("2026-10-01") + timedelta(days=i)).date().isoformat() for i in range(20)]
    archive = {
        "days": {d: {"10:00": {"amountYi": "50"}, "close": {"amountYi": "100"}} for d in days}
    }
    archive["days"]["2026-11-05"] = {
        "10:00": {
            "slot": "10:00",
            "amountYi": "80",
            "asOf": stamp("2026-11-05T10:00:00").isoformat(),
        }
    }
    return archive, days + ["2026-11-05"]


def test_same_slot_progress_uses_daily_ratios_and_excludes_current_day():
    archive, sessions = fixture()
    result = turnover.project(archive, sessions, stamp("2026-11-05T10:15:00"))
    assert result["status"] == "ready"
    assert Decimal(result["latest"]["estimate5Yi"]) == 160
    assert Decimal(result["latest"]["estimate20Yi"]) == 160
    archive["days"][sessions[-2]]["10:00"]["amountYi"] = "200"
    archive["days"][sessions[-2]]["close"]["amountYi"] = "400"
    assert (
        Decimal(
            turnover.project(archive, sessions, stamp("2026-11-05T10:15:00"))["latest"][
                "estimate5Yi"
            ]
        )
        == 160
    )
    del archive["days"][sessions[-2]]["10:00"]
    result = turnover.project(archive, sessions, stamp("2026-11-05T10:15:00"))
    assert result["latest"]["samples5"] == 4
    assert result["latest"]["estimate5Yi"] is None  # no substitute older day
    assert result["latest"]["estimate20Yi"] is None


def test_stale_and_close_are_distinct_from_live_forecast():
    archive, sessions = fixture()
    assert turnover.project(archive, sessions, stamp("2026-11-05T10:30:00"))["status"] == "stale"
    archive["days"]["2026-11-05"]["close"] = {
        "slot": "close",
        "amountYi": "150",
        "asOf": stamp("2026-11-05T15:05:00").isoformat(),
    }
    result = turnover.project(archive, sessions, stamp("2026-11-05T16:15:00"))
    assert result["status"] == "closed" and result["latest"]["estimate5Yi"] is None
    assert turnover.project({}, sessions, stamp("2026-11-05T10:15:00"))["status"] == "no_data"


def test_projection_anchors_future_path_to_latest_actual_and_daily_progress():
    archive, sessions = fixture()
    for day in sessions[:-1]:
        archive["days"][day]["14:00"] = {"amountYi": "75"}
    result = turnover.project(archive, sessions, stamp("2026-11-05T10:15:00"))
    paths = result["paths"]
    assert [r["slot"] for r in paths] == ["10:00", "14:00", "close"]
    assert [r["amountYi"] for r in paths] == ["80", None, None]
    assert [Decimal(r["forecast5Yi"]) for r in paths] == [80, 120, 160]
    assert [Decimal(r["forecast20Yi"]) for r in paths] == [80, 120, 160]
    del archive["days"][sessions[-2]]["14:00"]
    result = turnover.project(archive, sessions, stamp("2026-11-05T10:15:00"))
    assert result["paths"][1]["forecast5Yi"] is None
    stale = turnover.project(archive, sessions, stamp("2026-11-05T11:00:00"))
    assert all(r["forecast5Yi"] is None for r in stale["paths"])


def test_last_trading_close_stays_closed_on_weekend():
    archive, sessions = fixture()
    archive["days"]["2026-11-05"]["close"] = {
        "slot": "close",
        "amountYi": "150",
        "asOf": stamp("2026-11-05T15:05:00").isoformat(),
    }
    result = turnover.project(archive, sessions, stamp("2026-11-07T10:00:00"))
    assert result["status"] == "closed"


def test_storage_rejects_regression_and_preserves_previous_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    turnover.store(quotes(), stamp("2026-11-05T10:15:00"))
    rows = quotes("2026-11-05T10:05:00")
    rows[0]["f6"] = "1"
    with pytest.raises(ValueError, match="regressed"):
        turnover.store(rows, stamp("2026-11-05T10:20:00"))
    assert list(turnover.read_archive()["days"]["2026-11-05"]) == ["10:00"]


def test_route_is_read_only_and_permission_scoped(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.auth import Principal, require_principal
    from app.research_routes import router

    monkeypatch.setattr(turnover, "read_archive", lambda: {})
    monkeypatch.setattr(turnover, "cached_sessions", lambda _: [])
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/v1/research/a-share/turnover-forecast"
    assert client.get(url).status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    response = client.get(url)
    assert response.status_code == 200 and response.json()["status"] == "no_data"
    assert response.headers["cache-control"] == "no-store"
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get(url).status_code == 403
