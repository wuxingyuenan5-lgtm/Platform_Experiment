from app.research_equity_observatory import market_breadth


def test_breadth_requires_exact_session_coverage_and_excludes_etf():
    sessions = [f"2026-10-{n:02}" for n in range(1, 22)]
    observations = {
        code: {
            "date": sessions[-1],
            "history": [
                {"date": d, "value": i + 10}
                for i, d in enumerate(sessions)
                if code != "gap" or i != 5
            ],
        }
        for code in ["up", "gap", "ETF"]
    }
    result = market_breadth(observations, sessions, sessions[-1], {"up", "gap"})
    assert result["expected"] == 2
    assert result["advancing"] == 2
    assert result["participation"][0]["valid"] == 1
    assert result["participation"][0]["highs"] == 1
    assert result["participation"][0]["abovePct"] == 100
    assert result["participation"][1]["valid"] == 0
    assert result["participation"][1]["abovePct"] is None


def test_new_snapshot_date_does_not_read_or_relabel_yesterdays_history():
    sessions = [f"2026-10-{n:02}" for n in range(1, 22)]
    observations = {
        "stock": {
            "date": "2026-10-22",
            "history": [{"date": d, "value": 100 + i} for i, d in enumerate(sessions)],
        }
    }
    result = market_breadth(observations, sessions, "2026-10-22")
    assert result["valid"] == 0
    assert all(r["valid"] == 0 and r["abovePct"] is None for r in result["participation"])
    # Same-day reported change remains usable without pretending that MA history exists.
    observations["stock"]["returnPct"] = "-2"
    result = market_breadth(observations, sessions, "2026-10-22")
    assert result["declining"] == 1 and result["valid"] == 1
    assert result["participation"][0]["valid"] == 0
