from decimal import Decimal
from uuid import uuid4

from app.fake_gateway import FakeGateway
from app.models import SubmitOrderCommand


def test_fake_gateway_acknowledges_and_fills() -> None:
    command = SubmitOrderCommand(
        command_id=uuid4(),
        platform_order_id=uuid4(),
        account_id=uuid4(),
        instrument_id=uuid4(),
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
