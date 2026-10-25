from datetime import date, timedelta
from decimal import Decimal

from app.research_equity_styles import build_styles


def test_style_spreads_and_ratio_are_distinct_and_stale_is_excluded(monkeypatch):
    import app.research_equity_styles as module

    monkeypatch.setattr(
        module, "US_STYLES", (("A", "A", "scope", "url"), ("B", "B", "scope", "url"))
    )
    monkeypatch.setattr(module, "STYLE_PAIRS", {"us": (("A/B", "A", "B"),)})
    days = [(date(2026, 9, 1) + timedelta(days=i)).isoformat() for i in range(21)]
    a = [{"date": d, "value": 100 + i} for i, d in enumerate(days)]
    b = [{"date": d, "value": Decimal(100) + Decimal(i) / 2} for i, d in enumerate(days)]
    rows = {
        "A": {"date": days[-1], "status": "ready", "history": a},
        "B": {"date": days[-1], "status": "ready", "history": b},
    }
    result = build_styles("us", rows, {}, b, days, days[-1])
    assert result["items"][0]["relative20"] == 10
    pair = result["pairs"][0]
    assert pair["spread20"] == 10
    assert pair["history"][0]["value"] == 100
    assert pair["history"][-1]["value"] == Decimal(120) / 110 * 100
    rows["B"]["status"] = "stale"
    stale = build_styles("us", rows, {}, b, days, days[-1])
    assert stale["pairs"][0]["spread20"] is None
    assert all(p["value"] is None for p in stale["pairs"][0]["history"])


def test_style_missing_session_is_not_shortened_or_filled(monkeypatch):
    import app.research_equity_styles as module

    monkeypatch.setattr(
        module, "CN_STYLES", (("A", "A", "scope", "url"), ("B", "B", "scope", "url"))
    )
    monkeypatch.setattr(module, "STYLE_PAIRS", {"cn": (("A/B", "A", "B"),)})
    days = [(date(2026, 9, 1) + timedelta(days=i)).isoformat() for i in range(21)]
    points = [{"date": d, "value": 100 + i} for i, d in enumerate(days)]
    refs = {
        "A": {"date": days[-1], "history": [p for p in points if p["date"] != days[-3]]},
        "B": {"date": days[-1], "history": points},
    }
    result = build_styles("cn", {}, refs, points, days, days[-1])
    assert result["items"][0]["return1"] is not None
    assert result["items"][0]["return5"] is None
    assert result["pairs"][0]["spread20"] is None
    assert result["pairs"][0]["history"][-3]["value"] is None


def test_catalog_keeps_transport_subsegments_and_all_style_producers():
    from app.research_equity_catalog import (
        CN_REFERENCE_CODES,
        CN_STYLES,
        CN_THEMES,
        US_EXTRA_SYMBOLS,
        US_STYLES,
        US_THEMES,
    )

    for catalog in (CN_THEMES, US_THEMES):
        transport = dict(dict(catalog)["交通运输／全球贸易"])
        assert {"油运", "集运", "干散货"} <= transport.keys()
        assert "BWET" not in " ".join(transport.values())
    assert {r[0] for r in CN_STYLES} <= set(CN_REFERENCE_CODES)
    assert {r[0] for r in US_STYLES} <= set(US_EXTRA_SYMBOLS)
