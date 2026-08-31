from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from app.bybit_fill_confirming_adapter import BybitFillConfirmingAdapter
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.live_route_store import get_order_route
from app.models import (
    GatewayAdapterCapability,
    VenueAccountRiskSnapshot,
    VenueFillHistoryPage,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueOrderHistoryPage,
    VenueOrderSnapshot,
)
from app.order_semantics import normalize_bybit_order_status


class BybitAcceptanceAdapter(BybitFillConfirmingAdapter):
    """Route-independent Bybit reads used during bounded live acceptance."""

    def capability(self) -> GatewayAdapterCapability:
        capability = super().capability()
        capability.capabilities.extend(
            [
                "order_list",
                "paged_order_history",
                "paged_fill_history",
                "account_risk_query",
                "instrument_specification_query",
                "api_key_readiness_query",
            ]
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
        rows = self._query_order_rows(account, query)
        if not rows:
            return None
        return self._snapshot(rows[0], account)

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
            active = self._with_fresh_client_retry(
                account,
                lambda client: client.get_open_orders(openOnly=0, **query)
            )
            self._require_success(active, "Bybit active-order query failed")
            history = self._with_fresh_client_retry(
                account,
                lambda client: client.get_order_history(**query)
            )
            self._require_success(history, "Bybit order-history query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit order-list result is unknown") from exc

        merged: dict[str, dict[str, object]] = {}
        for row in [*self._result_list(active), *self._result_list(history)]:
            order_id = str(row.get("orderId") or "")
            if order_id and order_id not in merged:
                merged[order_id] = row
        snapshots: list[VenueOrderSnapshot] = []
        for row in merged.values():
            snapshot = self._snapshot(row, account)
            if snapshot is not None:
                snapshots.append(snapshot)
        snapshots.sort(key=lambda item: item.as_of, reverse=True)
        return snapshots[:bounded_limit]

    def query_order_history(
        self,
        *,
        account_id: str,
        symbol: str | None,
        start_time: datetime,
        end_time: datetime,
        cursor: str | None,
        limit: int,
        scope: Literal["active", "closed"],
    ) -> VenueOrderHistoryPage:
        self._assert_account(account_id)
        bounded_limit = max(1, min(limit, 50))
        query: dict[str, object] = {
            "category": self.settings.bybit_category,
            "limit": bounded_limit,
        }
        if symbol:
            query["symbol"] = symbol.upper()
        if cursor:
            query["cursor"] = cursor
        try:
            if scope == "active":
                response = self._with_fresh_client_retry(
                    account_id,
                    lambda client: client.get_open_orders(openOnly=0, **query)
                )
                quality = "complete"
            else:
                query["startTime"] = int(start_time.timestamp() * 1000)
                query["endTime"] = int(end_time.timestamp() * 1000)
                response = self._with_fresh_client_retry(
                    account_id,
                    lambda client: client.get_order_history(**query)
                )
                quality = "venue_windowed"
            self._require_success(response, "Bybit paged order query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit paged order result is unknown") from exc
        items = [
            snapshot
            for row in self._result_list(response)
            if (snapshot := self._snapshot(row, account_id)) is not None
        ]
        return VenueOrderHistoryPage(
            source=self.name,
            accountId=account_id,
            items=items,
            nextCursor=self._next_cursor(response),
            startTime=start_time,
            endTime=end_time,
            dataQualityState=quality,
        )

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
        query: dict[str, object] = {
            "category": self.settings.bybit_category,
            "limit": 100,
        }
        if route is not None:
            query["symbol"] = route.symbol
            if route.external_order_id:
                query["orderId"] = route.external_order_id
            else:
                query["orderLinkId"] = route.external_client_id
        elif external_order_id is not None:
            query["orderId"] = external_order_id
        try:
            response = self._with_fresh_client_retry(
                account,
                lambda client: client.get_executions(**query)
            )
            self._require_success(response, "Bybit execution query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit execution query result is unknown") from exc

        snapshots: list[VenueFillSnapshot] = []
        for row in self._result_list(response):
            snapshot = self._fill_snapshot(row, account)
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots

    def query_fill_history(
        self,
        *,
        account_id: str,
        symbol: str | None,
        start_time: datetime,
        end_time: datetime,
        cursor: str | None,
        limit: int,
    ) -> VenueFillHistoryPage:
        self._assert_account(account_id)
        query: dict[str, object] = {
            "category": self.settings.bybit_category,
            "limit": max(1, min(limit, 100)),
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
        }
        if symbol:
            query["symbol"] = symbol.upper()
        if cursor:
            query["cursor"] = cursor
        try:
            response = self._with_fresh_client_retry(
                account_id,
                lambda client: client.get_executions(**query)
            )
            self._require_success(response, "Bybit paged execution query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit paged execution result is unknown") from exc
        items = [
            snapshot
            for row in self._result_list(response)
            if (snapshot := self._fill_snapshot(row, account_id)) is not None
        ]
        return VenueFillHistoryPage(
            source=self.name,
            accountId=account_id,
            items=items,
            nextCursor=self._next_cursor(response),
            startTime=start_time,
            endTime=end_time,
            dataQualityState="venue_windowed",
        )

    def get_account_risk(self, account_id: str) -> VenueAccountRiskSnapshot:
        self._assert_account(account_id)
        try:
            response = self._with_fresh_client_retry(
                account_id,
                lambda client: client.get_wallet_balance(accountType="UNIFIED")
            )
            self._require_success(response, "Bybit account-risk query failed")
            rows = self._result_list(response)
            if not rows:
                raise GatewayConfigurationError("Bybit account-risk query returned no data")
            account_response = self._with_fresh_client_retry(
                account_id,
                lambda client: (
                    client.get_account_info()
                    if callable(getattr(client, "get_account_info", None))
                    else {}
                )
            )
            if account_response:
                self._require_success(account_response, "Bybit margin-mode query failed")
        except (GatewayConfigurationError, GatewayRequestRejectedError):
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit account-risk result is unknown") from exc
        row = rows[0]
        account_result = account_response.get("result") if account_response else {}
        if not isinstance(account_result, dict):
            account_result = {}
        return VenueAccountRiskSnapshot(
            source=self.name,
            accountId=account_id,
            currency="USD",
            equity=self._optional_decimal(row.get("totalEquity")),
            walletBalance=self._optional_decimal(row.get("totalWalletBalance")),
            marginBalance=self._optional_decimal(row.get("totalMarginBalance")),
            availableBalance=self._optional_decimal(row.get("totalAvailableBalance")),
            initialMargin=self._optional_decimal(row.get("totalInitialMargin")),
            maintenanceMargin=self._optional_decimal(row.get("totalMaintenanceMargin")),
            unrealizedPnl=self._optional_decimal(row.get("totalPerpUPL")),
            accountImRate=self._optional_decimal(row.get("accountIMRate")),
            accountMmRate=self._optional_decimal(row.get("accountMMRate")),
            marginMode=str(account_result.get("marginMode") or "UNIFIED"),
            tradeAllowed=True,
            expertTradingAllowed=True,
            fieldAvailability={
                "marginCallLevel": "not_reported_by_bybit_uta",
                "stopOutLevel": "not_reported_by_bybit_uta",
                "liquidationPrice": "reported_per_position_when_finite",
            },
            asOf=datetime.now(UTC),
        )

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None = None,
        category: str | None = None,
    ) -> VenueInstrumentSpecification:
        self._assert_account(account_id)
        normalized = symbol.upper()
        resolved_instrument_type, resolved_category = self._market_identity(
            account_id=account_id,
            symbol=normalized,
            instrument_type=instrument_type,
            category=category,
        )
        instrument_id = self._instrument_id_for_symbol(
            account_id=account_id,
            symbol=normalized,
            instrument_type=resolved_instrument_type,
            category=resolved_category,
        )
        try:
            response = self._with_fresh_client_retry(
                account_id,
                lambda client: client.get_instruments_info(
                    category=resolved_category,
                    symbol=normalized,
                )
            )
            self._require_success(response, "Bybit instrument query failed")
            rows = self._result_list(response)
            if not rows:
                raise GatewayConfigurationError(
                    "Bybit instrument query returned no data"
                )
            api_response = self._with_fresh_client_retry(
                account_id,
                lambda client: client.get_api_key_information()
            )
            self._require_success(api_response, "Bybit API-key readiness query failed")
        except (GatewayConfigurationError, GatewayRequestRejectedError):
            raise
        except Exception as exc:
            raise GatewayResultUnknownError(
                "Bybit instrument query result is unknown"
            ) from exc

        row = rows[0]
        lot = row.get("lotSizeFilter") or {}
        api_result = api_response.get("result") or {}
        permissions = api_result.get("permissions") or {}
        contract_permissions = permissions.get("ContractTrade") or []
        maximum = lot.get("maxMktOrderQty") or lot.get("maxMarketOrderQty")
        return VenueInstrumentSpecification(
            source=self.name,
            accountId=account_id,
            instrumentId=instrument_id,
            instrumentType=resolved_instrument_type,
            category=resolved_category,
            symbol=normalized,
            status=str(row.get("status") or "unknown"),
            priceTick=Decimal(str((row.get("priceFilter") or {}).get("tickSize") or "0")),
            minQuantity=Decimal(str(lot.get("minOrderQty") or "0")),
            quantityStep=Decimal(str(lot.get("qtyStep") or "0")),
            maxMarketQuantity=self._optional_decimal(maximum),
            contractMultiplier=Decimal("1"),
            contractSize=Decimal("1"),
            trade_mode=resolved_category,
            filling_mode="market",
            accessChecks={
                "readOnly": int(api_result.get("readOnly") or 0) == 1,
                "ipBound": bool(api_result.get("ips") or []),
                "orderPermission": "Order" in contract_permissions,
                "positionPermission": "Position" in contract_permissions,
            },
            asOf=datetime.now(UTC),
        )

    def _query_order_rows(
        self,
        account_id: str,
        query: dict[str, object],
    ) -> list[dict[str, object]]:
        try:
            realtime = self._with_fresh_client_retry(
                account_id,
                lambda client: client.get_open_orders(**query)
            )
            self._require_success(realtime, "Bybit order query failed")
            rows = self._result_list(realtime)
            if not rows:
                history = self._with_fresh_client_retry(
                    account_id,
                    lambda client: client.get_order_history(**query)
                )
                self._require_success(history, "Bybit order history query failed")
                rows = self._result_list(history)
            return rows
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("Bybit order query result is unknown") from exc

    def _snapshot(
        self,
        row: dict[str, object],
        account: str,
    ) -> VenueOrderSnapshot | None:
        order_id = str(row.get("orderId") or "")
        if not order_id:
            return None
        route = get_order_route(external_order_id=order_id)
        if route is None:
            link_id = str(row.get("orderLinkId") or "")
            if link_id:
                route = get_order_route(external_client_id=link_id)
        route_symbol = route.symbol if route is not None else ""
        symbol = str(row.get("symbol") or route_symbol).upper()
        instrument_id = (
            route.instrument_id
            if route is not None
            else self.settings.bybit_instruments.get(symbol)
        )
        if instrument_id is None:
            return None
        external_identity = f"external:{self.name}:{order_id}"
        quantity = Decimal(str(row.get("qty") or "0"))
        filled = Decimal(str(row.get("cumExecQty") or "0"))
        remaining = max(Decimal("0"), quantity - filled)
        position_index = row.get("positionIdx")
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=order_id,
            platformOrderId=(
                route.platform_order_id if route is not None else external_identity
            ),
            commandId=route.command_id if route is not None else external_identity,
            accountId=route.account_id if route is not None else account,
            instrumentId=instrument_id,
            symbol=symbol,
            side="buy" if str(row.get("side")) == "Buy" else "sell",
            orderType=(
                "market" if str(row.get("orderType")) == "Market" else "limit"
            ),
            quantity=quantity,
            price=self._optional_decimal(row.get("price")),
            status=normalize_bybit_order_status(row.get("orderStatus")),
            filledQuantity=filled,
            remainingQuantity=remaining,
            averageFillPrice=self._optional_decimal(row.get("avgPrice")),
            externalClientId=str(row.get("orderLinkId") or "") or None,
            reduceOnly=(bool(row.get("reduceOnly")) if "reduceOnly" in row else None),
            positionIndex=(int(position_index) if position_index is not None else None),
            timeInForce=str(row.get("timeInForce") or "") or None,
            rejectReason=str(row.get("rejectReason") or "") or None,
            cancelReason=str(row.get("cancelType") or "") or None,
            occurredAt=self._millis(row.get("createdTime")),
            asOf=self._millis(row.get("updatedTime")),
            dataQualityState="complete" if route is not None else "external_only",
        )

    def _fill_snapshot(
        self,
        row: dict[str, object],
        account: str,
    ) -> VenueFillSnapshot | None:
        order_id = str(row.get("orderId") or "unknown")
        route = get_order_route(external_order_id=order_id)
        if route is None:
            link_id = str(row.get("orderLinkId") or "")
            if link_id:
                route = get_order_route(external_client_id=link_id)
        symbol = str(row.get("symbol") or "").upper()
        instrument_id = (
            route.instrument_id
            if route is not None
            else self.settings.bybit_instruments.get(symbol)
        )
        if instrument_id is None:
            return None
        external_identity = f"external:{self.name}:{order_id}"
        return VenueFillSnapshot(
            source=self.name,
            externalFillId=str(
                row.get("execId") or f"{order_id}:{row.get('execTime')}"
            ),
            externalOrderId=order_id,
            platformOrderId=(
                route.platform_order_id if route is not None else external_identity
            ),
            commandId=route.command_id if route is not None else external_identity,
            accountId=route.account_id if route is not None else account,
            instrumentId=instrument_id,
            symbol=symbol,
            side="buy" if str(row.get("side")) == "Buy" else "sell",
            quantity=Decimal(str(row.get("execQty") or "0")),
            price=Decimal(str(row.get("execPrice") or "0")),
            fee=Decimal(str(row.get("execFee") or "0")),
            currency=str(row.get("feeCurrency") or self.settings.bybit_settle_coin),
            occurredAt=self._millis(row.get("execTime")),
            dataQualityState="complete" if route is not None else "external_only",
        )

    @staticmethod
    def _next_cursor(response: dict[str, object]) -> str | None:
        result = response.get("result") or {}
        if not isinstance(result, dict):
            return None
        cursor = str(result.get("nextPageCursor") or "")
        return cursor or None

    def _assert_no_existing_position(self, symbol: str) -> None:
        maximum = self.settings.live_acceptance_max_positions_per_symbol
        if maximum <= 0:
            # Legacy position-count cap is disabled: zero means "no cap".
            return
        try:
            response = self._with_fresh_client_retry(
                lambda client: client.get_positions(
                    category=self.settings.bybit_category,
                    symbol=symbol.upper(),
                )
            )
            self._require_success(response, "Bybit pre-trade position query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError(
                "Bybit pre-trade position result is unknown"
            ) from exc
        active = sum(
            1
            for row in self._result_list(response)
            if Decimal(str(row.get("size") or "0")) != 0
        )
        if active >= maximum:
            raise GatewayRequestRejectedError(
                "Live acceptance position limit is already reached"
            )
