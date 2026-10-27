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
