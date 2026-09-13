from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier

import pytest

from app.cross_spread_market import (
    _SNAPSHOT_CACHE,
    build_cross_spread_snapshot,
    estimate_cached_fill_price,
)
from app.fake_gateway import FakeGateway
from app.models import (
    CrossSpreadSnapshotResponse,
    MarketQuote,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueMarketQuoteSnapshot,
    VenuePositionSnapshot,
)


class ReadGateway:
    name = "isolated"

    def __init__(self):
        self.calls = []
        self.observed = datetime.now(UTC) - timedelta(seconds=2)
        self.fail_positions = False
        self.wrong_account = False
        self.barrier = None

    def get_market_quote(self, *, account_id, symbol, category=None):
        self.calls.append(("quote", account_id))
        if self.barrier:
            self.barrier.wait()
        bybit = account_id.startswith("bybit")
        bid, ask = ("3330.10", "3330.30") if bybit else ("3331.0", "3331.4")
        return VenueMarketQuoteSnapshot(
            source="test",
            accountId="wrong" if self.wrong_account else account_id,
            instrumentType="crypto_perp" if bybit else "mt5_contract",
            category=category,
            symbol=symbol,
            bid=bid,
            ask=ask,
            mid=(Decimal(bid) + Decimal(ask)) / 2,
            last=(Decimal(bid) + Decimal(ask)) / 2,
            currency="USDT" if bybit else "USD",
            asOf=self.observed,
            fundingRate="0.0001" if bybit else None,
            rawPayload={}
            if bybit
            else {"swap_long": "-78.29", "swap_short": "29.49", "trade_contract_size": "100"},
        )

    def get_positions(self, account_id):
        self.calls.append(("positions", account_id))
        if self.fail_positions:
            raise RuntimeError("position endpoint rejected")
        bybit = account_id.startswith("bybit")
        return [
            VenuePositionSnapshot(
                source="test",
                accountId=account_id,
                externalPositionId="bybit-position" if bybit else "123",
                instrumentId="test",
                symbol="XAUTUSDT" if bybit else "XAUUSD+",
                instrumentType="crypto_perp" if bybit else "mt5_contract",
                category="linear" if bybit else "mt5",
                netQuantity="2.5" if bybit else "-0.25",
                averagePrice="3328",
                unrealizedPnl="5.5",
                currency="USDT" if bybit else "EUR",
                asOf=self.observed,
            )
        ]

    def list_balances(self, account_id):
        self.calls.append(("balances", account_id))
        if self.barrier:
            self.barrier.wait()
        return [
            VenueBalanceSnapshot(
                source="test",
                externalBalanceId="balance",
                accountId=account_id,
                currency="USDT",
                equity="100",
                usdValue="99.9",
                asOf=self.observed,
            )
        ]


def snapshot(gateway, bybit="bybit-1"):
    return build_cross_spread_snapshot(
        gateway=gateway,
        bybit_account_id=bybit,
        mt5_account_id="mt5-1",
        bybit_symbol="XAUTUSDT",
        mt5_symbol="XAUUSD+",
    )


def test_shared_gateway_supplies_quotes_positions_swap_and_valuation():
    gateway = ReadGateway()
    result = snapshot(gateway)
    assert result.status == "available"
    assert result.long_spread == Decimal("-0.70")
    assert result.short_spread == Decimal("-1.30")
    assert result.bybit.positions[0].quantity == Decimal("2.5")
    assert result.mt5.positions[0].quantity == Decimal("-0.25")
    assert result.mt5.positions[0].external_id == "123"
    assert result.mt5.positions[0].account_id == "mt5-1"
    assert result.mt5.positions[0].currency == "EUR"
    assert result.mt5.positions[0].as_of == gateway.observed
    assert result.mt5.quote.currency == "USD"  # Price currency; PnL account is EUR.
    assert result.mt5.quote_source_as_of is None
    assert result.metrics.funding_rate == Decimal("0.0001")
    assert result.metrics.buyer_inventory_fee == Decimal("-78.29")
    assert result.metrics.seller_inventory_fee == Decimal("29.49")
    assert result.metrics.usdt_usd == Decimal("0.999")
    assert result.execution_state == "monitor_only"
    assert result.mt5.open_allowed is False
    assert sorted(gateway.calls) == sorted(
        [
            ("quote", "bybit-1"),
            ("positions", "bybit-1"),
            ("quote", "mt5-1"),
            ("positions", "mt5-1"),
            ("balances", "bybit-1"),
        ]
    )


def test_market_reads_run_concurrently_and_cached_read_preserves_observation():
    gateway = ReadGateway()
    gateway.barrier = Barrier(3, timeout=3)
    result = snapshot(gateway)
    cached = snapshot(gateway)
    assert cached is result
    assert len(gateway.calls) == 5
    assert result.bybit.as_of == gateway.observed
    assert result.mt5.as_of == gateway.observed
    assert result.bybit.fetch_latency_ms is not None
    assert result.mt5.fetch_latency_ms is not None


def test_cache_is_scoped_to_gateway_and_accounts():
    first = ReadGateway()
    second = ReadGateway()
    assert snapshot(first) is not snapshot(second)
    assert snapshot(first) is not snapshot(first, "bybit-2")


def test_position_failure_keeps_the_available_quote():
    gateway = ReadGateway()
    gateway.fail_positions = True
    result = snapshot(gateway)
    assert result.bybit.quote is not None
    assert result.bybit.positions == []
    assert "position endpoint rejected" in result.bybit.reason


def test_cross_exposes_executable_only_when_both_venues_have_fresh_native_evidence():
    gateway = ReadGateway()
    gateway.observed = datetime.now(UTC) - timedelta(seconds=1)
    original = gateway.get_market_quote

    def quote_with_evidence(*, account_id, symbol, category=None):
        quote = original(account_id=account_id, symbol=symbol, category=category)
        if account_id.startswith("bybit"):
            quote.raw_payload = {"serverTime": "fresh"}
            quote.source_as_of = datetime.now(UTC)
        else:
            quote.raw_payload = {
                "tradeMode": 4,
                "accountTradeAllowed": True,
                "terminalTradeAllowed": True,
                "accountExpertTradeAllowed": True,
                "pythonTradeAllowed": True,
                "symbolVisible": True,
            }
            quote.source_as_of = datetime.now(UTC)
        return quote

    gateway.get_market_quote = quote_with_evidence
    result = snapshot(gateway)
    assert result.execution_state == "executable"
    assert result.bybit.open_allowed and result.bybit.close_allowed
    assert result.mt5.open_allowed and result.mt5.close_allowed


def test_cross_keeps_stale_quotes_for_monitoring_but_blocks_execution():
    gateway = ReadGateway()
    gateway.observed = datetime.now(UTC) - timedelta(seconds=90)
    original = gateway.get_market_quote

    def quote_with_evidence(*, account_id, symbol, category=None):
        quote = original(account_id=account_id, symbol=symbol, category=category)
        quote.raw_payload = (
            {"serverTime": "stale"}
            if account_id.startswith("bybit")
            else {
                "tradeMode": 4,
                "accountTradeAllowed": True,
                "terminalTradeAllowed": True,
                "accountExpertTradeAllowed": True,
                "pythonTradeAllowed": True,
                "symbolVisible": True,
            }
        )
        quote.source_as_of = gateway.observed
        return quote

    gateway.get_market_quote = quote_with_evidence
    result = snapshot(gateway)
    assert result.execution_state == "monitor_only"
    assert result.bybit.quote is not None and result.mt5.quote is not None
    assert result.bybit.execution_block_reason == "quote_stale"
    assert result.mt5.execution_block_reason == "quote_stale"


def test_mt5_close_only_allows_close_but_not_open():
    gateway = ReadGateway()
    gateway.observed = datetime.now(UTC) - timedelta(seconds=1)
    original = gateway.get_market_quote

    def quote_with_close_only(*, account_id, symbol, category=None):
        quote = original(account_id=account_id, symbol=symbol, category=category)
        quote.source_as_of = datetime.now(UTC)
        quote.raw_payload = (
            {"serverTime": "fresh"}
            if account_id.startswith("bybit")
            else {
                "tradeMode": 3,
                "accountTradeAllowed": True,
                "terminalTradeAllowed": True,
                "accountExpertTradeAllowed": True,
                "pythonTradeAllowed": True,
                "symbolVisible": True,
            }
        )
        return quote

    gateway.get_market_quote = quote_with_close_only
    result = snapshot(gateway)
    assert result.mt5.open_allowed is False
    assert result.mt5.close_allowed is True
    assert result.execution_state == "monitor_only"


@pytest.mark.parametrize(
    ("permission", "expected_reason"),
    [
        ("accountExpertTradeAllowed", "mt5_expert_trade_not_allowed"),
        ("pythonTradeAllowed", "mt5_python_trade_not_allowed"),
    ],
)
def test_mt5_permission_evidence_blocks_cross_execution(permission, expected_reason):
    gateway = ReadGateway()
    gateway.observed = datetime.now(UTC) - timedelta(seconds=1)
    original = gateway.get_market_quote

    def quote_with_permission(*, account_id, symbol, category=None):
        quote = original(account_id=account_id, symbol=symbol, category=category)
        quote.source_as_of = datetime.now(UTC)
        quote.raw_payload = {
            "tradeMode": 4,
            "accountTradeAllowed": True,
            "terminalTradeAllowed": True,
            "accountExpertTradeAllowed": True,
            "pythonTradeAllowed": True,
            "symbolVisible": True,
        }
        if account_id.startswith("bybit"):
            quote.raw_payload = {"serverTime": "fresh"}
        elif permission:
            quote.raw_payload[permission] = False
        return quote

    gateway.get_market_quote = quote_with_permission
    result = snapshot(gateway)
    assert result.execution_state == "monitor_only"
    assert result.mt5.execution_block_reason == expected_reason


def test_wrong_account_quote_is_never_published():
    gateway = ReadGateway()
    gateway.wrong_account = True
    result = snapshot(gateway)
    assert result.status == "unavailable"
    assert result.bybit.quote is None and result.mt5.quote is None


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
