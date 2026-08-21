from decimal import Decimal

from app.config import get_settings
from app.fake_gateway import FakeGateway
from app.models import SubmitOrderCommand


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
