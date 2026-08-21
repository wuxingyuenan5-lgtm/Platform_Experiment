from decimal import Decimal

from app.cross_spread_market import (
    _SNAPSHOT_CACHE,
    build_cross_spread_snapshot,
    estimate_cached_fill_price,
)
from app.fake_gateway import FakeGateway
from app.models import CrossSpreadSnapshotResponse, MarketQuote, SubmitOrderCommand


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


def test_cross_spread_snapshot_uses_fake_gateway_positions_when_runtime_gateway_is_simulation(
    monkeypatch,
) -> None:
    import app.cross_spread_market as market
    from app.config import get_settings

    _SNAPSHOT_CACHE.clear()
    get_settings().gateway_name = "fake"

    monkeypatch.setattr(
        market,
        "_build_bybit_snapshot",
        lambda **_: market.CrossSpreadVenueSnapshot(
            venue="bybit",
            symbol="XAUTUSDT",
            status="available",
            quote=MarketQuote(
                bid=Decimal("3330.10"),
                ask=Decimal("3330.30"),
                mid=Decimal("3330.20"),
                last=Decimal("3330.20"),
                currency="USDT",
            ),
            positions=[],
        ),
    )
    monkeypatch.setattr(
        market,
        "_build_mt5_snapshot",
        lambda **_: market.CrossSpreadVenueSnapshot(
            venue="mt5",
            symbol="XAUUSD+",
            status="available",
            quote=MarketQuote(
                bid=Decimal("3331.00"),
                ask=Decimal("3331.40"),
                mid=Decimal("3331.20"),
                last=Decimal("3331.20"),
                currency="USD",
            ),
            positions=[],
        ),
    )
    monkeypatch.setattr(
        market,
        "_gateway_positions_for_symbol",
        lambda symbol: [
            market.VenuePosition(
                symbol=symbol,
                side="buy" if symbol == "XAUTUSDT" else "sell",
                quantity=Decimal("1") if symbol == "XAUTUSDT" else Decimal("-0.01"),
                averagePrice=Decimal("2500") if symbol == "XAUTUSDT" else Decimal("2501"),
                unrealizedPnl=None,
                externalId=f"pos-{symbol}",
            )
        ],
    )

    snapshot = build_cross_spread_snapshot(
        bybit_symbol="XAUTUSDT",
        mt5_symbol="XAUUSD+",
    )

    assert snapshot.bybit.positions[0].quantity == Decimal("1")
    assert snapshot.mt5.positions[0].quantity == Decimal("-0.01")


def test_fake_gateway_uses_cached_market_price_before_fallback() -> None:
    _SNAPSHOT_CACHE.clear()
    snapshot = CrossSpreadSnapshotResponse(
        status="available",
        bybit={
            "venue": "bybit",
            "symbol": "XAUTUSDT",
            "status": "available",
            "quote": MarketQuote(
                bid=Decimal("3330.10"),
                ask=Decimal("3330.30"),
                mid=Decimal("3330.20"),
                last=Decimal("3330.20"),
                currency="USDT",
            ),
            "positions": [],
        },
        mt5={
            "venue": "mt5",
            "symbol": "XAUUSD+",
            "status": "available",
            "quote": MarketQuote(
                bid=Decimal("3331.00"),
                ask=Decimal("3331.40"),
                mid=Decimal("3331.20"),
                last=Decimal("3331.20"),
                currency="USD",
            ),
            "positions": [],
        },
        longSpread=Decimal("-0.70"),
        shortSpread=Decimal("-1.30"),
        metrics={},
    )
    _SNAPSHOT_CACHE["test"] = (1.0, snapshot)

    assert estimate_cached_fill_price(symbol="XAUTUSDT", side="buy") == Decimal("3330.30")
    assert estimate_cached_fill_price(symbol="XAUUSD+", side="sell") == Decimal("3331.00")

    gateway = FakeGateway()
    fill_price = gateway._estimate_market_fill_price(
        SubmitOrderCommand(
            command_id="cmd",
            platform_order_id="ord",
            account_id="account_crypto_test",
            instrument_id="instrument_xau_usdt_perp",
            symbol="XAUTUSDT",
            side="buy",
            order_type="market",
            quantity=Decimal("1"),
        )
    )
    assert fill_price == Decimal("3330.30")
