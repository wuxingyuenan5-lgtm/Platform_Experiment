from datetime import date, timedelta
from decimal import Decimal

from app import research_theme_crowding as module
from app.research_data_schemas import AShareIndexHistoryPoint


def fixture(monkeypatch):
    monkeypatch.setattr(module, "CN_THEMES", (("Theme", (("X", "A B"), ("Y", "A"))),))
    days = [(date(2026, 10, 1) + timedelta(days=i)).isoformat() for i in range(7)]
    prices = {
        "A": [AShareIndexHistoryPoint(observed_at=d, close=10 + i) for i, d in enumerate(days)],
        "B": [AShareIndexHistoryPoint(observed_at=d, close=100) for d in days],
    }
    amounts = [
        (d, c, {"amountYuan": v})
        for d in days
        for c, v in (("A", 10), ("B", 20), ("__market__", 100))
    ]
    return days, prices, amounts


def test_same_market_denominator_dedup_and_fixed_base_price(monkeypatch):
    days, prices, amounts = fixture(monkeypatch)
    t = module.build_theme_crowding(prices, amounts, days, days[-1])["items"][0]
    assert t["expected"] == 2
    assert t["history"][-1]["sharePct"] == 30
    assert t["segments"][1]["history"][-1]["sharePct"] == 10  # not 10/30
    assert t["history"][0]["price"] == 100
    assert t["history"][-1]["price"] == 130  # normalized equal weight, not raw price average
    assert t["history"][3]["shareMa5"] is None
    assert t["history"][4]["shareMa5"] == Decimal(30)


def test_gaps_do_not_reweight_fill_zero_or_shorten_ma(monkeypatch):
    days, prices, amounts = fixture(monkeypatch)
    amounts = [r for r in amounts if (r[0], r[1]) != (days[2], "B")]
    prices["B"] = [p for p in prices["B"] if str(p.observed_at) != days[2]]
    t = module.build_theme_crowding(prices, amounts, days, days[-1])["items"][0]
    rows = t["history"]
    assert rows[2]["sharePct"] is None and rows[2]["amountCount"] == 1
    assert rows[2]["price"] is None and rows[2]["priceCount"] == 1
    assert all(r["shareMa5"] is None for r in rows)
    assert t["segments"][1]["history"][4]["shareMa5"] == 10  # independent coverage


def test_future_amounts_and_prices_are_excluded_and_invalid_denominator_stays_missing(monkeypatch):
    days, prices, amounts = fixture(monkeypatch)
    amounts = [r for r in amounts if (r[0], r[1]) != (days[3], "__market__")]
    result = module.build_theme_crowding(prices, amounts, days, days[4])["items"][0]
    assert result["history"][-1]["date"] == days[4]
    assert result["history"][3]["sharePct"] is None
    assert result["history"][-1]["shareMa5"] is None


def test_close_archive_keeps_market_total_and_rejects_partial_snapshot(monkeypatch):
    fixture(monkeypatch)
    stocks = [{"securityCode": str(i), "turnoverYuan": 1} for i in range(1000)]
    stocks += [{"securityCode": "A", "turnoverYuan": 10}, {"securityCode": "B", "turnoverYuan": 20}]
    assert not module.close_amount_points(stocks, "2026-10-28", closed=False)
    assert not module.close_amount_points(stocks[:10], "2026-10-28", closed=True)
    points = module.close_amount_points(stocks + [stocks[-1]], "2026-10-28", closed=True)
    assert len(points) == 3
    assert points[0][2]["amountYuan"] == 1030
    assert points[0][2]["count"] == 1002
    stocks[2]["turnoverYuan"] = None
    assert not module.close_amount_points(stocks, "2026-10-28", closed=True)


def test_same_date_publication_replaces_whole_amount_universe(tmp_path, monkeypatch):
    from app import research_a_share_repository as repository
    from app.config import get_settings
    from app.database import initialize_database

    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "amounts.db"))
    initialize_database()
    monkeypatch.setattr(repository, "write_dashboard", lambda *a, **kw: None)
    monkeypatch.setattr(repository, "write_stock_pool", lambda *a, **kw: None)
    for run_id, day, codes in (
        ("r1", "2026-10-27", ["__market__", "A", "B"]),
        ("r2", "2026-10-28", ["__market__", "A", "B"]),
        ("r3", "2026-10-28", ["__market__", "A"]),
    ):
        repository.start_refresh(run_id, day)
        repository.publish_refresh(
            run_id,
            None,
            pool={},
            datasets=[],
            histories=[
                (
                    "theme_amount",
                    [(day, c, {"amountYuan": "123.456789"}) for c in codes],
                    "test close",
                )
            ],
            trade_date=day,
            status="ready",
        )
    rows = repository.read_theme_amount_history()
    assert len(rows) == 5
    assert not any(d == "2026-10-28" and c == "B" for d, c, _ in rows)
    assert all(p["amountYuan"] == "123.456789" for _, _, p in rows)
