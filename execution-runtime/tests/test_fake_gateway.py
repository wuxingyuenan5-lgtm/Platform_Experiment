import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

from app.config import get_settings
from app.fake_gateway import FakeGateway
from app.models import InternalCapitalTransferStepCommand, SubmitOrderCommand


def test_fake_gateway_acknowledges_and_fills() -> None:
    command = SubmitOrderCommand(
        command_id="command-1",
        platform_order_id="order-1",
        account_id="account-1",
        instrument_id="instrument-1",
        symbol="BTCUSDT",
        side="buy",
        quantity=Decimal("0.01"),
        price=Decimal("65000"),
    )

    events = FakeGateway().submit_order(command)

    assert [event.event_type for event in events] == [
        "order_acknowledged",
        "order_filled",
    ]
    assert events[1].fill_price == Decimal("65000")
    assert events[1].fill_quantity == Decimal("0.01")


def test_fake_gateway_uses_cross_spread_balance_seeds_for_test_accounts(tmp_path) -> None:
    settings = get_settings()
    settings.journal_path = str(tmp_path / "fake-balance-seeds.db")

    gateway = FakeGateway()

    cross_spread_balances = gateway.list_balances("account_crypto_test")
    mt5_balances = gateway.list_balances("account_mt5_demo")

    assert cross_spread_balances[0].equity == Decimal("500")
    assert cross_spread_balances[0].available_balance == Decimal("500")
    assert mt5_balances[0].equity == Decimal("500")
    assert mt5_balances[0].available_balance == Decimal("500")


def test_fake_gateway_internal_capital_transfer_is_bidirectional_and_idempotent(
    tmp_path,
) -> None:
    settings = get_settings()
    settings.journal_path = str(tmp_path / "fake-capital-transfer.db")
    gateway = FakeGateway()

    forward = InternalCapitalTransferStepCommand(
        idempotencyKey="forward-1",
        sourceAccountId="account_crypto_test",
        destinationAccountId="fake:bybit-funding",
        sourceCurrency="USDT",
        destinationCurrency="USDT",
        amount="125.25",
    )
    first = gateway.transfer_internal_capital(forward)
    replay = gateway.transfer_internal_capital(forward)
    gateway.transfer_internal_capital(
        InternalCapitalTransferStepCommand(
            idempotencyKey="forward-2",
            sourceAccountId="fake:bybit-funding",
            destinationAccountId="account_mt5_demo",
            sourceCurrency="USDT",
            destinationCurrency="USD",
            amount="125.25",
        )
    )
    gateway.transfer_internal_capital(
        InternalCapitalTransferStepCommand(
            idempotencyKey="reverse-1",
            sourceAccountId="account_mt5_demo",
            destinationAccountId="fake:bybit-funding",
            sourceCurrency="USD",
            destinationCurrency="USDT",
            amount="25.25",
        )
    )
    gateway.transfer_internal_capital(
        InternalCapitalTransferStepCommand(
            idempotencyKey="reverse-2",
            sourceAccountId="fake:bybit-funding",
            destinationAccountId="account_crypto_test",
            sourceCurrency="USDT",
            destinationCurrency="USDT",
            amount="25.25",
        )
    )

    assert replay == first
    assert gateway.list_balances("account_crypto_test")[0].available_balance == Decimal("400")
    assert gateway.list_balances("account_mt5_demo")[0].available_balance == Decimal("600")
    assert gateway.list_balances("fake:bybit-funding")[0].available_balance == Decimal("100000")


def test_fake_gateway_scripted_limit_order_can_stay_open_until_cancel_terminal(tmp_path) -> None:
    settings = get_settings()
    settings.journal_path = str(tmp_path / "fake-scripted-open.db")
    with sqlite3.connect(settings.journal_path) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS fake_venue_order_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                behavior TEXT NOT NULL,
                partial_fill_quantity TEXT,
                partial_fill_price TEXT,
                cancel_terminal_after_queries INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                consumed_at TEXT
            )
            """
        )
        db.execute(
            """
            INSERT INTO fake_venue_order_scripts (
                symbol, behavior, partial_fill_quantity, partial_fill_price,
                cancel_terminal_after_queries, created_at, consumed_at
            ) VALUES ('BTCUSDT', 'accepted_no_fill', NULL, NULL, 1, ?, NULL)
            """,
            (datetime.now(UTC).isoformat(),),
        )

    gateway = FakeGateway()
    events = gateway.submit_order(
        SubmitOrderCommand(
            command_id="command-open-1",
            platform_order_id="order-open-1",
            account_id="account-1",
            instrument_id="instrument-1",
            symbol="BTCUSDT",
            side="sell",
            order_type="limit",
            quantity=Decimal("1"),
            price=Decimal("100.1"),
        )
    )
    assert [event.event_type for event in events] == ["order_acknowledged"]

    first = gateway.get_order(platform_order_id="order-open-1")
    assert first is not None and first.status == "accepted"
    cancel = gateway.cancel_order(first.external_order_id, "cancel-script-1", "test")
    assert cancel.status == "canceled"
    after_ack = gateway.get_order(platform_order_id="order-open-1")
    assert after_ack is not None and after_ack.status == "accepted"
    after_terminal = gateway.get_order(platform_order_id="order-open-1")
    assert after_terminal is not None and after_terminal.status == "canceled"


def test_fake_gateway_scripted_partial_fill_and_quote_query(tmp_path) -> None:
    settings = get_settings()
    settings.journal_path = str(tmp_path / "fake-scripted-partial.db")
    with sqlite3.connect(settings.journal_path) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS fake_venue_order_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                behavior TEXT NOT NULL,
                partial_fill_quantity TEXT,
                partial_fill_price TEXT,
                cancel_terminal_after_queries INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                consumed_at TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS fake_venue_quotes (
                symbol TEXT PRIMARY KEY,
                bid TEXT NOT NULL,
                ask TEXT NOT NULL,
                last TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            INSERT INTO fake_venue_order_scripts (
                symbol, behavior, partial_fill_quantity, partial_fill_price,
                cancel_terminal_after_queries, created_at, consumed_at
            ) VALUES ('BTCUSDT', 'partial_fill', '0.4', '100.1', 0, ?, NULL)
            """,
            (datetime.now(UTC).isoformat(),),
        )
        db.execute(
            """
            INSERT INTO fake_venue_quotes(symbol, bid, ask, last, updated_at)
            VALUES ('BTCUSDT', '100', '100.1', '100.05', ?)
            """,
            (datetime.now(UTC).isoformat(),),
        )

    gateway = FakeGateway()
    events = gateway.submit_order(
        SubmitOrderCommand(
            command_id="command-partial-1",
            platform_order_id="order-partial-1",
            account_id="account-1",
            instrument_id="instrument-1",
            symbol="BTCUSDT",
            side="sell",
            order_type="limit",
            quantity=Decimal("1"),
            price=Decimal("100.1"),
        )
    )
    assert [event.event_type for event in events] == ["order_acknowledged"]
    order = gateway.get_order(platform_order_id="order-partial-1")
    assert order is not None
    assert order.status == "partially_filled"
    assert order.filled_quantity == Decimal("0.4")
    fills = gateway.list_fills(platform_order_id="order-partial-1")
    assert len(fills) == 1
    assert fills[0].quantity == Decimal("0.4")
    quote = gateway.get_market_quote(account_id="account-1", symbol="BTCUSDT")
    assert quote.bid == Decimal("100")
    assert quote.ask == Decimal("100.1")
