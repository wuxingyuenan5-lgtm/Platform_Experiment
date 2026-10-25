from datetime import date, timedelta
from decimal import Decimal

from app.research_equity_themes import build_themes, summarize, window_metrics


def history():
    return [
        {"date": (date(2026, 9, 1) + timedelta(days=i)).isoformat(), "value": 100 + i}
        for i in range(21)
    ]


def test_windows_require_every_benchmark_session_and_keep_null():
    points = history()
    days = [p["date"] for p in points]
    assert window_metrics(points, days, days[-1])["return20"] == 20
    assert window_metrics(points[1:], days, days[-1])["return20"] is None
    gap = [p for p in points if p != points[-3]]
    metrics = window_metrics(gap, days, days[-1])
    assert metrics["return1"] is not None
    assert metrics["return5"] is None and metrics["above20"] is None
    assert window_metrics(points[:-1], days, days[-1])["return1"] is None
    assert window_metrics(points, [], days[-1])["return20"] is None


def test_summary_deduplicates_members_and_ranks_each_window_by_coverage():
    rows = [{"code": str(i), "returnPct": i, "return20": i if i < 4 else None} for i in range(5)]
    result = summarize(rows + [rows[0]])
    assert result["expected"] == 5
    assert result["return20Count"] == 4 and result["return20Rankable"]
    assert result["return20"] == Decimal("1.5")
    assert not result["return5Rankable"] and result["return5"] is None
    rows[3]["return20"] = None
    assert not summarize(rows)["return20Rankable"]
    assert not summarize(rows[:2])["returnPctRankable"]


def test_etfs_are_separate_and_stale_stocks_do_not_enter_statistics(monkeypatch):
    import app.research_equity_themes as module

    monkeypatch.setattr(
        module, "US_THEMES", (("T", (("A", "ONE TWO"), ("B", "ONE THREE"))), ("Style", ()))
    )
    monkeypatch.setattr(module, "US_REFERENCES", {"T": [("ETF", "ETF", "partial", "scope", "url")]})
    points = history()
    end = points[-1]["date"]
    rows = {
        code: {"date": end, "status": "ready", "history": points}
        for code in ("ONE", "TWO", "THREE", "ETF")
    }
    rows["THREE"]["status"] = "stale"
    result = build_themes("us", rows, end, benchmark={"history": points})
    theme = result["items"][0]
    assert theme["expected"] == 3 and theme["return20Count"] == 2
    assert theme["relative20"] == 0
    assert theme["references"][0]["return20"] == 20
    assert all(m["code"] != "ETF" for m in theme["members"])
    assert result["items"][1]["expected"] == 0
    assert result["items"][1]["medianReturn"] is None


def test_us_projection_anchors_history_not_intraday_quote_and_preserves_stale(monkeypatch):
    from app import research_equity_observatory as module

    points = history()
    rows = [
        {
            "id": code,
            "symbol": code,
            "status": status,
            "asOf": "2026-09-22T13:00:00Z",
            "history": points,
            "name": code,
        }
        for code, status in (("SPY", "ready"), ("NVDA", "ready"), ("AMD", "stale"))
    ]
    monkeypatch.setattr(module, "read_dataset", lambda _: {"rows": rows, "status": "partial"})
    result = module.build_us("2026-09-22", {})
    assert result["date"] == points[-1]["date"]
    members = [m for t in result["themes"]["items"] for m in t["members"]]
    assert next(m for m in members if m["code"] == "NVDA")["return20"] == 20
    assert next(m for m in members if m["code"] == "AMD")["return20"] is None
