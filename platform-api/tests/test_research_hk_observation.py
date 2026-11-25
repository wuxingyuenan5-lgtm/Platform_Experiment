from datetime import date, timedelta
from decimal import Decimal

from app.research_equity_metrics import hk_session_metrics


def points(n):
    start = date(2025, 1, 1)
    return [{"date": (start + timedelta(days=i)).isoformat(), "value": str(100 + i)} for i in range(n)]


def test_hk_session_windows_use_n_plus_one_prices_and_complete_averages():
    rows = points(252)
    result = hk_session_metrics(list(reversed(rows)))
    assert result["return5"] == (Decimal(351) / 346 - 1) * 100
    assert result["return20"] == (Decimal(351) / 331 - 1) * 100
    assert result["deviation20"] == (Decimal(351) / Decimal("341.5") - 1) * 100
    assert result["drawdown252"] == 0
    assert hk_session_metrics(rows[-251:])["drawdown252"] is None


def test_missing_quotes_do_not_compress_return_windows_or_backdate_latest():
    rows = points(30)
    rows[-10]["value"] = None
    result = hk_session_metrics(rows)
    assert result["return20"] is None
    assert result["deviation20"] is None
    assert result["return5"] == (Decimal(129) / 124 - 1) * 100
    rows[-1]["value"] = None
    result = hk_session_metrics(rows)
    assert result["date"] == rows[-1]["date"]
    assert result["value"] is None and result["returnPct"] is None


def test_hk_metrics_preserve_negative_returns_and_revised_duplicate_session():
    rows = points(21)
    rows.append({**rows[-1], "value": "90"})
    result = hk_session_metrics(rows)
    assert result["return20"] == -10
    assert result["returnPct"] == (Decimal(90) / 119 - 1) * 100
    rows[-1]["value"] = "NaN"
    assert hk_session_metrics(rows)["returnPct"] is None


def test_hk_projection_keeps_sources_full_history_and_independent_benchmark():
    from app.research_equity_observatory import build_hk

    rows = points(300)
    sources = {"hk_hstech": {"name": "科技", "rows": rows, "url": "https://example.com/hk", "status": "ready", "observationDate": rows[-1]["date"]}}
    benchmark = {"name": "沪深300", "history": points(30), "status": "ready"}
    result = build_hk("2025-11-01", sources, benchmark)
    tech = next(row for row in result["indices"] if row["id"] == "hk_hstech")
    assert len(tech["history"]) == 300
    assert tech["sourceUrl"] == "https://example.com/hk"
    assert tech["return20"] == (Decimal(399) / 379 - 1) * 100
    assert result["benchmark"] == benchmark
    assert result["indices"][0]["return5"] is None


def test_benchmark_failure_does_not_fail_other_hong_kong_content(monkeypatch):
    from app import research_a_share_repository as repository
    from app.research_equity_observatory import hk_benchmark, build_hk

    monkeypatch.setattr(repository, "read_index_history", lambda _: (_ for _ in ()).throw(OSError("offline")))
    benchmark = hk_benchmark()
    assert benchmark["status"] == "error" and not benchmark["history"]
    result = build_hk("2026-11-05", {"hk_hsi": {"rows": points(30)}}, benchmark)
    assert result["indices"][0]["value"] == 129
    assert result["benchmark"]["status"] == "error"
