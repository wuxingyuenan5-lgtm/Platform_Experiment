from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.bybit_fill_confirming_adapter import BybitFillConfirmingAdapter
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.live_route_store import get_order_route
from app.models import (
    SubmitOrderCommand,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueOrderSnapshot,
)
from app.mt5_position_closing_adapter import Mt5PositionClosingAdapter


class BybitAcceptanceAdapter(BybitFillConfirmingAdapter):
    """Bybit live adapter with temporary one-ounce acceptance controls."""

    def submit_order(self, command: SubmitOrderCommand):
        self._validate_acceptance_quantity(command)
        if not command.reduce_only:
            self._assert_no_existing_position(command.symbol)
        return super().submit_order(command)

    def get_order(
        self,
        *,
        platform_order_id: str | None = None,
        external_order_id: str | None = None,
    ) -> VenueOrderSnapshot | None:
        route = self._resolve_route(
            platform_order_id=platform_order_id,
            external_order_id=external_order_id,
        )
        if route is None and platform_order_id is not None:
            return None
        account = route.account_id if route is not None else self._single_account()
        self._assert_account(account)
        query: dict[str, object] = {"category": self.settings.bybit_category}
        if route is not None:
            query["symbol"] = route.symbol
            if route.external_order_id:
                query["orderId"] = route.external_order_id
            else:
                query["orderLinkId"] = route.external_client_id
        elif external_order_id is not None:
            query["orderId"] = external_order_id
        else:
            raise ValueError("Order identity is required")

        rows = self._query_order_rows(query)
        if not rows:
            return None
        return self._order_snapshot_without_route_requirement(rows[0], account)

    def list_orders(
        self,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[VenueOrderSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        bounded_limit = max(1, min(limit, 50))
        query: dict[str, object] = {
            "category": self.settings.bybit_category,
            "limit": bounded_limit,
        }
        if symbol:
            query["symbol"] = symbol.upper()
        try:
            active_response = self._client().get_open_orders(openOnly=0, **query)
            self._require_success(active_response, "Bybit active-order query failed")
            history_response = self._client().get_order_history(**query)
            self._require_success(history_response, "Bybit order-history query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit order-list result is unknown") from exc

        merged: dict[str, dict[str, object]] = {}
        for row in [*self._result_list(active_response), *self._result_list(history_response)]:
            order_id = str(row.get("orderId") or "")
            if order_id and order_id not in merged:
                merged[order_id] = row
        snapshots = [
            snapshot
            for row in merged.values()
            if (snapshot := self._order_snapshot_without_route_requirement(row, account)) is not None
        ]
        snapshots.sort(key=lambda item: item.as_of, reverse=True)
        return snapshots[:bounded_limit]

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        route = None
        if platform_order_id is not None or external_order_id is not None:
            route = self._resolve_route(
                platform_order_id=platform_order_id,
                external_order_id=external_order_id,
            )
            if route is None and platform_order_id is not None:
                return []
        query: dict[str, object] = {"category": self.settings.bybit_category, "limit": 100}
        if route is not None:
            query["symbol"] = route.symbol
            if route.external_order_id:
                query["orderId"] = route.external_order_id
            else:
                query["orderLinkId"] = route.external_client_id
        elif external_order_id is not None:
            query["orderId"] = external_order_id
        try:
            response = self._client().get_executions(**query)
            self._require_success(response, "Bybit execution query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit execution query result is unknown") from exc

        snapshots: list[VenueFillSnapshot] = []
        for row in self._result_list(response):
            order_id = str(row.get("orderId") or "unknown")
            row_route = get_order_route(external_order_id=order_id)
            if row_route is None:
                link_id = str(row.get("orderLinkId") or "")
                if link_id:
                    row_route = get_order_route(external_client_id=link_id)
            symbol_value = str(row.get("symbol") or "").upper()
            instrument_id = (
                row_route.instrument_id
                if row_route is not None
                else self.settings.bybit_instruments.get(symbol_value)
            )
            if instrument_id is None:
                continue
            snapshots.append(
                VenueFillSnapshot(
                    source=self.name,
                    externalFillId=str(row.get("execId") or f"{order_id}:{row.get('execTime')}"),
                    externalOrderId=order_id,
                    platformOrderId=(
                        row_route.platform_order_id
                        if row_route is not None
                        else f"external:{self.name}:{order_id}"
                    ),
                    commandId=(
                        row_route.command_id
                        if row_route is not None
                        else f"external:{self.name}:{order_id}"
                    ),
                    accountId=row_route.account_id if row_route is not None else account,
                    instrumentId=instrument_id,
                    symbol=symbol_value,
                    side="buy" if str(row.get("side")) == "Buy" else "sell",
                    quantity=Decimal(str(row.get("execQty") or "0")),
                    price=Decimal(str(row.get("execPrice") or "0")),
                    fee=Decimal(str(row.get("execFee") or "0")),
                    currency=str(row.get("feeCurrency") or self.settings.bybit_settle_coin),
                    occurredAt=self._millis(row.get("execTime")),
                    dataQualityState="complete" if row_route is not None else "external_only",
                )
            )
        return snapshots

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
    ) -> VenueInstrumentSpecification:
        self._assert_account(account_id)
        normalized_symbol = symbol.upper()
        instrument_id = self.settings.bybit_instruments.get(normalized_symbol)
        if instrument_id is None:
            raise GatewayConfigurationError("Bybit symbol is not mapped to a Platform instrument")
        try:
            response = self._client().get_instruments_info(
                category=self.settings.bybit_category,
                symbol=normalized_symbol,
            )
            self._require_success(response, "Bybit instrument query failed")
            rows = self._result_list(response)
            if not rows:
                raise GatewayConfigurationError("Bybit instrument query returned no data")
            api_response = self._client().get_api_key_information()
            self._require_success(api_response, "Bybit API-key readiness query failed")
        except (GatewayConfigurationError, GatewayRequestRejectedError):
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit instrument query result is unknown") from exc

        row = rows[0]
        lot = row.get("lotSizeFilter") or {}
        api_result = api_response.get("result") or {}
        permissions = api_result.get("permissions") or {}
        contract_permissions = permissions.get("ContractTrade") or []
        return VenueInstrumentSpecification(
            source=self.name,
            accountId=account_id,
            instrumentId=instrument_id,
            symbol=normalized_symbol,
            status=str(row.get("status") or "unknown"),
            minQuantity=Decimal(str(lot.get("minOrderQty") or "0")),
            quantityStep=Decimal(str(lot.get("qtyStep") or "0")),
            maxMarketQuantity=self._optional_decimal(lot.get("maxMktOrderQty")),
            contractSize=Decimal("1"),
            trade_mode=self.settings.bybit_category,
            filling_mode="market",
            accessChecks={
                "readOnly": int(api_result.get("readOnly") or 0) == 1,
                "ipBound": bool(api_result.get("ips") or []),
                "orderPermission": "Order" in contract_permissions,
                "positionPermission": "Position" in contract_permissions,
            },
            asOf=datetime.now(UTC),
        )

    def _query_order_rows(self, query: dict[str, object]) -> list[dict[str, object]]:
        try:
            realtime = self._client().get_open_orders(**query)
            self._require_success(realtime, "Bybit order query failed")
            rows = self._result_list(realtime)
            if not rows:
                history = self._client().get_order_history(**query)
                self._require_success(history, "Bybit order history query failed")
                rows = self._result_list(history)
            return rows
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit order query result is unknown") from exc

    def _order_snapshot_without_route_requirement(
        self,
        row: dict[str, object],
        account: str,
    ) -> VenueOrderSnapshot | None:
        external_order_id = str(row.get("orderId") or "")
        if not external_order_id:
            return None
        route = get_order_route(external_order_id=external_order_id)
        if route is None:
            link_id = str(row.get("orderLinkId") or "")
            if link_id:
                route = get_order_route(external_client_id=link_id)
        symbol = str(row.get("symbol") or (route.symbol if route else "")).upper()
        instrument_id = route.instrument_id if route else self.settings.bybit_instruments.get(symbol)
        if instrument_id is None:
            return None
        status_map = {
            "New": "accepted",
            "Created": "accepted",
            "PartiallyFilled": "partially_filled",
            "Filled": "filled",
            "Cancelled": "canceled",
            "Canceled": "canceled",
            "Rejected": "rejected",
        }
        synthetic_identity = f"external:{self.name}:{external_order_id}"
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=external_order_id,
            platformOrderId=route.platform_order_id if route else synthetic_identity,
            commandId=route.command_id if route else synthetic_identity,
            accountId=route.account_id if route else account,
            instrumentId=instrument_id,
            symbol=symbol,
            side="buy" if str(row.get("side")) == "Buy" else "sell",
            orderType="market" if str(row.get("orderType")) == "Market" else "limit",
            quantity=Decimal(str(row.get("qty") or "0")),
            price=self._optional_decimal(row.get("price")),
            status=status_map.get(str(row.get("orderStatus")), "unknown"),
            filledQuantity=Decimal(str(row.get("cumExecQty") or "0")),
            averageFillPrice=self._optional_decimal(row.get("avgPrice")),
            occurredAt=self._millis(row.get("createdTime")),
            asOf=self._millis(row.get("updatedTime")),
            dataQualityState="complete" if route else "external_only",
        )

    def _validate_acceptance_quantity(self, command: SubmitOrderCommand) -> None:
        maximum = self.settings.live_acceptance_max_order_quantity
        if maximum <= 0:
            raise GatewayConfigurationError("Live acceptance maximum quantity is not configured")
        if command.quantity > maximum:
            raise GatewayRequestRejectedError("Live acceptance maximum quantity would be exceeded")

    def _assert_no_existing_position(self, symbol: str) -> None:
        maximum = self.settings.live_acceptance_max_positions_per_symbol
        if maximum <= 0:
            raise GatewayConfigurationError("Live acceptance position limit is not configured")
        try:
            response = self._client().get_positions(
                category=self.settings.bybit_category,
                symbol=symbol.upper(),
            )
            self._require_success(response, "Bybit pre-trade position query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit pre-trade position result is unknown") from exc
        active = sum(
            1
            for row in self._result_list(response)
            if Decimal(str(row.get("size") or "0")) != 0
        )
        if active >= maximum:
            raise GatewayRequestRejectedError("Live acceptance position limit is already reached")


class Mt5AcceptanceAdapter(Mt5PositionClosingAdapter):
    """MT5 live adapter with route-independent reads and ticket correction."""

    def submit_order(self, command: SubmitOrderCommand):
        self._validate_acceptance_quantity(command)
        if not command.reduce_only:
            self._assert_no_existing_position(command.symbol)
        return super().submit_order(command)

    def get_order(
        self,
        *,
        platform_order_id: str | None = None,
        external_order_id: str | None = None,
    ) -> VenueOrderSnapshot | None:
        route = self._resolve_route(
            platform_order_id=platform_order_id,
            external_order_id=external_order_id,
        )
        if route is None and platform_order_id is not None:
            return None
        account = route.account_id if route else self._single_account()
        self._assert_account(account)
        ticket_text = route.external_order_id if route else external_order_id
        if not ticket_text:
            return None
        try:
            ticket = int(ticket_text)
        except ValueError as exc:
            raise GatewayRequestRejectedError("MT5 ticket must be numeric") from exc
        mt5 = self._connect()
        try:
            rows = mt5.orders_get(ticket=ticket) or ()
            if not rows:
                rows = mt5.history_orders_get(ticket=ticket) or ()
            if rows:
                return self._order_snapshot_without_route_requirement(mt5, rows[0], account)
            deals = mt5.history_deals_get(ticket=ticket) or ()
            if not deals:
                return None
            deal = deals[0]
            order_ticket = int(getattr(deal, "order", 0) or 0)
            if order_ticket:
                order_rows = mt5.history_orders_get(ticket=order_ticket) or ()
                if order_rows:
                    return self._order_snapshot_without_route_requirement(
                        mt5,
                        order_rows[0],
                        account,
                        fallback_route=route,
                    )
            return self._deal_as_order_snapshot(mt5, deal, account, fallback_route=route)
        except (GatewayConfigurationError, GatewayRequestRejectedError):
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 order query result is unknown") from exc

    def list_orders(
        self,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[VenueOrderSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        bounded_limit = max(1, min(limit, 100))
        mt5 = self._connect()
        end = datetime.now(UTC)
        start = end - timedelta(days=self.settings.mt5_history_lookback_days)
        try:
            active = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
            history = mt5.history_orders_get(start, end) or ()
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 order-list result is unknown") from exc
        merged: dict[str, Any] = {}
        for row in [*(active or ()), *history]:
            row_symbol = str(getattr(row, "symbol", "")).upper()
            if symbol and row_symbol != symbol.upper():
                continue
            ticket = str(getattr(row, "ticket", 0))
            if ticket != "0" and ticket not in merged:
                merged[ticket] = row
        snapshots = [
            snapshot
            for row in merged.values()
            if (snapshot := self._order_snapshot_without_route_requirement(mt5, row, account))
            is not None
        ]
        snapshots.sort(key=lambda item: item.as_of, reverse=True)
        return snapshots[:bounded_limit]

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        route = None
        if platform_order_id is not None or external_order_id is not None:
            route = self._resolve_route(
                platform_order_id=platform_order_id,
                external_order_id=external_order_id,
            )
            if route is None and platform_order_id is not None:
                return []
        mt5 = self._connect()
        end = datetime.now(UTC)
        start = end - timedelta(days=self.settings.mt5_history_lookback_days)
        try:
            deals = mt5.history_deals_get(start, end) or ()
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 deal query result is unknown") from exc

        target = route.external_order_id if route is not None else external_order_id
        snapshots: list[VenueFillSnapshot] = []
        for deal in deals:
            if not self._is_trade_deal(mt5, deal):
                continue
            deal_ticket = str(getattr(deal, "ticket", 0))
            order_ticket = str(getattr(deal, "order", 0) or deal_ticket)
            comment = str(getattr(deal, "comment", "") or "")
            if target is not None and target not in {deal_ticket, order_ticket}:
                if route is None or comment != route.external_client_id:
                    continue
            row_route = get_order_route(external_order_id=order_ticket)
            if row_route is None:
                row_route = get_order_route(external_order_id=deal_ticket)
            if row_route is None and comment:
                row_route = get_order_route(external_client_id=comment)
            symbol_value = str(getattr(deal, "symbol", "")).upper()
            instrument_id = (
                row_route.instrument_id
                if row_route is not None
                else self.settings.mt5_instruments.get(symbol_value)
            )
            if instrument_id is None:
                continue
            synthetic_identity = f"external:{self.name}:{order_ticket}"
            snapshots.append(
                VenueFillSnapshot(
                    source=self.name,
                    externalFillId=deal_ticket,
                    externalOrderId=order_ticket,
                    platformOrderId=(
                        row_route.platform_order_id if row_route else synthetic_identity
                    ),
                    commandId=row_route.command_id if row_route else synthetic_identity,
                    accountId=row_route.account_id if row_route else account,
                    instrumentId=instrument_id,
                    symbol=symbol_value,
                    side=(
                        "buy"
                        if int(getattr(deal, "type", -1))
                        == int(getattr(mt5, "DEAL_TYPE_BUY", 0))
                        else "sell"
                    ),
                    quantity=Decimal(str(getattr(deal, "volume", 0))),
                    price=Decimal(str(getattr(deal, "price", 0))),
                    fee=abs(
                        Decimal(str(getattr(deal, "commission", 0) or 0))
                        + Decimal(str(getattr(deal, "fee", 0) or 0))
                    ),
                    currency=self._account_currency(mt5),
                    occurredAt=self._deal_time(deal),
                    dataQualityState="complete" if row_route else "external_only",
                )
            )
        return snapshots

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
    ) -> VenueInstrumentSpecification:
        self._assert_account(account_id)
        normalized_symbol = symbol.upper()
        instrument_id = self.settings.mt5_instruments.get(normalized_symbol)
        if instrument_id is None:
            raise GatewayConfigurationError("MT5 symbol is not mapped to a Platform instrument")
        mt5 = self._connect()
        info = mt5.symbol_info(symbol)
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if info is None or account is None or terminal is None:
            raise GatewayResultUnknownError(f"MT5 specification query failed: {mt5.last_error()}")
        actual_login = str(getattr(account, "login", ""))
        secret = self._secret()
        return VenueInstrumentSpecification(
            source=self.name,
            accountId=account_id,
            instrumentId=instrument_id,
            symbol=normalized_symbol,
            status="available" if bool(getattr(info, "select", True)) else "unselected",
            minQuantity=Decimal(str(getattr(info, "volume_min", 0) or 0)),
            quantityStep=Decimal(str(getattr(info, "volume_step", 0) or 0)),
            maxMarketQuantity=Decimal(str(getattr(info, "volume_max", 0) or 0)),
            contractSize=Decimal(str(getattr(info, "trade_contract_size", 0) or 0)),
            trade_mode=str(int(getattr(info, "trade_mode", -1))),
            filling_mode=str(int(getattr(info, "filling_mode", -1))),
            accessChecks={
                "accountLoginMatched": actual_login == str(secret["LOGIN"]),
                "accountTradeAllowed": bool(getattr(account, "trade_allowed", False)),
                "terminalTradeAllowed": bool(getattr(terminal, "trade_allowed", False)),
                "symbolVisible": bool(getattr(info, "visible", False)),
            },
            asOf=datetime.now(UTC),
        )

    def _order_snapshot_without_route_requirement(
        self,
        mt5,
        row,
        account: str,
        *,
        fallback_route=None,
    ) -> VenueOrderSnapshot | None:
        ticket = str(getattr(row, "ticket", 0))
        if ticket == "0":
            return None
        route = get_order_route(external_order_id=ticket) or fallback_route
        comment = str(getattr(row, "comment", "") or "")
        if route is None and comment:
            route = get_order_route(external_client_id=comment)
        symbol = str(getattr(row, "symbol", route.symbol if route else "")).upper()
        instrument_id = route.instrument_id if route else self.settings.mt5_instruments.get(symbol)
        if instrument_id is None:
            return None
        state = int(getattr(row, "state", -1))
        status = "unknown"
        if state in {
            int(getattr(mt5, "ORDER_STATE_STARTED", 0)),
            int(getattr(mt5, "ORDER_STATE_PLACED", 1)),
            int(getattr(mt5, "ORDER_STATE_REQUEST_ADD", 7)),
        }:
            status = "accepted"
        elif state == int(getattr(mt5, "ORDER_STATE_PARTIAL", 3)):
            status = "partially_filled"
        elif state == int(getattr(mt5, "ORDER_STATE_FILLED", 4)):
            status = "filled"
        elif state in {
            int(getattr(mt5, "ORDER_STATE_CANCELED", 2)),
            int(getattr(mt5, "ORDER_STATE_EXPIRED", 6)),
        }:
            status = "canceled"
        elif state == int(getattr(mt5, "ORDER_STATE_REJECTED", 5)):
            status = "rejected"
        order_type_value = int(getattr(row, "type", -1))
        buy_types = {
            int(getattr(mt5, "ORDER_TYPE_BUY", 0)),
            int(getattr(mt5, "ORDER_TYPE_BUY_LIMIT", 2)),
            int(getattr(mt5, "ORDER_TYPE_BUY_STOP", 4)),
        }
        market_types = {
            int(getattr(mt5, "ORDER_TYPE_BUY", 0)),
            int(getattr(mt5, "ORDER_TYPE_SELL", 1)),
        }
        initial = Decimal(str(getattr(row, "volume_initial", 0) or 0))
        current = Decimal(str(getattr(row, "volume_current", 0) or 0))
        synthetic_identity = f"external:{self.name}:{ticket}"
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=ticket,
            platformOrderId=route.platform_order_id if route else synthetic_identity,
            commandId=route.command_id if route else synthetic_identity,
            accountId=route.account_id if route else account,
            instrumentId=instrument_id,
            symbol=symbol,
            side="buy" if order_type_value in buy_types else "sell",
            orderType="market" if order_type_value in market_types else "limit",
            quantity=initial,
            price=Decimal(str(getattr(row, "price_open", 0) or 0)),
            status=status,
            filledQuantity=initial - current,
            averageFillPrice=None,
            occurredAt=self._seconds(getattr(row, "time_setup", None)),
            asOf=self._seconds(
                getattr(row, "time_done", None) or getattr(row, "time_setup", None)
            ),
            dataQualityState="complete" if route else "external_only",
        )

    def _deal_as_order_snapshot(
        self,
        mt5,
        deal,
        account: str,
        *,
        fallback_route=None,
    ) -> VenueOrderSnapshot | None:
        deal_ticket = str(getattr(deal, "ticket", 0))
        order_ticket = str(getattr(deal, "order", 0) or deal_ticket)
        route = get_order_route(external_order_id=order_ticket)
        if route is None:
            route = get_order_route(external_order_id=deal_ticket) or fallback_route
        comment = str(getattr(deal, "comment", "") or "")
        if route is None and comment:
            route = get_order_route(external_client_id=comment)
        symbol = str(getattr(deal, "symbol", route.symbol if route else "")).upper()
        instrument_id = route.instrument_id if route else self.settings.mt5_instruments.get(symbol)
        if instrument_id is None:
            return None
        quantity = Decimal(str(getattr(deal, "volume", 0) or 0))
        price = Decimal(str(getattr(deal, "price", 0) or 0))
        synthetic_identity = f"external:{self.name}:{order_ticket}"
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=order_ticket,
            platformOrderId=route.platform_order_id if route else synthetic_identity,
            commandId=route.command_id if route else synthetic_identity,
            accountId=route.account_id if route else account,
            instrumentId=instrument_id,
            symbol=symbol,
            side=(
                "buy"
                if int(getattr(deal, "type", -1)) == int(getattr(mt5, "DEAL_TYPE_BUY", 0))
                else "sell"
            ),
            orderType="market",
            quantity=quantity,
            price=price,
            status="filled",
            filledQuantity=quantity,
            averageFillPrice=price,
            occurredAt=self._deal_time(deal),
            asOf=self._deal_time(deal),
            dataQualityState="complete" if route else "external_only",
        )

    def _validate_acceptance_quantity(self, command: SubmitOrderCommand) -> None:
        maximum = self.settings.live_acceptance_max_order_quantity
        if maximum <= 0:
            raise GatewayConfigurationError("Live acceptance maximum quantity is not configured")
        if command.quantity > maximum:
            raise GatewayRequestRejectedError("Live acceptance maximum quantity would be exceeded")

    def _assert_no_existing_position(self, symbol: str) -> None:
        maximum = self.settings.live_acceptance_max_positions_per_symbol
        if maximum <= 0:
            raise GatewayConfigurationError("Live acceptance position limit is not configured")
        mt5 = self._connect()
        try:
            rows = mt5.positions_get(symbol=symbol) or ()
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 pre-trade position result is unknown") from exc
        if len(rows) >= maximum:
            raise GatewayRequestRejectedError("Live acceptance position limit is already reached")
