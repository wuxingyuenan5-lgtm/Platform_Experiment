from __future__ import annotations

import platform
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.config import Settings
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.live_route_store import (
    get_order_route,
    record_order_route,
    stable_external_client_id,
    update_external_order_id,
)
from app.live_safety import validate_live_cancel, validate_live_write
from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayAdapterCapability,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.secret_resolver import inspect_credential_reference, resolve_secret_reference


class Mt5LiveAdapter:
    name = "mt5_live"

    def __init__(self, settings: Settings, provider: Any | None = None) -> None:
        self.settings = settings
        self._provider = provider
        self._connected = False

    def capability(self) -> GatewayAdapterCapability:
        inspection = inspect_credential_reference(
            self.settings.mt5_credential_ref,
            required_fields=("LOGIN", "PASSWORD", "SERVER"),
        )
        missing = list(inspection.missing_fields)
        if not self.settings.mt5_accounts:
            missing.append("MT5_ACCOUNT_IDS")
        if not self.settings.mt5_instruments:
            missing.append("MT5_INSTRUMENT_MAP")
        if self._provider is None and platform.system() != "Windows":
            missing.append("WINDOWS_RUNTIME")
        if self._provider is None and not self._dependency_available():
            missing.append("METATRADER5_DEPENDENCY")
        configured = not [item for item in missing if item not in {"WINDOWS_RUNTIME", "METATRADER5_DEPENDENCY"}]
        operational = configured and not missing
        return GatewayAdapterCapability(
            adapter=self.name,
            environment="live",
            configured=configured,
            operational=operational,
            writeEnabled=operational and self.settings.live_write_enabled,
            accountIds=sorted(self.settings.mt5_accounts),
            capabilities=[
                "order_query",
                "deal_query",
                "position_query",
                "balance_query",
                "swap_query",
                "fee_query",
                "submit_order_gated",
                "cancel_order_gated",
            ],
            missingRequirements=sorted(set(missing)),
        )

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        self._assert_account(command.account_id)
        mt5 = self._connect()
        reference_price = command.price or self._market_reference_price(mt5, command)
        validate_live_write(
            command,
            adapter=self.name,
            reference_price=reference_price,
            settings=self.settings,
        )
        client_id = stable_external_client_id("VG-", command.platform_order_id, length=28)
        record_order_route(command, self.name, client_id)
        request = self._build_order_request(mt5, command, reference_price, client_id)
        try:
            checked = mt5.order_check(request)
        except Exception as exc:
            raise GatewayConfigurationError("MT5 order_check failed") from exc
        if checked is None:
            raise GatewayConfigurationError(f"MT5 order_check returned no result: {mt5.last_error()}")
        if int(getattr(checked, "retcode", -1)) != 0:
            raise GatewayRequestRejectedError(
                f"MT5 order_check rejected request: {getattr(checked, 'comment', 'unknown')}"
            )
        try:
            result = mt5.order_send(request)
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 order_send result is unknown") from exc
        if result is None:
            raise GatewayResultUnknownError(f"MT5 order_send returned no result: {mt5.last_error()}")
        retcode = int(getattr(result, "retcode", -1))
        success_codes = {
            int(getattr(mt5, "TRADE_RETCODE_DONE", 10009)),
            int(getattr(mt5, "TRADE_RETCODE_PLACED", 10008)),
            int(getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010)),
        }
        if retcode not in success_codes:
            raise GatewayRequestRejectedError(
                f"MT5 rejected order: {getattr(result, 'comment', retcode)}"
            )
        order_ticket = int(getattr(result, "order", 0) or 0)
        deal_ticket = int(getattr(result, "deal", 0) or 0)
        external_order_id = str(order_ticket or deal_ticket)
        if external_order_id == "0":
            raise GatewayResultUnknownError("MT5 accepted request without order or deal ticket")
        update_external_order_id(command.platform_order_id, external_order_id)
        events = [
            ExecutionEvent(
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_acknowledged",
                external_order_id=external_order_id,
                occurred_at=datetime.now(UTC),
            )
        ]
        result_volume = Decimal(str(getattr(result, "volume", 0) or 0))
        result_price = Decimal(str(getattr(result, "price", 0) or 0))
        if deal_ticket and result_volume > 0 and result_price > 0:
            events.append(
                ExecutionEvent(
                    event_id=f"MT5-DEAL-{deal_ticket}",
                    command_id=command.command_id,
                    platform_order_id=command.platform_order_id,
                    event_type="order_filled",
                    external_order_id=external_order_id,
                    fill_price=result_price,
                    fill_quantity=result_volume,
                    occurred_at=datetime.now(UTC),
                )
            )
        return events

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
        if route is None:
            return None
        mt5 = self._connect()
        ticket = int(route.external_order_id or 0)
        try:
            rows = mt5.orders_get(ticket=ticket) if ticket else ()
            if not rows and ticket:
                rows = mt5.history_orders_get(ticket=ticket)
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 order query result is unknown") from exc
        if not rows:
            return None
        return self._order_snapshot(mt5, rows[0], route)

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
        mt5 = self._connect()
        try:
            if route is not None and route.external_order_id:
                deals = mt5.history_deals_get(ticket=int(route.external_order_id)) or ()
            else:
                end = datetime.now(UTC)
                start = end - timedelta(days=self.settings.mt5_history_lookback_days)
                deals = mt5.history_deals_get(start, end) or ()
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 deal query result is unknown") from exc
        snapshots: list[VenueFillSnapshot] = []
        for deal in deals:
            if not self._is_trade_deal(mt5, deal):
                continue
            symbol = str(getattr(deal, "symbol", "")).upper()
            instrument_id = self.settings.mt5_instruments.get(symbol)
            if instrument_id is None:
                continue
            order_ticket = str(getattr(deal, "order", 0) or getattr(deal, "ticket", 0))
            row_route = get_order_route(external_order_id=order_ticket)
            snapshots.append(
                VenueFillSnapshot(
                    source=self.name,
                    externalFillId=str(getattr(deal, "ticket", order_ticket)),
                    externalOrderId=order_ticket,
                    platformOrderId=(
                        row_route.platform_order_id if row_route else f"external:{order_ticket}"
                    ),
                    commandId=(row_route.command_id if row_route else f"external:{order_ticket}"),
                    accountId=(row_route.account_id if row_route else account),
                    instrumentId=(row_route.instrument_id if row_route else instrument_id),
                    symbol=symbol,
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
                )
            )
        return snapshots

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        mt5 = self._connect()
        try:
            rows = mt5.positions_get() or ()
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 position query result is unknown") from exc
        currency = self._account_currency(mt5)
        snapshots: list[VenuePositionSnapshot] = []
        for row in rows:
            symbol = str(getattr(row, "symbol", "")).upper()
            instrument_id = self.settings.mt5_instruments.get(symbol)
            if instrument_id is None:
                continue
            volume = Decimal(str(getattr(row, "volume", 0)))
            if int(getattr(row, "type", -1)) == int(getattr(mt5, "POSITION_TYPE_SELL", 1)):
                volume = -volume
            snapshots.append(
                VenuePositionSnapshot(
                    source=self.name,
                    externalPositionId=str(getattr(row, "ticket", 0)),
                    accountId=account,
                    instrumentId=instrument_id,
                    symbol=symbol,
                    netQuantity=volume,
                    averagePrice=Decimal(str(getattr(row, "price_open", 0))),
                    currency=currency,
                    asOf=self._position_time(row),
                )
            )
        return snapshots

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        mt5 = self._connect()
        info = mt5.account_info()
        if info is None:
            raise GatewayResultUnknownError(f"MT5 account_info failed: {mt5.last_error()}")
        actual_login = str(getattr(info, "login", ""))
        secret = self._secret()
        if actual_login != str(secret["LOGIN"]):
            raise GatewayConfigurationError("Connected MT5 account does not match configured login")
        as_of = datetime.now(UTC)
        currency = str(getattr(info, "currency", "USD"))
        return [
            VenueBalanceSnapshot(
                source=self.name,
                externalBalanceId=f"{account}:{actual_login}:{int(as_of.timestamp())}",
                accountId=account,
                equity=Decimal(str(getattr(info, "equity", 0))),
                availableBalance=Decimal(str(getattr(info, "margin_free", 0))),
                currency=currency,
                asOf=as_of,
            )
        ]

    def list_economic_events(
        self,
        *,
        account_id: str | None = None,
        instrument_id: str | None = None,
        event_type: str | None = None,
    ) -> list[VenueEconomicEventSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        mt5 = self._connect()
        end = datetime.now(UTC)
        start = end - timedelta(days=self.settings.mt5_history_lookback_days)
        try:
            deals = mt5.history_deals_get(start, end) or ()
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 economic event query result is unknown") from exc
        currency = self._account_currency(mt5)
        events: list[VenueEconomicEventSnapshot] = []
        for deal in deals:
            symbol = str(getattr(deal, "symbol", "")).upper()
            mapped_instrument = self.settings.mt5_instruments.get(symbol)
            if instrument_id is not None and mapped_instrument != instrument_id:
                continue
            ticket = str(getattr(deal, "ticket", 0))
            occurred_at = self._deal_time(deal)
            components = {
                "swap": Decimal(str(getattr(deal, "swap", 0) or 0)),
                "fee": Decimal(str(getattr(deal, "commission", 0) or 0))
                + Decimal(str(getattr(deal, "fee", 0) or 0)),
            }
            for component_type, amount in components.items():
                if amount == 0 or event_type not in {None, component_type}:
                    continue
                events.append(
                    VenueEconomicEventSnapshot(
                        source=self.name,
                        externalEventId=f"{component_type}:{ticket}",
                        eventType=component_type,
                        accountId=account,
                        instrumentId=mapped_instrument,
                        symbol=symbol or None,
                        amount=amount,
                        currency=currency,
                        occurredAt=occurred_at,
                        payload=self._as_dict(deal),
                    )
                )
        return events

    def cancel_order(
        self,
        external_order_id: str,
        idempotency_key: str,
        reason: str | None,
    ) -> CancelOrderResponse:
        route = get_order_route(external_order_id=external_order_id)
        if route is None or route.adapter != self.name:
            return CancelOrderResponse(
                source=self.name,
                externalOrderId=external_order_id,
                platformOrderId="unknown",
                status="not_found",
                reason="Live order route not found",
                asOf=datetime.now(UTC),
            )
        validate_live_cancel(route, self.settings)
        mt5 = self._connect()
        request = {
            "action": int(getattr(mt5, "TRADE_ACTION_REMOVE")),
            "order": int(external_order_id),
            "magic": self.settings.mt5_magic_number,
            "comment": route.external_client_id,
        }
        try:
            result = mt5.order_send(request)
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 cancel result is unknown") from exc
        if result is None:
            raise GatewayResultUnknownError(f"MT5 cancel returned no result: {mt5.last_error()}")
        success_codes = {
            int(getattr(mt5, "TRADE_RETCODE_DONE", 10009)),
            int(getattr(mt5, "TRADE_RETCODE_PLACED", 10008)),
        }
        if int(getattr(result, "retcode", -1)) not in success_codes:
            raise GatewayRequestRejectedError(
                f"MT5 cancel rejected: {getattr(result, 'comment', 'unknown')}"
            )
        return CancelOrderResponse(
            source=self.name,
            externalOrderId=external_order_id,
            platformOrderId=route.platform_order_id,
            status="canceled",
            reason=reason,
            asOf=datetime.now(UTC),
        )

    def _connect(self):
        if self._provider is not None:
            return self._provider
        if platform.system() != "Windows":
            raise GatewayConfigurationError("MT5 live adapter requires Windows")
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise GatewayConfigurationError("MetaTrader5 dependency is not installed") from exc
        if self._connected:
            return mt5
        initialized = mt5.initialize(path=self.settings.mt5_terminal_path)
        if not initialized:
            raise GatewayConfigurationError(f"MT5 initialize failed: {mt5.last_error()}")
        secret = self._secret()
        authorized = mt5.login(
            int(secret["LOGIN"]),
            password=secret["PASSWORD"],
            server=secret["SERVER"],
        )
        if not authorized:
            raise GatewayConfigurationError(f"MT5 login failed: {mt5.last_error()}")
        self._connected = True
        return mt5

    def _secret(self) -> dict[str, str]:
        try:
            return resolve_secret_reference(
                self.settings.mt5_credential_ref,
                required_fields=("LOGIN", "PASSWORD", "SERVER"),
            )
        except ValueError as exc:
            raise GatewayConfigurationError(str(exc)) from exc

    def _assert_account(self, account_id: str) -> None:
        if account_id not in self.settings.mt5_accounts:
            raise GatewayConfigurationError("Account is not mapped to MT5 live adapter")

    def _single_account(self) -> str:
        accounts = sorted(self.settings.mt5_accounts)
        if len(accounts) != 1:
            raise GatewayConfigurationError("MT5 query requires an explicit accountId")
        return accounts[0]

    def _resolve_route(
        self,
        *,
        platform_order_id: str | None,
        external_order_id: str | None,
    ):
        if platform_order_id is not None:
            route = get_order_route(platform_order_id=platform_order_id)
        elif external_order_id is not None:
            route = get_order_route(external_order_id=external_order_id)
        else:
            raise ValueError("Order identity is required")
        if route is not None and route.adapter != self.name:
            return None
        return route

    def _market_reference_price(self, mt5, command: SubmitOrderCommand) -> Decimal:
        tick = mt5.symbol_info_tick(command.symbol)
        if tick is None:
            raise GatewayConfigurationError(f"MT5 symbol tick unavailable: {mt5.last_error()}")
        value = getattr(tick, "ask" if command.side == "buy" else "bid", 0)
        price = Decimal(str(value or 0))
        if price <= 0:
            raise GatewayConfigurationError("MT5 reference price is invalid")
        return price

    def _build_order_request(
        self,
        mt5,
        command: SubmitOrderCommand,
        reference_price: Decimal,
        comment: str,
    ) -> dict[str, object]:
        if command.order_type == "market":
            action = int(getattr(mt5, "TRADE_ACTION_DEAL"))
            order_type = int(
                getattr(mt5, "ORDER_TYPE_BUY" if command.side == "buy" else "ORDER_TYPE_SELL")
            )
        else:
            if command.price is None:
                raise GatewayRequestRejectedError("MT5 limit order requires price")
            action = int(getattr(mt5, "TRADE_ACTION_PENDING"))
            order_type = int(
                getattr(
                    mt5,
                    "ORDER_TYPE_BUY_LIMIT" if command.side == "buy" else "ORDER_TYPE_SELL_LIMIT",
                )
            )
        request: dict[str, object] = {
            "action": action,
            "symbol": command.symbol,
            "volume": float(command.quantity),
            "type": order_type,
            "price": float(command.price or reference_price),
            "deviation": self.settings.mt5_deviation_points,
            "magic": self.settings.mt5_magic_number,
            "comment": comment,
            "type_time": int(getattr(mt5, "ORDER_TIME_GTC")),
        }
        if command.order_type == "market":
            request["type_filling"] = int(getattr(mt5, "ORDER_FILLING_IOC"))
        else:
            request["type_filling"] = int(getattr(mt5, "ORDER_FILLING_RETURN"))
        return request

    def _order_snapshot(self, mt5, row, route) -> VenueOrderSnapshot:
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
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=str(getattr(row, "ticket", route.external_order_id or "unknown")),
            platformOrderId=route.platform_order_id,
            commandId=route.command_id,
            accountId=route.account_id,
            instrumentId=route.instrument_id,
            symbol=route.symbol,
            side="buy" if order_type_value in buy_types else "sell",
            orderType="market" if order_type_value in market_types else "limit",
            quantity=Decimal(str(getattr(row, "volume_initial", 0))),
            price=Decimal(str(getattr(row, "price_open", 0))),
            status=status,
            filledQuantity=Decimal(str(getattr(row, "volume_initial", 0)))
            - Decimal(str(getattr(row, "volume_current", 0))),
            averageFillPrice=None,
            occurredAt=self._seconds(getattr(row, "time_setup", None)),
            asOf=self._seconds(getattr(row, "time_done", None) or getattr(row, "time_setup", None)),
        )

    @staticmethod
    def _is_trade_deal(mt5, deal) -> bool:
        return int(getattr(deal, "type", -1)) in {
            int(getattr(mt5, "DEAL_TYPE_BUY", 0)),
            int(getattr(mt5, "DEAL_TYPE_SELL", 1)),
        }

    @staticmethod
    def _deal_time(deal) -> datetime:
        time_msc = int(getattr(deal, "time_msc", 0) or 0)
        if time_msc:
            return datetime.fromtimestamp(time_msc / 1000, UTC)
        return datetime.fromtimestamp(int(getattr(deal, "time", 0) or 0), UTC)

    @staticmethod
    def _position_time(row) -> datetime:
        time_msc = int(getattr(row, "time_update_msc", 0) or 0)
        if time_msc:
            return datetime.fromtimestamp(time_msc / 1000, UTC)
        return datetime.fromtimestamp(int(getattr(row, "time_update", 0) or 0), UTC)

    @staticmethod
    def _seconds(value: object) -> datetime:
        if not value:
            return datetime.now(UTC)
        return datetime.fromtimestamp(int(value), UTC)

    @staticmethod
    def _as_dict(value: object) -> dict[str, object]:
        converter = getattr(value, "_asdict", None)
        if converter is None:
            return {}
        return dict(converter())

    @staticmethod
    def _dependency_available() -> bool:
        try:
            import MetaTrader5  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def _account_currency(mt5) -> str:
        info = mt5.account_info()
        if info is None:
            raise GatewayResultUnknownError(f"MT5 account_info failed: {mt5.last_error()}")
        return str(getattr(info, "currency", "USD"))
