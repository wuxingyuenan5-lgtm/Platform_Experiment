from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.research_a_share_refresh import _history_return
from app.research_data_schemas import AShareIndexHistoryPoint
from app.research_equity_themes import window_metrics

pytestmark = pytest.mark.unit


def test_five_and_twenty_sessions_use_n_plus_one_closes_and_compound():
    days = [(date(2026, 8, 1) + timedelta(days=i)).isoformat() for i in range(22)]
    closes = [Decimal("100") * Decimal("1.01") ** i for i in range(22)]
    points = [
        AShareIndexHistoryPoint(observed_at=d, close=v) for d, v in zip(days, closes, strict=True)
    ]
    themed = window_metrics(
        [{"date": d, "value": str(v)} for d, v in zip(days, closes, strict=True)], days, days[-1]
    )
    for n in [5, 20]:
        expected = Decimal("1.01") ** n - 1
        assert _history_return(points, n, days) == pytest.approx(float(expected), abs=1e-12)
        assert float(themed[f"return{n}"]) == pytest.approx(float(expected * 100), abs=1e-10)
    assert _history_return(points, 20) != _history_return(points, 21)


def test_missing_sessions_and_duplicate_rows_never_shorten_return_window():
    days = [(date(2026, 8, 1) + timedelta(days=i)).isoformat() for i in range(8)]
    points = [AShareIndexHistoryPoint(observed_at=d, close=100 + i) for i, d in enumerate(days)]
    assert _history_return(points[:5], 5) is None
    assert _history_return(points + [points[-1]], 5, days) == _history_return(points, 5, days)
    missing = [p for p in points if str(p.observed_at) != days[-3]]
    assert _history_return(missing, 5, days) is None
    assert _history_return(points, 5, []) is None


def test_index_snapshot_short_history_is_not_a_week_month_or_year(monkeypatch):
    import asyncio

    from app.research_provider_a_share import AShareResearchProvider

    provider = AShareResearchProvider(
        timeout_seconds=1, user_agent="test", akshare_loader=lambda: None
    )
    monkeypatch.setattr(
        provider,
        "_direct_index_history",
        lambda *a: [
            {"date": date(2026, 10, 22), "close": Decimal("100"), "amount": None},
            {"date": date(2026, 10, 23), "close": Decimal("101"), "amount": None},
        ],
    )
    result = asyncio.run(provider._index_snapshot("000300", "沪深300", "sh000300"))
    assert result.return_1d_pct == Decimal("1")
    assert result.return_1w_pct is None
    assert result.return_1m_pct is None
    assert result.return_1y_pct is None
