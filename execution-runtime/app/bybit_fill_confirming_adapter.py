from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from time import monotonic, sleep

from app.bybit_live_adapter import BybitLiveAdapter
from app.gateway_errors import (
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.live_route_store import (
    record_order_route,
    stable_external_client_id,
    update_external_order_id,
)
from app.live_safety import validate_live_write
from app.models import ExecutionEvent, SubmitOrderCommand, VenueOrderSnapshot

CROSS_SPREAD_STRATEGY_INSTANCE_ID = "strategy_cross_venue_spread_instance_default"


class BybitFillConfirmingAdapter(BybitLiveAdapter):
    """Bybit adapter with bounded terminal confirmation and close safeguards."""

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        events = self._submit_acknowledgement(command)
        is_fok = self._is_cross_spread_fok(command)
        if command.order_type != "market" and not is_fok:
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
                if is_fok and snapshot.filled_quantity != command.quantity:
                    acknowledgement.reason = (
                        "Bybit FOK order reported filled with a quantity mismatch; "
                        "MT5 hedge was not submitted pending reconciliation"
                    )
                    return events
                fill_event = self._fill_event(command, snapshot, partial=False)
                return [*events, fill_event] if fill_event is not None else events

            if snapshot.status == "canceled":
                if is_fok:
                    if snapshot.filled_quantity > 0:
                        acknowledgement.reason = (
                            "Bybit FOK order reached a terminal partial fill; "
                            "MT5 hedge was not submitted pending reconciliation"
                        )
                        return events
                    return [
                        *events,
                        ExecutionEvent(
                            event_id=f"BYBIT-REJECT-{external_order_id}",
                            command_id=command.command_id,
                            platform_order_id=command.platform_order_id,
                            event_type="order_rejected",
                            external_order_id=external_order_id,
                            occurred_at=snapshot.as_of,
                            reason="Bybit FOK limit order was not filled",
                        ),
                    ]
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
                order_label = "FOK limit" if is_fok else "market"
                return [
                    *events,
                    ExecutionEvent(
                        event_id=f"BYBIT-REJECT-{external_order_id}",
                        command_id=command.command_id,
                        platform_order_id=command.platform_order_id,
                        event_type="order_rejected",
                        external_order_id=external_order_id,
                        occurred_at=snapshot.as_of,
                        reason=f"Bybit rejected the {order_label} order after acknowledgement",
                    ),
                ]

            self._sleep_before_retry()

        if is_fok:
            if last_snapshot is not None and last_snapshot.filled_quantity > 0:
                acknowledgement.reason = (
                    "Bybit FOK order has a non-zero unresolved fill at confirmation timeout; "
                    "MT5 hedge was not submitted pending reconciliation"
                )
            else:
                acknowledgement.reason = "Bybit FOK limit-order confirmation timed out"
        elif last_snapshot is not None and last_snapshot.status == "partially_filled":
            acknowledgement.reason = (
                "Bybit market order remained partially filled at confirmation timeout; "
                "MT5 hedge was not submitted because the remaining Bybit quantity is unresolved"
            )
        else:
            acknowledgement.reason = "Bybit market-order fill confirmation timed out"
        return events

    def _submit_acknowledgement(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        self._assert_account(command.account_id)
        client = self._client()
        reference_price = command.price or self._market_reference_price(client, command)
        validate_live_write(
            command,
            adapter=self.name,
            reference_price=reference_price,
            settings=self.settings,
        )
        client_id = stable_external_client_id("VG", command.platform_order_id, length=36)
        record_order_route(command, self.name, client_id)
        payload: dict[str, object] = {
            "category": self.settings.bybit_category,
            "symbol": command.symbol.upper(),
            "side": "Buy" if command.side == "buy" else "Sell",
            "orderType": "Market" if command.order_type == "market" else "Limit",
            "qty": format(command.quantity, "f"),
            "orderLinkId": client_id,
            "reduceOnly": command.reduce_only,
        }
        if command.reduce_only:
            payload["positionIdx"] = self._resolve_reduce_position_idx(client, command)
        if command.order_type == "limit":
            if command.price is None:
                raise GatewayRequestRejectedError("Bybit limit order requires price")
            payload["price"] = format(command.price, "f")
            payload["timeInForce"] = "FOK" if self._is_cross_spread_fok(command) else "GTC"
        try:
            response = client.place_order(**payload)
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit place_order result is unknown") from exc
        self._require_success(response, "Bybit rejected order")
        result = response.get("result") or {}
        external_order_id = str(result.get("orderId") or "")
        if not external_order_id:
            raise GatewayResultUnknownError("Bybit accepted order without orderId")
        update_external_order_id(command.platform_order_id, external_order_id)
        return [
            ExecutionEvent(
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_acknowledged",
                external_order_id=external_order_id,
                occurred_at=datetime.now(UTC),
            )
        ]

    def _resolve_reduce_position_idx(self, client, command: SubmitOrderCommand) -> int:
        try:
            response = client.get_positions(
                category=self.settings.bybit_category,
                symbol=command.symbol.upper(),
            )
            self._require_success(response, "Bybit position query failed before close")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError(
                "Bybit close-position query result is unknown"
            ) from exc

        required_side = "Buy" if command.side == "sell" else "Sell"
        matches = []
        for row in self._result_list(response):
            size = Decimal(str(row.get("size") or "0"))
            if size <= 0 or str(row.get("side") or "") != required_side:
                continue
            matches.append((row, size))
        if len(matches) != 1:
            raise GatewayRequestRejectedError(
                "Bybit reduce-only close requires exactly one matching live position"
            )
        row, size = matches[0]
        if command.quantity > size:
            raise GatewayRequestRejectedError(
                "Bybit reduce-only close quantity exceeds the matching live position"
            )
        return int(row.get("positionIdx") or 0)

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

    def _is_cross_spread_fok(self, command: SubmitOrderCommand) -> bool:
        return (
            command.order_type == "limit"
            and command.strategy_instance_id == CROSS_SPREAD_STRATEGY_INSTANCE_ID
        )

    def _sleep_before_retry(self) -> None:
        interval = self.settings.bybit_fill_confirmation_poll_seconds
        if interval > 0:
            sleep(interval)
