from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueFillSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)


class BybitMt5Gateway:
    """Controlled shell; real Demo adapters are implemented in Phase 4C."""

    name = "bybit_mt5"

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        if command.order_type != "market":
            return [self._reject(command, "Bybit/MT5 V1 only supports market orders")]
        return [
            self._reject(
                command,
                "Bybit/MT5 Demo adapter is not connected; Phase 4C credentials are required",
            )
        ]

    def get_order(
        self,
        *,
        platform_order_id: str | None = None,
        external_order_id: str | None = None,
    ) -> VenueOrderSnapshot | None:
        return None

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        return []

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        return []

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        return []

    def cancel_order(
        self,
        external_order_id: str,
        idempotency_key: str,
        reason: str | None,
    ) -> CancelOrderResponse:
        return CancelOrderResponse(
            source=self.name,
            externalOrderId=external_order_id,
            platformOrderId="unknown",
            status="unsupported",
            reason="External cancellation is not available until Phase 4C",
            asOf=datetime.now(UTC),
        )

    def _reject(self, command: SubmitOrderCommand, reason: str) -> ExecutionEvent:
        return ExecutionEvent(
            event_id=str(uuid4()),
            command_id=command.command_id,
            platform_order_id=command.platform_order_id,
            event_type="order_rejected",
            reason=reason,
        )
