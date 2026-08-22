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
