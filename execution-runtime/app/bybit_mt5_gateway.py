from __future__ import annotations

from uuid import uuid4

from app.models import ExecutionEvent, SubmitOrderCommand


class BybitMt5Gateway:
    """Controlled V1 gateway shell for cross-venue market-order execution."""

    name = "bybit_mt5"

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        if command.order_type != "market":
            return [self._reject(command, "Bybit/MT5 V1 only supports market orders")]

        return [
            self._reject(
                command,
                "Bybit/MT5 live adapter is not connected; configure credentials first",
            )
        ]

    def _reject(self, command: SubmitOrderCommand, reason: str) -> ExecutionEvent:
        return ExecutionEvent(
            event_id=str(uuid4()),
            command_id=command.command_id,
            platform_order_id=command.platform_order_id,
            event_type="order_rejected",
            reason=reason,
        )
