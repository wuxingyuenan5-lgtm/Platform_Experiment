from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, cast

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
    VenueAccountRiskSnapshot,
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.secret_resolver import inspect_credential_reference, resolve_secret_reference


class BybitLiveAdapter:
    name = "bybit_live"

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self._injected_client = client
        self._resolved_clients: dict[str, Any] = {}

    def capability(self) -> GatewayAdapterCapability:
        missing: list[str] = []
        for account_id in self.settings.bybit_accounts:
            inspection = inspect_credential_reference(
                self.settings.bybit_credential_for_account(account_id),
                required_fields=("API_KEY", "SECRET"),
            )
            missing.extend(f"{account_id}:{field}" for field in inspection.missing_fields)
        if not self.settings.bybit_accounts:
            missing.append("BYBIT_ACCOUNT_IDS")
        if not self.settings.bybit_instruments:
            missing.append("BYBIT_INSTRUMENT_MAP")
        configured = not missing
        operational = configured and self._dependency_available()
        if configured and not operational:
            missing.append("PYBIT_DEPENDENCY")
        return GatewayAdapterCapability(
            adapter=self.name,
            environment="live",
            configured=configured,
            operational=operational,
            writeEnabled=operational and self.settings.live_write_enabled,
            accountIds=sorted(self.settings.bybit_accounts),
            capabilities=[
                "order_query",
                "fill_query",
                "position_query",
                "balance_query",
                "funding_query",
                "submit_order_gated",
                "post_only_single_attempt_submit",
                "cancel_order_gated",
                "account_risk_query",
            ],
            missingRequirements=sorted(set(missing)),
        )

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        self._assert_account(command.account_id)
        self._assert_write_account(command.account_id)
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
        if command.order_type == "limit":
            if command.price is None:
                raise GatewayRequestRejectedError("Bybit limit order requires price")
            payload["price"] = format(command.price, "f")
            payload["timeInForce"] = (
                "PostOnly"
                if command.execution_policy == "post_only_single_attempt"
                else "GTC"
            )
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

    def set_leverage(self, *, account_id: str, symbol: str, leverage: Decimal) -> dict[str, object]:
        self._assert_account(account_id)
        self._assert_write_account(account_id)
        if leverage <= 0 or leverage > Decimal("100"):
            raise GatewayRequestRejectedError("Bybit leverage must be between 0 and 100")
        try:
            response = self._client(account_id).set_leverage(
                category=self.settings.bybit_category,
                symbol=symbol.upper(),
                buyLeverage=format(leverage, "f"),
                sellLeverage=format(leverage, "f"),
            )
            self._require_success(response, "Bybit rejected leverage update")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit leverage update result is unknown", exc) from exc
        return {"accountId": account_id, "symbol": symbol.upper(), "leverage": str(leverage), "source": self.name}

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
        client = self._client(route.account_id)
        query: dict[str, object] = {
            "category": self.settings.bybit_category,
            "symbol": route.symbol,
        }
        if route.external_order_id:
            query["orderId"] = route.external_order_id
        else:
            query["orderLinkId"] = route.external_client_id
        try:
            realtime = client.get_open_orders(**query)
            self._require_success(realtime, "Bybit order query failed")
            rows = self._result_list(realtime)
            if not rows:
                history = client.get_order_history(**query)
                self._require_success(history, "Bybit order history query failed")
                rows = self._result_list(history)
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit order query result is unknown", exc) from exc
        if not rows:
            return None
        return self._order_snapshot(rows[0], route)

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        if account_id is not None:
            self._assert_account(account_id)
        route = None
        if platform_order_id is not None or external_order_id is not None:
            route = self._resolve_route(
                platform_order_id=platform_order_id,
                external_order_id=external_order_id,
            )
        query: dict[str, object] = {"category": self.settings.bybit_category, "limit": 100}
        if route is not None:
            query["symbol"] = route.symbol
            if route.external_order_id:
                query["orderId"] = route.external_order_id
            else:
                query["orderLinkId"] = route.external_client_id
        try:
            client_account = account_id or (route.account_id if route else None)
            response = self._client(client_account).get_executions(**query)
            self._require_success(response, "Bybit execution query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit execution query result is unknown", exc) from exc
        snapshots: list[VenueFillSnapshot] = []
        default_account = account_id or self._single_account()
        for row in self._result_list(response):
            symbol = str(row.get("symbol") or "").upper()
            instrument_id = self.settings.bybit_instruments.get(symbol)
            if instrument_id is None:
                continue
            row_route = get_order_route(external_order_id=str(row.get("orderId") or ""))
            order_id = str(row.get("orderId") or "unknown")
            snapshots.append(
                VenueFillSnapshot(
                    source=self.name,
                    externalFillId=str(row.get("execId") or f"{order_id}:{row.get('execTime')}"),
                    externalOrderId=order_id,
                    platformOrderId=(
                        row_route.platform_order_id if row_route else f"external:{order_id}"
                    ),
                    commandId=(row_route.command_id if row_route else f"external:{order_id}"),
                    accountId=(row_route.account_id if row_route else default_account),
                    instrumentId=(row_route.instrument_id if row_route else instrument_id),
                    symbol=symbol,
                    side="buy" if str(row.get("side")) == "Buy" else "sell",
                    quantity=Decimal(str(row.get("execQty") or "0")),
                    price=Decimal(str(row.get("execPrice") or "0")),
                    fee=Decimal(str(row.get("execFee") or "0")),
                    currency=str(row.get("feeCurrency") or self.settings.bybit_settle_coin),
                    occurredAt=self._millis(row.get("execTime")),
                )
            )
        return snapshots

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        try:
            response = self._with_fresh_client_retry(account,
                lambda client: client.get_positions(
                    category=self.settings.bybit_category,
                    settleCoin=self.settings.bybit_settle_coin,
                )
            )
            self._require_success(response, "Bybit position query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit position query result is unknown", exc) from exc
        snapshots: list[VenuePositionSnapshot] = []
        for row in self._result_list(response):
            size = Decimal(str(row.get("size") or "0"))
            if size == 0:
                continue
            symbol = str(row.get("symbol") or "").upper()
            instrument_id = self.settings.bybit_instruments.get(symbol)
            if instrument_id is None:
                continue
            side = str(row.get("side") or "")
            quantity = size if side == "Buy" else -size
            snapshots.append(
                VenuePositionSnapshot(
                    source=self.name,
                    externalPositionId=f"{account}:{symbol}",
                    accountId=account,
                    instrumentId=instrument_id,
                    symbol=symbol,
                    netQuantity=quantity,
                    averagePrice=self._optional_decimal(row.get("avgPrice")),
                    currency=self.settings.bybit_settle_coin,
                    asOf=self._millis(row.get("updatedTime")),
                    openTime=self._micros(row.get("openTime")),
                )
            )
        return snapshots

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        try:
            response = self._with_fresh_client_retry(account,
                lambda client: client.get_wallet_balance(accountType="UNIFIED")
            )
            self._require_success(response, "Bybit wallet query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit wallet query result is unknown", exc) from exc
        result_rows = self._result_list(response)
        if not result_rows:
            return []
        account_row = result_rows[0]
        as_of = datetime.now(UTC)
        account_available = self._optional_decimal(account_row.get("totalAvailableBalance"))
        snapshots: list[VenueBalanceSnapshot] = []
        raw_coins = account_row.get("coin")
        coins = raw_coins if isinstance(raw_coins, list) else []
        for coin in coins:
            if not isinstance(coin, dict):
                continue
            currency = str(coin.get("coin") or "").upper()
            equity = Decimal(str(coin.get("equity") or "0"))
            wallet = Decimal(str(coin.get("walletBalance") or "0"))
            if equity == 0 and wallet == 0:
                continue
            snapshots.append(
                VenueBalanceSnapshot(
                    source=self.name,
                    externalBalanceId=f"{account}:{currency}:{int(as_of.timestamp())}",
                    accountId=account,
                    equity=equity,
                    availableBalance=self._available_balance(
                        coin,
                        account_available=account_available,
                    ),
                    currency=currency,
                    asOf=as_of,
                )
            )
        return snapshots

    def list_economic_events(
        self,
        *,
        account_id: str | None = None,
        instrument_id: str | None = None,
        event_type: str | None = None,
    ) -> list[VenueEconomicEventSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        if event_type not in {None, "funding", "fee"}:
            return []
        try:
            response = self._client(account).get_transaction_log(
                accountType="UNIFIED",
                category=self.settings.bybit_category,
                limit=50,
            )
            self._require_success(response, "Bybit transaction log query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit transaction log result is unknown", exc) from exc
        events: list[VenueEconomicEventSnapshot] = []
        for row in self._result_list(response):
            symbol = str(row.get("symbol") or "").upper()
            mapped_instrument = self.settings.bybit_instruments.get(symbol)
            if instrument_id is not None and mapped_instrument != instrument_id:
                continue
            occurred_at = self._millis(row.get("transactionTime"))
            funding = Decimal(str(row.get("funding") or "0"))
            if funding != 0 and event_type in {None, "funding"}:
                events.append(
                    VenueEconomicEventSnapshot(
                        source=self.name,
                        externalEventId=(
                            f"funding:{row.get('id') or row.get('tradeId') or row.get('transactionTime')}"
                        ),
                        eventType="funding",
                        accountId=account,
                        instrumentId=mapped_instrument,
                        symbol=symbol or None,
                        amount=funding,
                        currency=str(row.get("currency") or self.settings.bybit_settle_coin),
                        occurredAt=occurred_at,
                        payload=dict(row),
                    )
                )
            fee = Decimal(str(row.get("fee") or "0"))
            if fee != 0 and event_type in {None, "fee"}:
                events.append(
                    VenueEconomicEventSnapshot(
                        source=self.name,
                        externalEventId=(
                            f"fee:{row.get('id') or row.get('tradeId') or row.get('transactionTime')}"
                        ),
                        eventType="fee",
                        accountId=account,
                        instrumentId=mapped_instrument,
                        symbol=symbol or None,
                        amount=-fee,
                        currency=str(row.get("currency") or self.settings.bybit_settle_coin),
                        occurredAt=occurred_at,
                        payload=dict(row),
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
        self._assert_write_account(route.account_id)
        validate_live_cancel(route, self.settings)
        try:
            response = self._client(route.account_id).cancel_order(
                category=self.settings.bybit_category,
                symbol=route.symbol,
                orderId=external_order_id,
                orderLinkId=route.external_client_id,
            )
        except Exception as exc:
            raise self._unknown_error("Bybit cancel result is unknown", exc) from exc
        self._require_success(response, "Bybit cancel rejected")
        return CancelOrderResponse(
            source=self.name,
            externalOrderId=external_order_id,
            platformOrderId=route.platform_order_id,
            status="canceled",
            reason=reason,
            asOf=datetime.now(UTC),
        )

    def get_account_snapshot(self, account_id: str) -> VenueAccountSnapshot:
        self._assert_account(account_id)
        balances = self.list_balances(account_id)
        categories = self.settings.bybit_categories_for_account(account_id)
        positions: list[VenuePositionSnapshot] = []
        orders_by_id: dict[str, VenueOrderSnapshot] = {}
        fills_by_id: dict[str, VenueFillSnapshot] = {}
        for category in categories:
            position_response = self._with_fresh_client_retry(
                account_id,
                lambda refreshed, current_category=category: refreshed.get_positions(
                    category=current_category,
                    settleCoin=self.settings.bybit_settle_coin,
                    limit=200,
                ),
            )
            self._require_success(position_response, "Bybit position query failed")
            for row in self._result_list(position_response):
                size = Decimal(str(row.get("size") or "0"))
                if size == 0:
                    continue
                symbol = str(row.get("symbol") or "").upper()
                instrument_id = self.settings.bybit_instruments.get(symbol)
                if instrument_id is None:
                    continue
                side = str(row.get("side") or "")
                quantity = size if side == "Buy" else -size
                positions.append(
                    VenuePositionSnapshot(
                        source=self.name,
                        externalPositionId=f"{account_id}:{category}:{symbol}:{row.get('positionIdx', 0)}",
                        accountId=account_id,
                        instrumentId=instrument_id,
                        symbol=symbol,
                        netQuantity=quantity,
                        averagePrice=self._optional_decimal(row.get("avgPrice")),
                        currentPrice=self._optional_decimal(row.get("markPrice")),
                        markPrice=self._optional_decimal(row.get("markPrice")),
                        unrealizedPnl=self._optional_decimal(row.get("unrealisedPnl")),
                        currency=self.settings.bybit_settle_coin,
                        asOf=self._millis(row.get("updatedTime")),
                    )
                )
            for query_name in ("get_open_orders", "get_order_history"):
                response = self._with_fresh_client_retry(
                    account_id,
                    lambda refreshed, method_name=query_name, current_category=category: getattr(
                        refreshed,
                        method_name,
                    )(
                        **self._account_snapshot_order_query_kwargs(current_category, limit=100),
                    ),
                )
                self._require_success(response, "Bybit order snapshot query failed")
                for row in self._result_list(response):
                    status_map: dict[
                        str,
                        Literal[
                            "accepted",
                            "partially_filled",
                            "filled",
                            "canceled",
                            "rejected",
                            "unknown",
                        ],
                    ] = {
                        "New": "accepted",
                        "Created": "accepted",
                        "PartiallyFilled": "partially_filled",
                        "Filled": "filled",
                        "Cancelled": "canceled",
                        "Canceled": "canceled",
                        "Rejected": "rejected",
                    }
                    symbol = str(row.get("symbol") or "").upper()
                    instrument_id = self.settings.bybit_instruments.get(symbol)
                    if instrument_id is None:
                        continue
                    external_order_id = str(row.get("orderId") or "")
                    route = get_order_route(external_order_id=external_order_id) or get_order_route(
                        external_client_id=str(row.get("orderLinkId") or "")
                    )
                    platform_order_id = (
                        route.platform_order_id
                        if route is not None
                        else f"external:{self.name}:{external_order_id}"
                    )
                    command_id = route.command_id if route is not None else platform_order_id
                    orders_by_id[external_order_id] = VenueOrderSnapshot(
                        source=self.name,
                        externalOrderId=external_order_id,
                        platformOrderId=platform_order_id,
                        commandId=command_id,
                        accountId=route.account_id if route is not None else account_id,
                        instrumentId=route.instrument_id if route is not None else instrument_id,
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
                        dataQualityState="complete" if route is not None else "external_only",
                    )
            execution_response = self._with_fresh_client_retry(
                account_id,
                lambda refreshed, current_category=category: refreshed.get_executions(
                    **self._account_snapshot_order_query_kwargs(current_category, limit=200),
                ),
            )
            self._require_success(execution_response, "Bybit execution query failed")
            for row in self._result_list(execution_response):
                symbol = str(row.get("symbol") or "").upper()
                instrument_id = self.settings.bybit_instruments.get(symbol)
                if instrument_id is None:
                    continue
                external_order_id = str(row.get("orderId") or "unknown")
                external_fill_id = str(row.get("execId") or f"{external_order_id}:{row.get('execTime')}")
                route = get_order_route(external_order_id=external_order_id)
                platform_order_id = (
                    route.platform_order_id
                    if route is not None
                    else f"external:{self.name}:{external_order_id}"
                )
                command_id = route.command_id if route is not None else platform_order_id
                fills_by_id[external_fill_id] = VenueFillSnapshot(
                    source=self.name,
                    externalFillId=external_fill_id,
                    externalOrderId=external_order_id,
                    platformOrderId=platform_order_id,
                    commandId=command_id,
                    accountId=route.account_id if route is not None else account_id,
                    instrumentId=route.instrument_id if route is not None else instrument_id,
                    symbol=symbol,
                    side="buy" if str(row.get("side")) == "Buy" else "sell",
                    quantity=Decimal(str(row.get("execQty") or "0")),
                    price=Decimal(str(row.get("execPrice") or "0")),
                    fee=Decimal(str(row.get("execFee") or "0")),
                    currency=str(row.get("feeCurrency") or self.settings.bybit_settle_coin),
                    occurredAt=self._millis(row.get("execTime")),
                    dataQualityState="complete" if route is not None else "external_only",
                )
        risk = (
            cast(Any, self).get_account_risk(account_id)
            if hasattr(self, "get_account_risk")
            else VenueAccountRiskSnapshot(
                source=self.name,
                accountId=account_id,
                currency=self.settings.bybit_settle_coin,
                equity=balances[0].equity if balances else None,
                availableBalance=balances[0].available_balance if balances else None,
                asOf=datetime.now(UTC),
                dataQualityState="partial",
            )
        )
        return VenueAccountSnapshot(
            source=self.name,
            accountId=account_id,
            venue="bybit",
            identity={
                "accountId": account_id,
                "categories": "|".join(categories),
                "credentialRef": self.settings.bybit_credential_for_account(account_id),
            },
            balances=balances,
            positions=positions,
            orders=sorted(orders_by_id.values(), key=lambda item: item.as_of, reverse=True),
            fills=sorted(fills_by_id.values(), key=lambda item: item.occurred_at, reverse=True),
            accountRisk=risk,
            asOf=risk.as_of,
            dataQualityState=risk.data_quality_state,
        )

    def _account_snapshot_order_query_kwargs(
        self,
        category: str,
        *,
        limit: int,
    ) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "category": category,
            "limit": limit,
        }
        if category in {"linear", "inverse"}:
            kwargs["settleCoin"] = self.settings.bybit_settle_coin
        return kwargs

    def _client(self, account_id: str | None = None):
        if self._injected_client is not None:
            return self._injected_client
        account = account_id or self._single_account()
        if account in self._resolved_clients:
            return self._resolved_clients[account]
        try:
            from pybit import _helpers
            from pybit.unified_trading import HTTP
        except ImportError as exc:
            raise GatewayConfigurationError("pybit dependency is not installed") from exc
        self._apply_timestamp_offset(_helpers)
        try:
            secret = resolve_secret_reference(
                self.settings.bybit_credential_for_account(account),
                required_fields=("API_KEY", "SECRET"),
            )
        except ValueError as exc:
            raise GatewayConfigurationError(str(exc)) from exc
        self._resolved_clients[account] = HTTP(
            testnet=False,
            demo=False,
            api_key=secret["API_KEY"],
            api_secret=secret["SECRET"],
            recv_window=self.settings.bybit_recv_window,
        )
        return self._resolved_clients[account]

    def _with_fresh_client_retry(self, account_id_or_operation, operation=None):
        if operation is None:
            account_id = self._single_account()
            operation = account_id_or_operation
        else:
            account_id = account_id_or_operation
        try:
            return operation(self._client(account_id))
        except Exception:
            if self._injected_client is not None:
                raise
            self._resolved_clients.pop(account_id, None)
            return operation(self._client(account_id))

    def _apply_timestamp_offset(self, helpers) -> None:
        raw_offset = getattr(self.settings, "bybit_timestamp_offset_ms", 0)
        offset_ms = int(cast(str | int | float, raw_offset or 0))
        if offset_ms == 0:
            return
        original = getattr(helpers, "_vg_original_generate_timestamp", None)
        if original is None:
            original = helpers.generate_timestamp
            helpers._vg_original_generate_timestamp = original
        helpers.generate_timestamp = lambda: original() + offset_ms

    def _assert_account(self, account_id: str) -> None:
        if account_id not in self.settings.bybit_accounts:
            raise GatewayConfigurationError("Account is not mapped to Bybit live adapter")

    def _assert_write_account(self, account_id: str) -> None:
        if account_id in self.settings.bybit_read_only_accounts:
            raise GatewayRequestRejectedError("Bybit account is configured read-only")

    def _single_account(self) -> str:
        accounts = sorted(self.settings.bybit_accounts)
        if len(accounts) != 1:
            raise GatewayConfigurationError("Bybit query requires an explicit accountId")
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

    def _market_reference_price(self, client, command: SubmitOrderCommand) -> Decimal:
        try:
            response = client.get_tickers(
                category=self.settings.bybit_category,
                symbol=command.symbol.upper(),
            )
            self._require_success(response, "Bybit ticker query failed")
            rows = self._result_list(response)
            if not rows:
                raise GatewayConfigurationError("Bybit ticker query returned no data")
            row = rows[0]
            price = row.get("markPrice") or row.get("lastPrice") or row.get("indexPrice")
            return Decimal(str(price))
        except GatewayConfigurationError:
            raise
        except Exception as exc:
            raise GatewayConfigurationError("Unable to obtain Bybit reference price") from exc

    def _order_snapshot(self, row: dict[str, object], route) -> VenueOrderSnapshot:
        status_map: dict[
            str,
            Literal["accepted", "partially_filled", "filled", "canceled", "rejected", "unknown"],
        ] = {
            "New": "accepted",
            "Created": "accepted",
            "PartiallyFilled": "partially_filled",
            "Filled": "filled",
            "Cancelled": "canceled",
            "Canceled": "canceled",
            "Rejected": "rejected",
        }
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=str(row.get("orderId") or route.external_order_id or "unknown"),
            platformOrderId=route.platform_order_id,
            commandId=route.command_id,
            accountId=route.account_id,
            instrumentId=route.instrument_id,
            symbol=route.symbol,
            side="buy" if str(row.get("side")) == "Buy" else "sell",
            orderType="market" if str(row.get("orderType")) == "Market" else "limit",
            quantity=Decimal(str(row.get("qty") or "0")),
            price=self._optional_decimal(row.get("price")),
            status=status_map.get(str(row.get("orderStatus")), "unknown"),
            filledQuantity=Decimal(str(row.get("cumExecQty") or "0")),
            averageFillPrice=self._optional_decimal(row.get("avgPrice")),
            occurredAt=self._millis(row.get("createdTime")),
            asOf=self._millis(row.get("updatedTime")),
        )

    @staticmethod
    def _require_success(response: dict[str, object], message: str) -> None:
        raw_code = response.get("retCode")
        code = int(cast(str | int | float, raw_code or 0))
        if code != 0:
            detail = str(response.get("retMsg") or message)
            raise GatewayRequestRejectedError(f"{message}: {detail}")

    @staticmethod
    def _unknown_error(message: str, exc: Exception) -> GatewayResultUnknownError:
        detail = str(exc).strip()
        if detail:
            return GatewayResultUnknownError(
                f"{message}: {exc.__class__.__name__}: {detail}"
            )
        return GatewayResultUnknownError(f"{message}: {exc.__class__.__name__}")

    @staticmethod
    def _result_list(response: dict[str, object]) -> list[dict[str, object]]:
        result = response.get("result") or {}
        rows = result.get("list") if isinstance(result, dict) else None
        return list(rows or [])

    @staticmethod
    def _optional_decimal(value: object) -> Decimal | None:
        if value in {None, ""}:
            return None
        return Decimal(str(value))

    @staticmethod
    def _available_balance(
        coin: dict[str, object],
        *,
        account_available: Decimal | None,
    ) -> Decimal:
        coin_available = coin.get("availableToWithdraw") or coin.get("availableToBorrow")
        if coin_available in {None, ""} and account_available is not None:
            return account_available
        coin_available = coin_available or coin.get("walletBalance") or "0"
        parsed = Decimal(str(coin_available))
        if parsed == 0 and account_available is not None:
            return account_available
        return parsed

    @staticmethod
    def _millis(value: object) -> datetime:
        if value in {None, ""}:
            return datetime.now(UTC)
        timestamp_ms = int(cast(str | int | float, value))
        return datetime.fromtimestamp(timestamp_ms / 1000, UTC)

    def _micros(self, value: object) -> datetime | None:
        if value in {None, ""}:
            return None
        try:
            return datetime.fromtimestamp(int(str(value)) / 1_000_000, UTC)
        except (TypeError, ValueError, OSError):
            return None

    def _dependency_available(self) -> bool:
        if self._injected_client is not None:
            return True
        try:
            import pybit  # noqa: F401
        except ImportError:
            return False
        return True
