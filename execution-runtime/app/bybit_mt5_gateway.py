from __future__ import annotations

from app.bybit_fill_confirming_adapter import BybitFillConfirmingAdapter
from app.bybit_live_adapter import BybitLiveAdapter
from app.config import Settings, get_settings
from app.gateway_errors import GatewayConfigurationError
from app.live_route_store import get_order_route
from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayCapabilitiesResponse,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.mt5_live_adapter import Mt5LiveAdapter


class BybitMt5Gateway:
    """Account-routed live gateway with independent Bybit and MT5 adapters."""

    # Keep the registered gateway identity stable for configuration and API compatibility.
    # Whether external writes are allowed is governed by the independent live safety gates.
    name = "bybit_mt5"

    def __init__(
        self,
        settings: Settings | None = None,
        bybit: BybitLiveAdapter | None = None,
        mt5: Mt5LiveAdapter | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.bybit = bybit or BybitFillConfirmingAdapter(self.settings)
        self.mt5 = mt5 or Mt5LiveAdapter(self.settings)

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        return self._adapter_for_account(command.account_id).submit_order(command)

    def get_order(
        self,
        *,
        platform_order_id: str | None = None,
        external_order_id: str | None = None,
    ) -> VenueOrderSnapshot | None:
        if platform_order_id is not None:
            route = get_order_route(platform_order_id=platform_order_id)
        elif external_order_id is not None:
            route = get_order_route(external_order_id=external_order_id)
        else:
            raise ValueError("Order identity is required")
        if route is None:
            return None
        return self._adapter_by_name(route.adapter).get_order(
            platform_order_id=platform_order_id,
            external_order_id=external_order_id,
        )

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        if account_id is not None:
            return self._adapter_for_account(account_id).list_fills(
                account_id=account_id,
                external_order_id=external_order_id,
                platform_order_id=platform_order_id,
            )
        if platform_order_id is not None:
            route = get_order_route(platform_order_id=platform_order_id)
            if route is None:
                return []
            return self._adapter_by_name(route.adapter).list_fills(
                platform_order_id=platform_order_id,
            )
        if external_order_id is not None:
            route = get_order_route(external_order_id=external_order_id)
            if route is None:
                return []
            return self._adapter_by_name(route.adapter).list_fills(
                external_order_id=external_order_id,
            )
        return [*self.bybit.list_fills(), *self.mt5.list_fills()]

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        if account_id is not None:
            return self._adapter_for_account(account_id).list_positions(account_id)
        return [*self.bybit.list_positions(), *self.mt5.list_positions()]

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        if account_id is not None:
            return self._adapter_for_account(account_id).list_balances(account_id)
        return [*self.bybit.list_balances(), *self.mt5.list_balances()]

    def list_economic_events(
        self,
        *,
        account_id: str | None = None,
        instrument_id: str | None = None,
        event_type: str | None = None,
    ) -> list[VenueEconomicEventSnapshot]:
        if account_id is not None:
            return self._adapter_for_account(account_id).list_economic_events(
                account_id=account_id,
                instrument_id=instrument_id,
                event_type=event_type,
            )
        return [
            *self.bybit.list_economic_events(
                instrument_id=instrument_id,
                event_type=event_type,
            ),
            *self.mt5.list_economic_events(
                instrument_id=instrument_id,
                event_type=event_type,
            ),
        ]

    def cancel_order(
        self,
        external_order_id: str,
        idempotency_key: str,
        reason: str | None,
    ) -> CancelOrderResponse:
        route = get_order_route(external_order_id=external_order_id)
        if route is None:
            raise GatewayConfigurationError("Live order route not found")
        return self._adapter_by_name(route.adapter).cancel_order(
            external_order_id,
            idempotency_key,
            reason,
        )

    def capabilities(self) -> GatewayCapabilitiesResponse:
        return GatewayCapabilitiesResponse(
            gateway=self.name,
            environment=self.settings.environment,
            liveWriteEnabled=self.settings.live_write_enabled,
            adapters=[self.bybit.capability(), self.mt5.capability()],
        )

    def _adapter_for_account(self, account_id: str):
        in_bybit = account_id in self.settings.bybit_accounts
        in_mt5 = account_id in self.settings.mt5_accounts
        if in_bybit and in_mt5:
            raise GatewayConfigurationError("Account is ambiguously mapped to multiple adapters")
        if in_bybit:
            return self.bybit
        if in_mt5:
            return self.mt5
        raise GatewayConfigurationError("Account is not mapped to a live adapter")

    def _adapter_by_name(self, name: str):
        if name == self.bybit.name:
            return self.bybit
        if name == self.mt5.name:
            return self.mt5
        raise GatewayConfigurationError(f"Unknown live adapter route: {name}")
