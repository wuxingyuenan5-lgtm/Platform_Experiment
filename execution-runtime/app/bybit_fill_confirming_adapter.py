from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from time import monotonic, sleep
from typing import Any

from app.bybit_live_adapter import BybitLiveAdapter
from app.bybit_postonly_chase import (
    ChaseAction,
    ChaseActionType,
    ChasePolicy,
    ChaseState,
    ChaseStatus,
    apply_private_event,
    next_quote_action,
    request_cancel_repost,
)
from app.bybit_private_stream import (
    BybitPrivateEventSource,
    PrivateEventSource,
)
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
PrivateSourceFactory = Callable[[str, str], PrivateEventSource]


class BybitFillConfirmingAdapter(BybitLiveAdapter):
    """Bybit adapter with bounded terminal confirmation and close safeguards."""

    def __init__(
        self,
        settings,
        client: Any | None = None,
        private_source_factory: PrivateSourceFactory | None = None,
    ) -> None:
        super().__init__(settings, client)
        self._private_source_factory = private_source_factory

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        if self._is_postonly_chase(command):
            return self._submit_postonly_chase(command)

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
                        self._rejected_event(
                            command,
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
                    self._rejected_event(
                        command,
                        external_order_id=external_order_id,
                        occurred_at=snapshot.as_of,
                        reason="Bybit market order canceled without a fill",
                    ),
                ]

            if snapshot.status == "rejected":
                order_label = "FOK limit" if is_fok else "market"
                return [
                    *events,
                    self._rejected_event(
                        command,
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

    def _submit_postonly_chase(
        self,
        command: SubmitOrderCommand,
    ) -> list[ExecutionEvent]:
        if not self.settings.bybit_postonly_chase_enabled:
            raise GatewayRequestRejectedError("Bybit PostOnly Chase is disabled")
        if command.price is None:
            raise GatewayRequestRejectedError("Bybit PostOnly Chase requires a hard limit price")

        self._assert_account(command.account_id)
        client = self._client(command.account_id)
        validate_live_write(
            command,
            adapter=self.name,
            reference_price=command.price,
            settings=self.settings,
        )
        tick_size = self._postonly_tick_size(client, command.symbol)
        best_bid, best_ask = self._postonly_quote(client, command.symbol)
        policy = ChasePolicy(
            ttl_seconds=self.settings.bybit_postonly_chase_ttl_seconds,
            min_amend_ticks=self.settings.bybit_postonly_chase_min_amend_ticks,
            max_mutations=self.settings.bybit_postonly_chase_max_mutations,
            cooldown_seconds=self.settings.bybit_postonly_chase_cooldown_seconds,
        )
        policy.validate()

        order_link_prefix = stable_external_client_id(
            "VGP",
            command.platform_order_id,
            length=28,
        )
        source = self._private_source(command.symbol, order_link_prefix)
        source.start()
        state = ChaseState(
            side=command.side,
            requested_quantity=command.quantity,
            hard_limit_price=command.price,
            tick_size=tick_size,
            started_at=datetime.now(UTC),
        )
        acknowledgement: ExecutionEvent | None = None
        child_index = 0
        reconcile_deadline: float | None = None

        try:
            transition = next_quote_action(
                state,
                policy,
                best_bid=best_bid,
                best_ask=best_ask,
                now=datetime.now(UTC),
            )
            state = transition.state
            for action in transition.actions:
                if action.action_type != ChaseActionType.REPOST or action.price is None:
                    raise GatewayResultUnknownError(
                        "PostOnly Chase did not produce an initial maker order"
                    )
                child_index += 1
                external_order_id, client_id = self._place_postonly_child(
                    client,
                    command,
                    price=action.price,
                    order_link_prefix=order_link_prefix,
                    child_index=child_index,
                    record_route=True,
                )
                state = replace(
                    state,
                    active_order_id=external_order_id,
                    active_price=action.price,
                )
                acknowledgement = ExecutionEvent(
                    command_id=command.command_id,
                    platform_order_id=command.platform_order_id,
                    event_type="order_acknowledged",
                    external_order_id=external_order_id,
                    occurred_at=datetime.now(UTC),
                    reason=f"Bybit PostOnly Chase started with {client_id}",
                )

            while state.status not in {
                ChaseStatus.FILLED,
                ChaseStatus.UNFILLED,
                ChaseStatus.MANUAL_STOPPED,
                ChaseStatus.RECONCILE_REQUIRED,
            }:
                private_event = source.next_event(
                    self.settings.bybit_postonly_chase_event_timeout_seconds
                )
                if private_event is not None:
                    transition = apply_private_event(state, private_event)
                    state = transition.state
                    for action in transition.actions:
                        state, child_index = self._execute_chase_action(
                            client,
                            command,
                            state,
                            action,
                            order_link_prefix=order_link_prefix,
                            child_index=child_index,
                            policy=policy,
                        )
                    if state.status == ChaseStatus.FILLED:
                        return self._postonly_full_fill_events(
                            command,
                            state,
                            acknowledgement,
                        )
                    if state.status == ChaseStatus.RECONCILE_REQUIRED:
                        break
                    continue

                best_bid, best_ask = self._postonly_quote(client, command.symbol)
                transition = next_quote_action(
                    state,
                    policy,
                    best_bid=best_bid,
                    best_ask=best_ask,
                    now=datetime.now(UTC),
                )
                state = transition.state
                for action in transition.actions:
                    state, child_index = self._execute_chase_action(
                        client,
                        command,
                        state,
                        action,
                        order_link_prefix=order_link_prefix,
                        child_index=child_index,
                        policy=policy,
                    )
                if state.status == ChaseStatus.CANCEL_PENDING:
                    reconcile_deadline = (
                        monotonic()
                        + self.settings.bybit_postonly_chase_rest_reconcile_seconds
                    )
                if reconcile_deadline is not None and monotonic() >= reconcile_deadline:
                    break

            return self._reconcile_postonly_terminal(
                command,
                state,
                acknowledgement,
            )
        finally:
            source.close()

    def _execute_chase_action(
        self,
        client,
        command: SubmitOrderCommand,
        state: ChaseState,
        action: ChaseAction,
        *,
        order_link_prefix: str,
        child_index: int,
        policy: ChasePolicy,
    ) -> tuple[ChaseState, int]:
        if action.action_type == ChaseActionType.AMEND:
            if state.active_order_id is None or action.price is None:
                return self._reconcile_state(state, "PostOnly amend identity is unavailable"), child_index
            try:
                response = client.amend_order(
                    category=self.settings.bybit_category,
                    symbol=command.symbol.upper(),
                    orderId=state.active_order_id,
                    price=format(action.price, "f"),
                )
                self._require_success(response, "Bybit rejected PostOnly amend")
                return state, child_index
            except GatewayRequestRejectedError:
                transition = request_cancel_repost(
                    state,
                    policy,
                    replacement_price=action.price,
                    now=datetime.now(UTC),
                )
                next_state = transition.state
                for fallback in transition.actions:
                    next_state, child_index = self._execute_chase_action(
                        client,
                        command,
                        next_state,
                        fallback,
                        order_link_prefix=order_link_prefix,
                        child_index=child_index,
                        policy=policy,
                    )
                return next_state, child_index
            except Exception:
                return self._reconcile_state(
                    state,
                    "Bybit PostOnly amend result is unknown",
                ), child_index

        if action.action_type == ChaseActionType.CANCEL:
            if state.active_order_id is None:
                return self._reconcile_state(state, "PostOnly cancel identity is unavailable"), child_index
            try:
                response = client.cancel_order(
                    category=self.settings.bybit_category,
                    symbol=command.symbol.upper(),
                    orderId=state.active_order_id,
                )
                self._require_success(response, "Bybit rejected PostOnly cancel")
                return state, child_index
            except Exception:
                return self._reconcile_state(
                    state,
                    "Bybit PostOnly cancel result is unknown",
                ), child_index

        if action.action_type == ChaseActionType.REPOST:
            if action.price is None:
                return self._reconcile_state(state, "PostOnly repost price is unavailable"), child_index
            child_index += 1
            try:
                external_order_id, _client_id = self._place_postonly_child(
                    client,
                    command,
                    price=action.price,
                    order_link_prefix=order_link_prefix,
                    child_index=child_index,
                    record_route=False,
                )
            except Exception:
                return self._reconcile_state(
                    state,
                    "Bybit PostOnly repost result is unknown",
                ), child_index
            return replace(
                state,
                status=ChaseStatus.ACTIVE,
                active_order_id=external_order_id,
                active_price=action.price,
            ), child_index
        return state, child_index

    def _place_postonly_child(
        self,
        client,
        command: SubmitOrderCommand,
        *,
        price: Decimal,
        order_link_prefix: str,
        child_index: int,
        record_route: bool,
    ) -> tuple[str, str]:
        client_id = f"{order_link_prefix}-{child_index}"
        if len(client_id) > 36:
            raise GatewayRequestRejectedError("Bybit PostOnly child identity is too long")
        if record_route:
            record_order_route(command, self.name, client_id)
        payload: dict[str, object] = {
            "category": self.settings.bybit_category,
            "symbol": command.symbol.upper(),
            "side": "Buy" if command.side == "buy" else "Sell",
            "orderType": "Limit",
            "qty": format(command.quantity, "f"),
            "price": format(price, "f"),
            "timeInForce": "PostOnly",
            "orderLinkId": client_id,
            "reduceOnly": command.reduce_only,
        }
        if command.reduce_only:
            payload["positionIdx"] = self._resolve_reduce_position_idx(client, command)
        try:
            response = client.place_order(**payload)
        except Exception as exc:
            raise self._unknown_error(
                "Bybit PostOnly place_order result is unknown",
                exc,
            ) from exc
        self._require_success(response, "Bybit rejected PostOnly order")
        result = response.get("result") or {}
        external_order_id = str(result.get("orderId") or "")
        if not external_order_id:
            raise GatewayResultUnknownError("Bybit accepted PostOnly order without orderId")
        update_external_order_id(command.platform_order_id, external_order_id)
        return external_order_id, client_id

    def _postonly_full_fill_events(
        self,
        command: SubmitOrderCommand,
        state: ChaseState,
        acknowledgement: ExecutionEvent | None,
    ) -> list[ExecutionEvent]:
        if acknowledgement is None or state.active_order_id is None:
            raise GatewayResultUnknownError("PostOnly acknowledgement identity is unavailable")
        if (
            state.cumulative_fill != command.quantity
            or state.average_fill_price is None
        ):
            acknowledgement.reason = (
                "Bybit PostOnly cumulative fill is not exact; "
                "MT5 hedge was not submitted pending reconciliation"
            )
            return [acknowledgement]
        return [
            acknowledgement,
            ExecutionEvent(
                event_id=f"BYBIT-POSTONLY-FILL-{command.platform_order_id}",
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_filled",
                external_order_id=state.active_order_id,
                fill_price=state.average_fill_price,
                fill_quantity=state.cumulative_fill,
                occurred_at=datetime.now(UTC),
                reason="Bybit PostOnly Chase reached an exact full fill",
            ),
        ]

    def _reconcile_postonly_terminal(
        self,
        command: SubmitOrderCommand,
        state: ChaseState,
        acknowledgement: ExecutionEvent | None,
    ) -> list[ExecutionEvent]:
        if acknowledgement is None:
            raise GatewayResultUnknownError("PostOnly order was not acknowledged")
        try:
            snapshot = self.get_order(platform_order_id=command.platform_order_id)
        except GatewayResultUnknownError as exc:
            acknowledgement.reason = f"PostOnly reconciliation is unknown: {exc}"
            return [acknowledgement]
        if snapshot is not None and snapshot.status == "filled":
            if (
                snapshot.filled_quantity == command.quantity
                and snapshot.average_fill_price is not None
            ):
                fill = self._fill_event(command, snapshot, partial=False)
                return [acknowledgement, fill] if fill is not None else [acknowledgement]
            acknowledgement.reason = (
                "Bybit PostOnly REST reconciliation found a quantity mismatch; "
                "MT5 hedge was not submitted"
            )
            return [acknowledgement]
        if (
            snapshot is not None
            and snapshot.status in {"canceled", "rejected"}
            and snapshot.filled_quantity == 0
            and state.cumulative_fill == 0
        ):
            return [
                acknowledgement,
                self._rejected_event(
                    command,
                    external_order_id=snapshot.external_order_id,
                    occurred_at=snapshot.as_of,
                    reason="Bybit PostOnly Chase ended without a fill",
                ),
            ]
        cumulative = max(
            state.cumulative_fill,
            snapshot.filled_quantity if snapshot is not None else Decimal("0"),
        )
        acknowledgement.reason = (
            "Bybit PostOnly Chase requires reconciliation; "
            f"confirmed cumulative fill is {cumulative} and MT5 was not submitted"
        )
        return [acknowledgement]

    def _postonly_quote(self, client, symbol: str) -> tuple[Decimal, Decimal]:
        try:
            response = client.get_tickers(
                category=self.settings.bybit_category,
                symbol=symbol.upper(),
            )
            self._require_success(response, "Bybit ticker query failed for PostOnly")
            rows = self._result_list(response)
            if not rows:
                raise GatewayRequestRejectedError("Bybit PostOnly ticker is unavailable")
            bid = Decimal(str(rows[0].get("bid1Price") or "0"))
            ask = Decimal(str(rows[0].get("ask1Price") or "0"))
            if bid <= 0 or ask <= 0 or bid >= ask:
                raise GatewayRequestRejectedError("Bybit PostOnly Bid/Ask is invalid")
            return bid, ask
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit PostOnly ticker result is unknown") from exc

    def _postonly_tick_size(self, client, symbol: str) -> Decimal:
        try:
            response = client.get_instruments_info(
                category=self.settings.bybit_category,
                symbol=symbol.upper(),
            )
            self._require_success(response, "Bybit instrument query failed for PostOnly")
            rows = self._result_list(response)
            price_filter = rows[0].get("priceFilter") if rows else None
            tick = (
                Decimal(str(price_filter.get("tickSize") or "0"))
                if isinstance(price_filter, dict)
                else Decimal("0")
            )
            if tick <= 0:
                raise GatewayRequestRejectedError("Bybit PostOnly Tick Size is invalid")
            return tick
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError(
                "Bybit PostOnly instrument result is unknown"
            ) from exc

    def _private_source(self, symbol: str, prefix: str) -> PrivateEventSource:
        if self._private_source_factory is not None:
            return self._private_source_factory(symbol, prefix)
        return BybitPrivateEventSource(
            self.settings,
            symbol=symbol,
            order_link_prefix=prefix,
        )

    @staticmethod
    def _reconcile_state(state: ChaseState, reason: str) -> ChaseState:
        return replace(state, status=ChaseStatus.RECONCILE_REQUIRED)

    def _submit_acknowledgement(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        self._assert_account(command.account_id)
        client = self._client(command.account_id)
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
            if command.execution_policy == "post_only_single_attempt":
                payload["timeInForce"] = "PostOnly"
            else:
                payload["timeInForce"] = "FOK" if self._is_cross_spread_fok(command) else "GTC"
        try:
            response = client.place_order(**payload)
        except Exception as exc:
            raise self._unknown_error("Bybit place_order result is unknown", exc) from exc
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

    def _rejected_event(
        self,
        command: SubmitOrderCommand,
        *,
        external_order_id: str,
        occurred_at: datetime,
        reason: str,
    ) -> ExecutionEvent:
        return ExecutionEvent(
            event_id=f"BYBIT-REJECT-{external_order_id}",
            command_id=command.command_id,
            platform_order_id=command.platform_order_id,
            event_type="order_rejected",
            external_order_id=external_order_id,
            occurred_at=occurred_at,
            reason=reason,
        )

    def _is_cross_spread_fok(self, command: SubmitOrderCommand) -> bool:
        return (
            command.order_type == "limit"
            and command.strategy_instance_id == CROSS_SPREAD_STRATEGY_INSTANCE_ID
            and command.execution_policy in {"default", "fok"}
        )

    @staticmethod
    def _is_postonly_chase(command: SubmitOrderCommand) -> bool:
        return (
            command.order_type == "limit"
            and command.strategy_instance_id == CROSS_SPREAD_STRATEGY_INSTANCE_ID
            and command.execution_policy == "post_only_chase"
        )

    def _sleep_before_retry(self) -> None:
        interval = self.settings.bybit_fill_confirmation_poll_seconds
        if interval > 0:
            sleep(interval)
