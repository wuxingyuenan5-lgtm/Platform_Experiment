from decimal import Decimal

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
