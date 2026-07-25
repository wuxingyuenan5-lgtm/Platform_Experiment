from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.bybit_fill_confirming_adapter import BybitFillConfirmingAdapter
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


class BybitAcceptanceAdapter(BybitFillConfirmingAdapter):
    """Route-independent Bybit reads used during bounded live acceptance."""

    def capability(self) -> GatewayAdapterCapability:
        capability = super().capability()
        capability.capabilities.extend(
            ["order_list", "instrument_specification_query", "api_key_readiness_query"]
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
        rows = self._query_order_rows(query)
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
            active = self._client().get_open_orders(openOnly=0, **query)
            self._require_success(active, "Bybit active-order query failed")
            history = self._client().get_order_history(**query)
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
            response = self._client().get_executions(**query)
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

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
    ) -> VenueInstrumentSpecification:
        self._assert_account(account_id)
        normalized = symbol.upper()
        instrument_id = self.settings.bybit_instruments.get(normalized)
        if instrument_id is None:
            raise GatewayConfigurationError(
                "Bybit symbol is not mapped to a Platform instrument"
            )
        try:
            response = self._client().get_instruments_info(
                category=self.settings.bybit_category,
                symbol=normalized,
            )
            self._require_success(response, "Bybit instrument query failed")
            rows = self._result_list(response)
            if not rows:
                raise GatewayConfigurationError(
                    "Bybit instrument query returned no data"
                )
            api_response = self._client().get_api_key_information()
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
            symbol=normalized,
            status=str(row.get("status") or "unknown"),
            minQuantity=Decimal(str(lot.get("minOrderQty") or "0")),
            quantityStep=Decimal(str(lot.get("qtyStep") or "0")),
            maxMarketQuantity=self._optional_decimal(maximum),
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

    def _query_order_rows(
        self,
        query: dict[str, object],
    ) -> list[dict[str, object]]:
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
        status_map = {
            "New": "accepted",
            "Created": "accepted",
            "PartiallyFilled": "partially_filled",
            "Filled": "filled",
            "Cancelled": "canceled",
            "Canceled": "canceled",
            "Rejected": "rejected",
        }
        external_identity = f"external:{self.name}:{order_id}"
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
            quantity=Decimal(str(row.get("qty") or "0")),
            price=self._optional_decimal(row.get("price")),
            status=status_map.get(str(row.get("orderStatus")), "unknown"),
            filledQuantity=Decimal(str(row.get("cumExecQty") or "0")),
            averageFillPrice=self._optional_decimal(row.get("avgPrice")),
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

    def _assert_no_existing_position(self, symbol: str) -> None:
        maximum = self.settings.live_acceptance_max_positions_per_symbol
        if maximum <= 0:
            raise GatewayConfigurationError(
                "Live acceptance position limit is not configured"
            )
        try:
            response = self._client().get_positions(
                category=self.settings.bybit_category,
                symbol=symbol.upper(),
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
