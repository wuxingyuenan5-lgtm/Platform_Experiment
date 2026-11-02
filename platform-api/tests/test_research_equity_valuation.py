from decimal import Decimal

import pytest

from app.research_equity_sources import parse_multpl
from app.research_equity_valuation import (
    build_valuation_charts,
    parse_index_metric,
    parse_russell,
    parse_ssga,
)


def test_multpl_percentage_preserves_percentage_points_and_estimate():
    rows = parse_multpl(
        '<table id="datatable"><tr><td>Oct 21, 2026 †</td><td>1.05%</td></tr></table>'
    )
    assert rows[0]["pe"] == Decimal("1.05")
    assert rows[0]["estimated"] is True


def test_index_identity_and_nulls_are_not_relabelled():
    with pytest.raises(ValueError, match="index_mismatch"):
        parse_index_metric('{"ticker":"USA","data":[]}', "NDX")
    assert (
        parse_index_metric(
            '{"ticker":"NDX","data":[{"trading_day (EOD)":"2026-06-30","value":null}]}', "NDX"
        )[0]["value"]
        is None
    )


def test_official_index_does_not_take_fund_pb():
    rows = parse_ssga(
        "<section>"
        "<h2>"
        "Fund Characteristics"
        "</h2>"
        "<table>"
        "<tr>"
        "<td>"
        "Price/Book"
        "</td>"
        "<td>"
        "5.63"
        "</td>"
        "</tr>"
        "</table>"
        "</section>"
        "<section>"
        "<h2>"
        "Index Characteristics "
        '<span class="date">'
        "as of Oct 21 2026"
        "</span>"
        "</h2>"
        "<table>"
        "<tr>"
        "<td>"
        "Price/Earnings"
        "</td>"
        "<td>"
        "21.85"
        "</td>"
        "</tr>"
        "<tr>"
        "<td>"
        "Price/Earnings Ratio FY1"
        "</td>"
        "<td>"
        "19.35"
        "</td>"
        "</tr>"
        "</table>"
        "</section>"
    )
    assert rows[0]["date"] == "2026-10-21"
    assert rows[0]["forwardFy1"] == Decimal("19.35")
    assert "pb" not in rows[0]


def test_public_snapshot_and_yearend_history_do_not_fill_forward():
    rows = parse_russell(
        "<p>"
        "Data through 30 September 2026"
        "</p>"
        "<table>"
        "<tr>"
        "<td>"
        "Russell 2000"
        "</td>"
        "<td>"
        "35.91"
        "</td>"
        "<td>"
        "23.59"
        "</td>"
        "<td>"
        "52%"
        "</td>"
        "<td>"
        "60.84"
        "</td>"
        "</tr>"
        "</table>"
        "<table>"
        "<tr>"
        "<th>"
        "Month"
        "</th>"
        "<th>"
        "Russell 2000"
        "</th>"
        "</tr>"
        "<tr>"
        "<td>"
        "2025 Dec"
        "</td>"
        "<td>"
        "35.52"
        "</td>"
        "</tr>"
        "<tr>"
        "<td>"
        "2020 Dec"
        "</td>"
        "<td>"
        "Negative"
        "</td>"
        "</tr>"
        "</table>"
    )
    assert [r["date"] for r in rows] == ["2025-12-31", "2026-09-30"]
    assert "forward" not in rows[0]


def test_cn_uses_same_index_price_and_keeps_valuation_sources_separate():
    chart = build_valuation_charts(
        {
            "csi_history_000300": {"rows": [{"date": "2026-10-21", "pe": "12", "close": "4000"}]},
            "choice_index_000300": {
                "rows": [{"date": "2026-10-22", "pe": "13", "pb": "1.5", "close": "4010"}]
            },
        },
        "cn",
    )[0]
    assert chart["prices"] == [{"date": "2026-10-21", "value": "4000"}]
    assert chart["metrics"][0]["history"] == [{"date": "2026-10-21", "value": "12"}]
    assert chart["metrics"][1]["history"] == [{"date": "2026-10-22", "value": "1.5"}]


def test_choice_test_bootstrap_is_small_and_existing_history_incremental():
    from datetime import date

    from app.research_equity_valuation import choice_window_start

    due = [("000300", "沪深300")]
    end = date(2026, 11, 2)
    assert choice_window_start({"choice_index_000300": {}}, due, end) == date(2026, 10, 4)
    old = {"choice_index_000300": {"schemaVersion": 2, "observationDate": "2026-10-30"}}
    assert choice_window_start(old, due, end) == date(2026, 10, 31)
    old["choice_index_000300"]["observationDate"] = "2020-01-01"
    assert choice_window_start(old, due, end) == date(2026, 10, 4)


def test_choice_quota_failure_cannot_retry_every_background_tick():
    from datetime import UTC, datetime, timedelta

    from app.research_equity_valuation import choice_source_due

    now = datetime(2026, 11, 2, tzinfo=UTC)
    doc = {
        "status": "error",
        "attemptedAt": (now - timedelta(hours=2)).isoformat(),
        "error": "RuntimeError: Choice csd:10001029",
    }
    assert not choice_source_due(doc, now)
    doc["attemptedAt"] = (now - timedelta(hours=21)).isoformat()
    assert choice_source_due(doc, now)


def test_choice_refresh_accumulates_history_and_failure_keeps_lkg(monkeypatch):
    import copy
    import json
    from types import SimpleNamespace

    from app import research_equity_sources as sources
    from app import research_equity_valuation as valuation

    stored = {
        "sources/choice_index_" + code: {
            "rows": [{"date": "2020-01-02", "close": "100", "pe": "10"}],
            "fetchedAt": "2020-01-03T00:00:00+00:00",
            "status": "ready",
        }
        for code, _ in valuation.CN_CHARTS
    }
    monkeypatch.setattr(sources, "read_artifact", lambda key: copy.deepcopy(stored[key]))
    monkeypatch.setattr(sources, "publish_artifact", lambda key, value: stored.update({key: value}))
    monkeypatch.setattr(sources, "archive", lambda *args: "raw-hash")
    records = [
        {"code": code + ".SH", "date": "2026-10-22", "close": "200", "pe": "20"}
        for code, _ in valuation.CN_CHARTS
    ]

    def run(*args, **kwargs):
        assert "force" not in args[0][2].lower()
        from datetime import date

        assert (date.fromisoformat(args[0][4]) - date.fromisoformat(args[0][3])).days < 30
        return SimpleNamespace(stdout=json.dumps({"ok": True, "records": records}))

    monkeypatch.setattr(valuation.subprocess, "run", run)
    result = valuation.collect_choice_indices()
    assert all(
        [r["date"] for r in doc["rows"]] == ["2020-01-02", "2026-10-22"] for doc in result.values()
    )
    for doc in stored.values():
        doc["fetchedAt"] = "2020-01-03T00:00:00+00:00"

    def fail(*args, **kwargs):
        raise OSError("SDK unavailable")

    monkeypatch.setattr(valuation.subprocess, "run", fail)
    failed = valuation.collect_choice_indices()
    assert all(d["status"] == "stale" and len(d["rows"]) == 2 for d in failed.values())
