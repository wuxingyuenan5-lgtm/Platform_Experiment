from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from time import monotonic, sleep
from typing import Any

from app.bybit_live_adapter import BybitLiveAdapter
from app.bybit_native_strategy import create_chase_order, list_strategy_orders, stop_strategy
from app.cross_spread_market import _execution_capability
from app.gateway_errors import (
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.live_route_store import (
    get_strategy_route,
    get_strategy_route_for_order,
    record_order_route,
    record_strategy_order_route,
    record_strategy_route,
    stable_external_client_id,
    update_external_order_id,
)
from app.live_safety import validate_live_write
from app.models import ExecutionEvent, SubmitOrderCommand, VenueOrderSnapshot

CROSS_SPREAD_STRATEGY_INSTANCE_ID = "strategy_cross_venue_spread_instance_default"


class BybitFillConfirmingAdapter(BybitLiveAdapter):
    """Bybit adapter with bounded terminal confirmation and close safeguards."""

    def __init__(
        self,
        settings,
        client: Any | None = None,
    ) -> None:
        super().__init__(settings, client)
        self.market_quote_reader = None

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        if self._is_postonly_chase(command):
            return self._submit_postonly_chase(command)

        events = self._submit_acknowledgement(command)
        is_fok = self._is_fok(command)
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
                        "dependent hedge was not submitted pending reconciliation"
                    )
                    return events
                fill_event = self._fill_event(command, snapshot, partial=False)
                return [*events, fill_event] if fill_event is not None else events

            if snapshot.status == "canceled":
                if is_fok:
                    if snapshot.filled_quantity > 0:
                        acknowledgement.reason = (
                            "Bybit FOK order reached a terminal partial fill; "
                            "dependent hedge was not submitted pending reconciliation"
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
        return self._submit_native_postonly_chase(command)

    def _submit_native_postonly_chase(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        if command.price is None or command.cross_spread_guard is None:
            raise GatewayRequestRejectedError("Cross native Chase requires its frozen spread guard")
        self._assert_account(command.account_id)
        self._assert_write_account(command.account_id)
        client = self._client(command.account_id)
        validate_live_write(
            command, adapter=self.name, reference_price=command.price, settings=self.settings
        )
        if not self._cross_guard_allows(command):
            raise GatewayRequestRejectedError(
                "Cross-spread market/price guard blocked Chase before create"
            )
        from app.live_route_store import get_order_route

        if get_order_route(platform_order_id=command.platform_order_id) is not None:
            raise GatewayResultUnknownError(
                "Native Chase intent already dispatched; recover without recreating"
            )
        position_idx = self._resolve_native_position_idx(client, command)
        record_order_route(
            command,
            self.name,
            stable_external_client_id("VGP", command.platform_order_id, length=28),
        )
        strategy_id = create_chase_order(
            client,
            category="UTA_USDT",
            symbol=command.symbol,
            side="Buy" if command.side == "buy" else "Sell",
            size=format(command.quantity, "f"),
            reduce_only=command.reduce_only,
            position_idx=position_idx,
            max_chase_price=format(command.price, "f"),
        )
        try:
            record_strategy_route(command, self.name, strategy_id)
        except Exception as exc:
            try:
                stop_strategy(client, strategy_id)
            except Exception:
                pass
            raise GatewayResultUnknownError(
                f"Native strategy {strategy_id} could not be persisted; verify original strategy"
            ) from exc
        deadline = monotonic() + self.settings.bybit_postonly_chase_ttl_seconds
        stopped = False
        reconcile_deadline = None
        try:
            while True:
                strategy, rows, quantity, price, at = self._native_evidence(
                    client, command, strategy_id
                )
                terminal = self._native_is_terminal(strategy, rows)
                if terminal:
                    return self._native_events(command, strategy_id, rows, quantity, price, at)
                guard = command.cross_spread_guard
                lots = quantity / guard.mt5_contract_multiplier
                hedgeable = lots >= guard.mt5_min_quantity and lots % guard.mt5_quantity_step == 0
                if not stopped and (
                    hedgeable or monotonic() >= deadline or not self._cross_guard_allows(command)
                ):
                    stopped = True
                    stop_strategy(client, strategy_id)
                    reconcile_deadline = (
                        monotonic() + self.settings.bybit_postonly_chase_rest_reconcile_seconds
                    )
                if reconcile_deadline is not None and monotonic() >= reconcile_deadline:
                    raise GatewayResultUnknownError(
                        "Native Chase stop remains unconfirmed; reconcile original intent"
                    )
                self._sleep_before_retry()
        except Exception as exc:
            # A read failure must not leave a known native strategy chasing.
            # Attempt stop once; no create/repost follows an uncertain result.
            if not stopped:
                try:
                    stop_strategy(client, strategy_id)
                except Exception:
                    pass
            raise GatewayResultUnknownError("Native Chase outcome requires reconciliation") from exc

    def _resolve_native_position_idx(self, client, command: SubmitOrderCommand) -> int:
        if command.reduce_only:
            return self._resolve_reduce_position_idx(client, command)
        try:
            response = client.get_positions(
                category=self._command_category(command), symbol=command.symbol.upper()
            )
            self._require_success(response, "Bybit position mode query failed")
            rows = self._result_list(response)
            if not rows or any(
                str(row.get("symbol", "")).upper() != command.symbol.upper() for row in rows
            ):
                raise ValueError("Position mode evidence missing or mismatched")
            indexes = {int(row["positionIdx"]) for row in rows}
            if indexes == {0}:
                return 0
            if indexes and indexes <= {1, 2}:
                return 1 if command.side == "buy" else 2
            raise ValueError("Position mode evidence is conflicting")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit position mode is unavailable") from exc

    def _cross_guard_allows(self, command: SubmitOrderCommand) -> bool:
        guard = command.cross_spread_guard
        if guard is None or self.market_quote_reader is None:
            return False
        try:
            mt5 = self.market_quote_reader(account_id=guard.mt5_account_id, symbol=guard.mt5_symbol)
            bybit = self.get_market_quote(
                account_id=command.account_id,
                symbol=command.symbol,
                instrument_type=command.instrument_type,
                category=self._command_category(command),
            )
            for quote, account, symbol in (
                (mt5, guard.mt5_account_id, guard.mt5_symbol),
                (bybit, command.account_id, command.symbol),
            ):
                if quote.account_id != account or quote.symbol.upper() != symbol.upper():
                    return False
                if (
                    not quote.bid.is_finite()
                    or not quote.ask.is_finite()
                    or not (0 < quote.bid <= quote.ask)
                ):
                    return False
            mo, mc, _ = _execution_capability("mt5", mt5)
            bo, bc, _ = _execution_capability("bybit", bybit)
            if not ((mc and bc) if guard.mt5_close else (mo and bo)):
                return False
            if command.side == "buy":
                return bybit.ask - mt5.bid <= guard.target_spread + guard.max_adverse_spread
            return bybit.bid - mt5.ask >= guard.target_spread - guard.max_adverse_spread
        except Exception:
            return False

    @staticmethod
    def _native_is_terminal(strategy, rows):
        return str(strategy.get("status")) in {"3", "4"} and all(
            str(row.get("status")) in {"3", "5", "6", "7"} for row in rows
        )

    def _native_evidence(self, client, command, strategy_id):
        from app.bybit_native_strategy import get_strategy

        strategy = get_strategy(client, strategy_id)
        if strategy is None:
            raise GatewayResultUnknownError("Native strategy identity is not yet visible")
        if (
            str(strategy.get("strategyId")) != strategy_id
            or str(strategy.get("symbol")).upper() != command.symbol.upper()
            or str(strategy.get("side")).lower() != command.side
            or str(strategy.get("strategyType")) not in {"chaseOrder", "ChaseOrder"}
            or str(strategy.get("category")) != "UTA_USDT"
            or Decimal(str(strategy.get("size"))) != command.quantity
        ):
            raise GatewayResultUnknownError("Native strategy identity conflicts with frozen intent")
        rows = list_strategy_orders(client, strategy_id=strategy_id, symbol=command.symbol)
        for row in rows:
            if str(row.get("strategyId")) != strategy_id:
                raise GatewayResultUnknownError("Native child belongs to a different strategy")
            order_id = str(row.get("orderId") or "")
            if not order_id:
                raise GatewayResultUnknownError("Native child order identity missing")
            record_strategy_order_route(strategy_id=strategy_id, order_id=order_id, command=command)
        fills = self._native_executions(client, command, rows)
        quantity = sum((Decimal(str(fill["execQty"])) for fill in fills), Decimal("0"))
        child_quantity = sum((Decimal(str(row["executedSize"])) for row in rows), Decimal("0"))
        aggregate = Decimal(str(strategy["executedSize"]))
        if not all(
            q.is_finite() and 0 <= q <= command.quantity
            for q in (quantity, child_quantity, aggregate)
        ):
            raise GatewayResultUnknownError(
                "Native Chase cumulative quantity invalid or exceeds intent"
            )
        if self._native_is_terminal(strategy, rows) and (
            quantity != child_quantity or quantity != aggregate
        ):
            raise GatewayResultUnknownError("Native terminal execution coverage is incomplete")
        value = sum(
            (Decimal(str(f["execQty"])) * Decimal(str(f["execPrice"])) for f in fills), Decimal("0")
        )
        at = max((self._millis(f["execTime"]) for f in fills), default=command.received_at)
        return strategy, rows, quantity, value / quantity if quantity else None, at

    def _native_executions(self, client, command, rows):
        fills = {}
        for row in rows:
            order_id = str(row["orderId"])
            cursor = None
            cursors = set()
            for _ in range(100):
                query = dict(
                    category=self._command_category(command),
                    symbol=command.symbol,
                    orderId=order_id,
                    limit=100,
                )
                if cursor:
                    query["cursor"] = cursor
                response = client.get_executions(**query)
                self._require_success(response, "Native execution query failed")
                result = response.get("result")
                if not isinstance(result, dict) or not isinstance(result.get("list"), list):
                    raise GatewayResultUnknownError("Native execution page malformed")
                for fill in result["list"]:
                    if str(fill.get("execType") or "Trade") != "Trade":
                        continue
                    if (
                        str(fill.get("orderId")) != order_id
                        or str(fill.get("symbol")).upper() != command.symbol.upper()
                        or str(fill.get("side")).lower() != command.side
                        or not fill.get("execId")
                    ):
                        raise GatewayResultUnknownError("Native execution identity mismatch")
                    qty, price = Decimal(str(fill["execQty"])), Decimal(str(fill["execPrice"]))
                    if (
                        not qty.is_finite()
                        or not price.is_finite()
                        or qty <= 0
                        or price <= 0
                        or int(fill["execTime"]) <= 0
                    ):
                        raise GatewayResultUnknownError(
                            "Native execution price/quantity/time invalid"
                        )
                    key = str(fill["execId"])
                    previous = fills.get(key)
                    if previous is not None and any(
                        previous.get(k) != fill.get(k)
                        for k in (
                            "orderId",
                            "execQty",
                            "execPrice",
                            "execTime",
                            "side",
                            "symbol",
                            "execType",
                            "execFee",
                            "feeCurrency",
                        )
                    ):
                        raise GatewayResultUnknownError(
                            "Native execution ID has conflicting payload"
                        )
                    fills[key] = fill
                cursor = result.get("nextPageCursor")
                if cursor is not None and not isinstance(cursor, str):
                    raise GatewayResultUnknownError("Native execution cursor malformed")
                if not cursor:
                    break
                if cursor in cursors:
                    raise GatewayResultUnknownError("Native execution pagination repeated")
                cursors.add(cursor)
            else:
                raise GatewayResultUnknownError("Native execution pagination exceeded bound")
        return list(fills.values())

    def _native_events(self, command, strategy_id, rows, quantity, price, at):
        from app.live_route_store import get_order_route

        route = get_order_route(platform_order_id=command.platform_order_id)
        order_id = route.external_order_id if route else None
        if order_id is None and rows:
            order_id = min(str(row["orderId"]) for row in rows)
            update_external_order_id(command.platform_order_id, order_id)
        ack = ExecutionEvent(
            event_id=f"bybit-chase-ack:{strategy_id}",
            command_id=command.command_id,
            platform_order_id=command.platform_order_id,
            event_type="order_acknowledged",
            external_order_id=order_id,
            occurred_at=command.received_at,
        )
        if quantity == 0:
            return [
                ack,
                ExecutionEvent(
                    event_id=f"bybit-chase-zero:{strategy_id}",
                    command_id=command.command_id,
                    platform_order_id=command.platform_order_id,
                    event_type="order_rejected",
                    external_order_id=order_id,
                    occurred_at=command.received_at,
                    reason="Native Chase terminated without execution",
                ),
            ]
        return [
            ack,
            ExecutionEvent(
                event_id=f"bybit-chase-fill:{strategy_id}",
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_filled",
                external_order_id=order_id,
                fill_quantity=quantity,
                fill_price=price,
                occurred_at=at,
                terminal=True,
                reason="Native Chase terminal cumulative fill; unfilled remainder canceled",
            ),
        ]

    def get_order(self, *, platform_order_id=None, external_order_id=None):
        from app.journal import get_command
        from app.live_route_store import get_order_route

        route = (
            get_order_route(platform_order_id=platform_order_id)
            if platform_order_id
            else get_order_route(external_order_id=external_order_id)
        )
        strategy_route = (
            get_strategy_route(platform_order_id=route.platform_order_id) if route else None
        )
        if strategy_route is None:
            return super().get_order(
                platform_order_id=platform_order_id, external_order_id=external_order_id
            )
        record = get_command(route.command_id)
        if record is None:
            raise GatewayResultUnknownError("Native Chase command evidence unavailable")
        command = record.command
        strategy, rows, quantity, price, at = self._native_evidence(
            self._client(route.account_id), command, strategy_route.strategy_id
        )
        if not rows:
            return None
        primary = route.external_order_id or min(str(row["orderId"]) for row in rows)
        if route.external_order_id is None:
            update_external_order_id(route.platform_order_id, primary)
        terminal = self._native_is_terminal(strategy, rows)
        status = (
            ("filled" if quantity == command.quantity else "canceled")
            if terminal
            else ("partially_filled" if quantity else "accepted")
        )
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=primary,
            platformOrderId=route.platform_order_id,
            commandId=route.command_id,
            accountId=route.account_id,
            instrumentId=route.instrument_id,
            symbol=route.symbol,
            side=command.side,
            orderType="limit",
            quantity=command.quantity,
            price=command.price,
            status=status,
            filledQuantity=quantity,
            remainingQuantity=Decimal("0") if terminal else command.quantity - quantity,
            averageFillPrice=price,
            reduceOnly=command.reduce_only,
            timeInForce="PostOnly",
            occurredAt=command.received_at,
            asOf=at,
        )

    def list_fills(self, *, account_id=None, external_order_id=None, platform_order_id=None):
        from app.journal import get_command
        from app.live_route_store import get_order_route
        from app.models import VenueFillSnapshot

        route = (
            get_order_route(platform_order_id=platform_order_id)
            if platform_order_id
            else get_order_route(external_order_id=external_order_id)
            if external_order_id
            else None
        )
        strategy = get_strategy_route(platform_order_id=route.platform_order_id) if route else None
        if strategy is None:
            return super().list_fills(
                account_id=account_id,
                external_order_id=external_order_id,
                platform_order_id=platform_order_id,
            )
        if account_id is not None and account_id != route.account_id:
            raise GatewayRequestRejectedError("Native fill account does not match route")
        self._assert_account(route.account_id)
        record = get_command(route.command_id)
        if record is None:
            raise GatewayResultUnknownError("Native command evidence unavailable")
        client = self._client(route.account_id)
        _, rows, _, _, _ = self._native_evidence(client, record.command, strategy.strategy_id)
        fills = self._native_executions(client, record.command, rows)
        return [
            VenueFillSnapshot(
                source=self.name,
                externalFillId=str(f["execId"]),
                externalOrderId=str(f["orderId"]),
                platformOrderId=route.platform_order_id,
                commandId=route.command_id,
                accountId=route.account_id,
                instrumentId=route.instrument_id,
                symbol=route.symbol,
                side=record.command.side,
                quantity=Decimal(str(f["execQty"])),
                price=Decimal(str(f["execPrice"])),
                fee=Decimal(str(f["execFee"])) if f.get("execFee") not in (None, "") else None,
                currency=str(f.get("feeCurrency") or self.settings.bybit_settle_coin),
                feeCurrencyQuality="reported" if f.get("feeCurrency") else "inferred_settlement",
                occurredAt=self._millis(f["execTime"]),
            )
            for f in fills
        ]

    def cancel_order(self, external_order_id, idempotency_key, reason):
        strategy_route = get_strategy_route_for_order(external_order_id)
        if strategy_route is None:
            return super().cancel_order(external_order_id, idempotency_key, reason)
        from app.journal import get_command
        from app.live_route_store import get_order_route
        from app.models import CancelOrderResponse

        route = get_order_route(platform_order_id=strategy_route.platform_order_id)
        record = get_command(route.command_id) if route else None
        if record is None:
            raise GatewayResultUnknownError("Native Chase cancel command identity missing")
        self._assert_write_account(route.account_id)
        client = self._client(route.account_id)
        stop_strategy(client, strategy_route.strategy_id)
        deadline = monotonic() + self.settings.bybit_postonly_chase_rest_reconcile_seconds
        while True:
            strategy, rows, quantity, _, _ = self._native_evidence(
                client, record.command, strategy_route.strategy_id
            )
            if self._native_is_terminal(strategy, rows):
                return CancelOrderResponse(
                    source=self.name,
                    externalOrderId=external_order_id,
                    platformOrderId=route.platform_order_id,
                    status="already_final" if quantity == record.command.quantity else "canceled",
                    reason=reason,
                    asOf=datetime.now(UTC),
                )
            if monotonic() >= deadline:
                raise GatewayResultUnknownError("Native Chase stop remains unconfirmed")
            self._sleep_before_retry()

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
            raise GatewayResultUnknownError("Bybit PostOnly instrument result is unknown") from exc

    def _submit_acknowledgement(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        self._assert_account(command.account_id)
        self._assert_write_account(command.account_id)
        market_fields = self._order_market_fields(command)
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
            **market_fields,
            "symbol": command.symbol.upper(),
            "side": "Buy" if command.side == "buy" else "Sell",
            "orderType": "Market" if command.order_type == "market" else "Limit",
            "qty": format(command.quantity, "f"),
            "orderLinkId": client_id,
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
                payload["timeInForce"] = "FOK" if self._is_fok(command) else "GTC"
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
            raise GatewayResultUnknownError("Bybit close-position query result is unknown") from exc

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

    def _is_fok(self, command: SubmitOrderCommand) -> bool:
        return command.order_type == "limit" and (
            command.execution_policy == "fok"
            or (
                command.strategy_instance_id == CROSS_SPREAD_STRATEGY_INSTANCE_ID
                and command.execution_policy == "default"
            )
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
