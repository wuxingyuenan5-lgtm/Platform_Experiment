from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.research_a_share_refresh import _build_stock_rows
from app.research_data_schemas import AShareIndexHistoryPoint


def test_current_valid_stored_history_does_not_require_duplicate_download(monkeypatch):
    import app.research_a_share_refresh as refresh

    points = [AShareIndexHistoryPoint(observed_at=date(2026, 10, 28), close=Decimal("32.61"))]
    monkeypatch.setattr(refresh, "read_stored_stock_histories", lambda codes: {"689009": points})
    monkeypatch.setattr(refresh, "_stock_session_days", lambda *args: [])

    class Quote(SimpleNamespace):
        def __getattr__(self, name):
            return None

    quote = Quote(
        security_name="九号公司",
        observed_at=datetime(2026, 10, 28, 15, tzinfo=UTC),
        price=Decimal("32.61"),
        return_pct=Decimal("-1.33"),
        currency="CNY",
        turnover_yuan=Decimal("100000000"),
    )
    rows, _ = _build_stock_rows(["689009"], {"689009": quote}, {}, {}, {}, "2026-10-28")
    assert rows[0]["status"] == "ready"
    assert rows[0]["history_source"] == "stored"
    points[0].observed_at = date(2026, 10, 27)
    rows, _ = _build_stock_rows(["689009"], {"689009": quote}, {}, {}, {}, "2026-10-28")
    assert rows[0]["status"] == "partial"
