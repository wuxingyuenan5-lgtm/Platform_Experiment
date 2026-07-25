from __future__ import annotations

from time import monotonic, sleep

from app.bybit_live_adapter import BybitLiveAdapter
from app.gateway_errors import GatewayResultUnknownError
from app.models import ExecutionEvent, SubmitOrderCommand, VenueOrderSnapshot


class BybitFillConfirmingAdapter(BybitLiveAdapter):
    """Bybit adapter that turns a terminal market-order fill into Runtime fill events.

    REST acknowledgement alone is never treated as a fill. The adapter performs a
    bounded confirmation loop so the cross-spread batch can submit the MT5 hedge
    only after Bybit exposes a terminal filled quantity.
    """

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        events = super().submit_order(command)
        if command.order_type != "market":
            return events

        acknowledgement = events[0]
        external_order_id = acknowledgement.external_order_id
        if not external_order_id:
            acknowledgement.reason = "Bybit acknowledgement did not include an order id"
            return events

        deadline = monotonic() + self.settings.bybit_fill_confirmation_timeout_seconds
        last_snapshot: VenueOrderSnapshot | None = None

        while monotonic() <= deadline:
            try:
                snapshot = self.get_order(platform_order_id=command.platform_order_id)
            except GatewayResultUnknownError as exc:
                acknowledgement.reason = f"Bybit fill confirmation result is unknown: {exc}"
                return events

            if snapshot is None:
                self._sleep_before_retry()
                continue

            last_snapshot = snapshot
            if snapshot.status == "filled":
                fill_event = self._fill_event(command, snapshot, partial=False)
                return [*events, fill_event] if fill_event is not None else events

            if snapshot.status == "canceled":
                if snapshot.filled_quantity > 0:
                    fill_event = self._fill_event(command, snapshot, partial=True)
                    return [*events, fill_event] if fill_event is not None else events
                return [
                    *events,
                    ExecutionEvent(
                        event_id=f"BYBIT-REJECT-{external_order_id}",
                        command_id=command.command_id,
                        platform_order_id=command.platform_order_id,
                        event_type="order_rejected",
                        external_order_id=external_order_id,
                        occurred_at=snapshot.as_of,
                        reason="Bybit market order canceled without a fill",
                    ),
                ]

            if snapshot.status == "rejected":
                return [
                    *events,
                    ExecutionEvent(
                        event_id=f"BYBIT-REJECT-{external_order_id}",
                        command_id=command.command_id,
                        platform_order_id=command.platform_order_id,
                        event_type="order_rejected",
                        external_order_id=external_order_id,
                        occurred_at=snapshot.as_of,
                        reason="Bybit rejected the market order after acknowledgement",
                    ),
                ]

            self._sleep_before_retry()

        if last_snapshot is not None and last_snapshot.status == "partially_filled":
            acknowledgement.reason = (
                "Bybit market order remained partially filled at confirmation timeout; "
                "MT5 hedge was not submitted because the remaining Bybit quantity is unresolved"
            )
        else:
            acknowledgement.reason = "Bybit market-order fill confirmation timed out"
        return events

    def _fill_event(
        self,
        command: SubmitOrderCommand,
        snapshot: VenueOrderSnapshot,
        *,
        partial: bool,
    ) -> ExecutionEvent | None:
        if snapshot.filled_quantity <= 0 or snapshot.average_fill_price is None:
            return None
        reason = None
        if partial:
            reason = (
                "Bybit market order reached a terminal partial fill; "
                f"hedge only the confirmed {snapshot.filled_quantity} quantity"
            )
        return ExecutionEvent(
            event_id=f"BYBIT-FILL-{snapshot.external_order_id}",
            command_id=command.command_id,
            platform_order_id=command.platform_order_id,
            event_type="order_filled",
            external_order_id=snapshot.external_order_id,
            fill_price=snapshot.average_fill_price,
            fill_quantity=snapshot.filled_quantity,
            occurred_at=snapshot.as_of,
            reason=reason,
        )

    def _sleep_before_retry(self) -> None:
        interval = self.settings.bybit_fill_confirmation_poll_seconds
        if interval > 0:
            sleep(interval)
