from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.live_route_store import get_order_route
from app.models import (
    GatewayAdapterCapability,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueOrderSnapshot,
)
from app.mt5_position_closing_adapter import Mt5PositionClosingAdapter
from app.order_semantics import OrderStatus, normalize_mt5_order_status


class Mt5AcceptanceAdapter(Mt5PositionClosingAdapter):
    """Route-independent MT5 reads with explicit Order/Deal ticket handling."""

    def _monitoring_instrument_identity(self, account_id: str, symbol: str) -> str:
        normalized_symbol = symbol.strip().upper()
        digest = hashlib.sha256(f"mt5:{account_id}:{normalized_symbol}".encode()).hexdigest()[:20]
        return f"monitor:mt5:{account_id}:{digest}"

    def _resolve_read_instrument(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_id: str | None,
        prefer_route: bool,
    ) -> tuple[str, str]:
        if instrument_id:
            return instrument_id, "complete" if prefer_route else "external_only"
        return self._monitoring_instrument_identity(account_id, symbol), "external_unmapped"

    def capability(self) -> GatewayAdapterCapability:
        capability = super().capability()
        capability.capabilities.extend(
            ["order_list", "instrument_specification_query", "deal_ticket_resolution"]
        )
        capability.capabilities = sorted(set(capability.capabilities))
        return capability

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
        ticket_text = route.external_order_id if route is not None else external_order_id
        if not ticket_text or not ticket_text.isdigit():
            return None
        ticket = int(ticket_text)
        mt5 = self._connect()
        try:
            rows = mt5.orders_get(ticket=ticket) or ()
            if not rows:
                rows = mt5.history_orders_get(ticket=ticket) or ()
            if rows:
                return self._snapshot(mt5, rows[0], account, fallback_route=route)
            deals = mt5.history_deals_get(ticket=ticket) or ()
            if not deals:
                return None
            deal = deals[0]
            order_ticket = int(getattr(deal, "order", 0) or 0)
            if order_ticket:
                order_rows = mt5.history_orders_get(ticket=order_ticket) or ()
                if order_rows:
                    return self._snapshot(
                        mt5,
                        order_rows[0],
                        account,
                        fallback_route=route,
                    )
            return self._deal_snapshot(mt5, deal, account, fallback_route=route)
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
        start, end = self._history_window()
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
        snapshots: list[VenueOrderSnapshot] = []
        for row in merged.values():
            snapshot = self._snapshot(mt5, row, account)
            if snapshot is not None:
                snapshots.append(snapshot)
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
        start, end = self._history_window()
        try:
            deals = mt5.history_deals_get(start, end) or ()
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 deal query result is unknown") from exc
        target = route.external_order_id if route is not None else external_order_id
        snapshots: list[VenueFillSnapshot] = []
        for deal in deals:
            if not self._is_trade_deal(mt5, deal):
                continue
            snapshot = self._fill_snapshot(
                mt5,
                deal,
                account,
                target=target,
                fallback_route=route,
            )
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
    ) -> VenueInstrumentSpecification:
        self._assert_account(account_id)
        normalized = symbol.upper()
        instrument_id = self.settings.mt5_instruments.get(normalized)
        if instrument_id is None:
            raise GatewayConfigurationError("MT5 symbol is not mapped to a Platform instrument")
        mt5 = self._connect()
        info = mt5.symbol_info(symbol)
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if info is None or account is None or terminal is None:
            raise GatewayResultUnknownError(f"MT5 specification query failed: {mt5.last_error()}")
        actual_login = str(getattr(account, "login", ""))
        secret = self._secret_for_account(account_id)
        return VenueInstrumentSpecification(
            source=self.name,
            accountId=account_id,
            instrumentId=instrument_id,
            instrumentType="mt5_contract",
            category="mt5",
            symbol=normalized,
            status="available" if bool(getattr(info, "select", True)) else "unselected",
            priceTick=Decimal(str(getattr(info, "point", 0) or 0)),
            minQuantity=Decimal(str(getattr(info, "volume_min", 0) or 0)),
            quantityStep=Decimal(str(getattr(info, "volume_step", 0) or 0)),
            maxMarketQuantity=Decimal(str(getattr(info, "volume_max", 0) or 0)),
            contractMultiplier=Decimal(str(getattr(info, "trade_contract_size", 0) or 0)),
            contractSize=Decimal(str(getattr(info, "trade_contract_size", 0) or 0)),
            trade_mode=str(int(getattr(info, "trade_mode", -1))),
            filling_mode=str(int(getattr(info, "filling_mode", -1))),
            accessChecks={
                "accountLoginMatched": actual_login == str(secret["LOGIN"]),
                "accountTradeAllowed": bool(getattr(account, "trade_allowed", False)),
                "terminalTradeAllowed": bool(getattr(terminal, "trade_allowed", False)),
                "accountExpertTradeAllowed": bool(getattr(account, "trade_expert", False)),
                "pythonTradeAllowed": getattr(terminal, "tradeapi_disabled", None) is False,
                "symbolVisible": bool(getattr(info, "visible", False)),
            },
            asOf=datetime.now(UTC),
            baseCurrency=str(getattr(info, "currency_base", "") or "") or None,
            quoteCurrency=str(getattr(info, "currency_profit", "") or "") or None,
            settlementCurrency=str(getattr(account, "currency", "") or "") or None,
            rawPayload={
                key: str(value)
                for key in (
                    "volume_min",
                    "volume_step",
                    "volume_max",
                    "trade_contract_size",
                    "point",
                    "currency_base",
                    "currency_profit",
                    "currency_margin",
                )
                if (value := getattr(info, key, None)) is not None
            },
        )

    def _snapshot(
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
        route = get_order_route(external_order_id=ticket, account_id=account) or fallback_route
        comment = str(getattr(row, "comment", "") or "")
        if route is None and comment:
            route = get_order_route(external_client_id=comment, account_id=account)
        route_symbol = route.symbol if route is not None else ""
        symbol = str(getattr(row, "symbol", route_symbol)).upper()
        mapped_instrument_id = (
            route.instrument_id if route is not None else self.settings.mt5_instruments.get(symbol)
        )
        instrument_id, quality = self._resolve_read_instrument(
            account_id=route.account_id if route is not None else account,
            symbol=symbol,
            instrument_id=mapped_instrument_id,
            prefer_route=route is not None,
        )
        state = int(getattr(row, "state", -1))
        status = self._status(mt5, state)
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
        external_identity = f"external:{self.name}:{account}:{ticket}"
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=ticket,
            platformOrderId=(route.platform_order_id if route is not None else external_identity),
            commandId=route.command_id if route is not None else external_identity,
            accountId=route.account_id if route is not None else account,
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
            asOf=datetime.now(UTC),
            dataQualityState=quality,
        )

    def _deal_snapshot(
        self,
        mt5,
        deal,
        account: str,
        *,
        fallback_route=None,
    ) -> VenueOrderSnapshot | None:
        deal_ticket = str(getattr(deal, "ticket", 0))
        order_ticket = str(getattr(deal, "order", 0) or deal_ticket)
        route = get_order_route(external_order_id=order_ticket, account_id=account)
        if route is None:
            route = (
                get_order_route(external_order_id=deal_ticket, account_id=account) or fallback_route
            )
        comment = str(getattr(deal, "comment", "") or "")
        if route is None and comment:
            route = get_order_route(external_client_id=comment, account_id=account)
        route_symbol = route.symbol if route is not None else ""
        symbol = str(getattr(deal, "symbol", route_symbol)).upper()
        mapped_instrument_id = (
            route.instrument_id if route is not None else self.settings.mt5_instruments.get(symbol)
        )
        instrument_id, quality = self._resolve_read_instrument(
            account_id=route.account_id if route is not None else account,
            symbol=symbol,
            instrument_id=mapped_instrument_id,
            prefer_route=route is not None,
        )
        quantity = Decimal(str(getattr(deal, "volume", 0) or 0))
        price = Decimal(str(getattr(deal, "price", 0) or 0))
        external_identity = f"external:{self.name}:{account}:{order_ticket}"
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=order_ticket,
            platformOrderId=(route.platform_order_id if route is not None else external_identity),
            commandId=route.command_id if route is not None else external_identity,
            accountId=route.account_id if route is not None else account,
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
            asOf=datetime.now(UTC),
            dataQualityState=quality,
        )

    def _fill_snapshot(
        self,
        mt5,
        deal,
        account: str,
        *,
        target: str | None,
        fallback_route=None,
    ) -> VenueFillSnapshot | None:
        deal_ticket = str(getattr(deal, "ticket", 0))
        order_ticket = str(getattr(deal, "order", 0) or deal_ticket)
        comment = str(getattr(deal, "comment", "") or "")
        if target is not None and target not in {deal_ticket, order_ticket}:
            if fallback_route is None or comment != fallback_route.external_client_id:
                return None
        route = get_order_route(external_order_id=order_ticket, account_id=account)
        if route is None:
            route = get_order_route(external_order_id=deal_ticket, account_id=account)
        if route is None and comment:
            route = get_order_route(external_client_id=comment, account_id=account)
        symbol = str(getattr(deal, "symbol", "")).upper()
        mapped_instrument_id = (
            route.instrument_id if route is not None else self.settings.mt5_instruments.get(symbol)
        )
        instrument_id, quality = self._resolve_read_instrument(
            account_id=route.account_id if route is not None else account,
            symbol=symbol,
            instrument_id=mapped_instrument_id,
            prefer_route=route is not None,
        )
        external_identity = f"external:{self.name}:{account}:{order_ticket}"
        return VenueFillSnapshot(
            source=self.name,
            externalFillId=deal_ticket,
            externalOrderId=order_ticket,
            platformOrderId=(route.platform_order_id if route is not None else external_identity),
            commandId=route.command_id if route is not None else external_identity,
            accountId=route.account_id if route is not None else account,
            instrumentId=instrument_id,
            symbol=symbol,
            side=(
                "buy"
                if int(getattr(deal, "type", -1)) == int(getattr(mt5, "DEAL_TYPE_BUY", 0))
                else "sell"
            ),
            quantity=Decimal(str(getattr(deal, "volume", 0))),
            price=Decimal(str(getattr(deal, "price", 0))),
            fee=-(
                Decimal(str(getattr(deal, "commission", 0) or 0))
                + Decimal(str(getattr(deal, "fee", 0) or 0))
            ),
            currency=self._account_currency(mt5),
            realizedPnl=Decimal(str(getattr(deal, "profit", 0) or 0)),
            swap=Decimal(str(getattr(deal, "swap", 0) or 0)),
            positionId=str(getattr(deal, "position_id", "") or "") or None,
            entryType=getattr(deal, "entry", None),
            occurredAt=self._deal_time(deal),
            dataQualityState=quality,
        )

    @staticmethod
    def _status(mt5, state: int) -> OrderStatus:
        return normalize_mt5_order_status(mt5, state)
