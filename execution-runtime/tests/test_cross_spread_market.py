from decimal import Decimal

from app.cross_spread_market import build_cross_spread_snapshot
from app.models import MarketQuote


class FakeBybitSession:
    def get_tickers(self, *, category: str, symbol: str):
        assert category == "linear"
        assert symbol == "XAUTUSDT"
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": symbol,
                        "bid1Price": "3330.10",
                        "ask1Price": "3330.30",
                        "lastPrice": "3330.20",
                    }
                ]
            },
        }

    def get_positions(self, *, category: str, symbol: str):
        assert category == "linear"
        assert symbol == "XAUTUSDT"
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": symbol,
                        "side": "Buy",
                        "size": "2.5",
                        "avgPrice": "3328.00",
                        "unrealisedPnl": "5.5",
                    }
                ]
            },
        }


class PositionFailingBybitSession(FakeBybitSession):
    def get_positions(self, *, category: str, symbol: str):
        raise RuntimeError("position endpoint rejected")


class FakeMt5Module:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1

    def initialize(self, **kwargs):
        return True

    def login(self, *args, **kwargs):
        return True

    def symbol_info_tick(self, symbol: str):
        assert symbol == "XAUUSD+"
        return type("Tick", (), {"bid": 3331.0, "ask": 3331.4, "last": 3331.2})()

    def positions_get(self, *, symbol: str):
        assert symbol == "XAUUSD+"
        return [
            type(
                "Position",
                (),
                {
                    "ticket": 123,
                    "symbol": symbol,
                    "type": self.ORDER_TYPE_SELL,
                    "volume": 0.25,
                    "price_open": 3332.0,
                    "profit": -8.0,
                },
            )()
        ]

    def shutdown(self):
        pass


def test_cross_spread_snapshot_uses_real_quotes_and_positions_without_secret_material(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_API_KEY", "real-key")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_SECRET", "real-secret")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_LOGIN", "1234567")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_PASSWORD", "mt5-password")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_SERVER", "BrokerDemo")

    snapshot = build_cross_spread_snapshot(
        bybit_symbol="XAUTUSDT",
        mt5_symbol="XAUUSD+",
        bybit_session_factory=lambda **_: FakeBybitSession(),
        mt5_module=FakeMt5Module(),
    )

    assert snapshot.status == "available"
    assert snapshot.bybit.quote == MarketQuote(
        bid=Decimal("3330.10"),
        ask=Decimal("3330.30"),
        mid=Decimal("3330.20"),
        last=Decimal("3330.20"),
        currency="USDT",
    )
    assert snapshot.mt5.quote == MarketQuote(
        bid=Decimal("3331.0"),
        ask=Decimal("3331.4"),
        mid=Decimal("3331.2"),
        last=Decimal("3331.2"),
        currency="USD",
    )
    assert snapshot.long_spread == Decimal("-0.70")
    assert snapshot.short_spread == Decimal("-1.30")
    assert snapshot.bybit.positions[0].quantity == Decimal("2.5")
    assert snapshot.mt5.positions[0].quantity == Decimal("-0.25")
    serialized = snapshot.model_dump_json().lower()
    assert "real-key" not in serialized
    assert "real-secret" not in serialized
    assert "mt5-password" not in serialized


def test_cross_spread_snapshot_keeps_bybit_quote_when_position_endpoint_fails(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_API_KEY", "real-key")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_SECRET", "real-secret")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_LOGIN", "1234567")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_PASSWORD", "mt5-password")
    monkeypatch.setenv("VG_SECRET_MT5_DEMO_001_SERVER", "BrokerDemo")

    snapshot = build_cross_spread_snapshot(
        bybit_symbol="XAUTUSDT",
        mt5_symbol="XAUUSD+",
        bybit_session_factory=lambda **_: PositionFailingBybitSession(),
        mt5_module=FakeMt5Module(),
    )

    assert snapshot.bybit.status == "available"
    assert snapshot.bybit.quote is not None
    assert snapshot.bybit.positions == []
    assert "position endpoint rejected" in (snapshot.bybit.reason or "")
