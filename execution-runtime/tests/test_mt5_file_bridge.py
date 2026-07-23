from decimal import Decimal

from app.mt5_file_bridge import read_mt5_bridge_snapshot


def test_read_mt5_bridge_snapshot_returns_quote_and_positions(tmp_path) -> None:
    bridge_file = tmp_path / "variable_global_mt5_bridge.json"
    bridge_file.write_text(
        """
        {
          "symbol": "XAUUSD+",
          "bid": 4115.25,
          "ask": 4115.65,
          "last": 4115.45,
          "swapLong": -42.5,
          "swapShort": 24.25,
          "time": "2026-07-22 19:58:01",
          "positions": [
            {
              "ticket": 9981,
              "symbol": "XAUUSD+",
              "side": "sell",
              "volume": 0.50,
              "priceOpen": 4117.00,
              "profit": -7.25
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    snapshot = read_mt5_bridge_snapshot(str(bridge_file), "XAUUSD+")

    assert snapshot.status == "available"
    assert snapshot.quote is not None
    assert snapshot.quote.bid == Decimal("4115.25")
    assert snapshot.quote.ask == Decimal("4115.65")
    assert snapshot.quote.mid == Decimal("4115.45")
    assert snapshot.positions[0].quantity == Decimal("-0.50")
    assert snapshot.positions[0].average_price == Decimal("4117.0")
    assert snapshot.positions[0].unrealized_pnl == Decimal("-7.25")
    assert snapshot.reason == "swapLong=-42.5;swapShort=24.25"


def test_read_mt5_bridge_snapshot_reports_missing_file(tmp_path) -> None:
    snapshot = read_mt5_bridge_snapshot(
        str(tmp_path / "missing.json"),
        "XAUUSD+",
    )

    assert snapshot.status == "unavailable"
    assert "not found" in (snapshot.reason or "")
