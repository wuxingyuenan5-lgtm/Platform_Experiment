from decimal import Decimal
from uuid import uuid4

from app.models import ExecutionEvent, SubmitOrderCommand


class FakeGateway:
    """Deterministic gateway used before connecting real venues."""

    name = "fake"

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        external_order_id = f"FAKE-{uuid4().hex[:12].upper()}"
        fill_price = command.price or Decimal("100")

        return [
            ExecutionEvent(
                event_id=str(uuid4()),
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_acknowledged",
                external_order_id=external_order_id,
            ),
            ExecutionEvent(
                event_id=str(uuid4()),
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_filled",
                external_order_id=external_order_id,
                fill_price=fill_price,
                fill_quantity=command.quantity,
            ),
        ]
