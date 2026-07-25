from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.bybit_acceptance_adapter import BybitAcceptanceAdapter
from app.bybit_fill_confirming_adapter import BybitFillConfirmingAdapter
from app.gateway_errors import GatewayRequestRejectedError
from app.live_observability import (
    bybit_positions,
    mt5_account_risk,
    mt5_fill_history,
    mt5_order_history,
    mt5_positions,
)
from app.models import (
    SubmitOrderCommand,
    VenueAccountRiskSnapshot,
    VenueFillHistoryPage,
    VenueOrderHistoryPage,
    VenuePositionSnapshot,
)
from app.mt5_acceptance_adapter import Mt5AcceptanceAdapter
from app.mt5_position_closing_adapter import Mt5PositionClosingAdapter


class StrictBybitAcceptanceAdapter(BybitAcceptanceAdapter):
    """Enforce current Bybit sizing and access evidence before every live write."""

    def submit_order(self, command: SubmitOrderCommand):
        specification = self.get_instrument_specification(
            account_id=command.account_id,
            symbol=command.symbol,
        )
        maximum_ounces = self.settings.live_acceptance_max_order_quantity
        if maximum_ounces <= 0 or command.quantity > maximum_ounces:
            raise GatewayRequestRejectedError(
                "Live acceptance Bybit quantity exceeds the temporary one-ounce limit"
            )
        _validate_step(
            command.quantity,
            minimum=specification.min_quantity,
            step=specification.quantity_step,
            maximum=specification.max_market_quantity,
            label="Bybit",
        )
        checks = specification.access_checks
        if specification.status.lower() not in {"trading", "available"}:
            raise GatewayRequestRejectedError("Bybit instrument is not trading")
        if checks.get("readOnly") is True:
            raise GatewayRequestRejectedError("Bybit API key is read-only")
        if checks.get("ipBound") is not True:
            raise GatewayRequestRejectedError(
                "Bybit API key is not bound to a fixed IP"
            )
        if checks.get("orderPermission") is not True:
            raise GatewayRequestRejectedError("Bybit API key lacks Order permission")
        if checks.get("positionPermission") is not True:
            raise GatewayRequestRejectedError("Bybit API key lacks Position permission")
        if not command.reduce_only:
            self._assert_no_existing_position(command.symbol)
        return BybitFillConfirmingAdapter.submit_order(self, command)

    def list_positions(
        self, account_id: str | None = None
    ) -> list[VenuePositionSnapshot]:
        return bybit_positions(self, account_id)


class StrictMt5AcceptanceAdapter(Mt5AcceptanceAdapter):
    """Convert MT5 lots to ounces before applying the temporary live cap."""

    def submit_order(self, command: SubmitOrderCommand):
        specification = self.get_instrument_specification(
            account_id=command.account_id,
            symbol=command.symbol,
        )
        maximum_ounces = self.settings.live_acceptance_max_order_quantity
        requested_ounces = command.quantity * specification.contract_size
        if maximum_ounces <= 0 or requested_ounces > maximum_ounces:
            raise GatewayRequestRejectedError(
                "Live acceptance MT5 quantity exceeds the temporary one-ounce limit"
            )
        _validate_step(
            command.quantity,
            minimum=specification.min_quantity,
            step=specification.quantity_step,
            maximum=specification.max_market_quantity,
            label="MT5",
        )
        checks = specification.access_checks
        if checks.get("accountLoginMatched") is not True:
            raise GatewayRequestRejectedError(
                "MT5 connected login does not match configuration"
            )
        if checks.get("accountTradeAllowed") is not True:
            raise GatewayRequestRejectedError("MT5 account does not allow trading")
        if checks.get("terminalTradeAllowed") is not True:
            raise GatewayRequestRejectedError("MT5 Terminal does not allow trading")
        if not command.reduce_only:
            self._assert_no_existing_position(command.symbol)
        return Mt5PositionClosingAdapter.submit_order(self, command)

    def list_positions(
        self, account_id: str | None = None
    ) -> list[VenuePositionSnapshot]:
        return mt5_positions(self, account_id)

    def get_account_risk(self, account_id: str) -> VenueAccountRiskSnapshot:
        return mt5_account_risk(self, account_id)

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
        return mt5_order_history(
            self,
            account_id=account_id,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            cursor=cursor,
            limit=limit,
            scope=scope,
        )

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
        return mt5_fill_history(
            self,
            account_id=account_id,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            cursor=cursor,
            limit=limit,
        )


def _validate_step(
    quantity: Decimal,
    *,
    minimum: Decimal,
    step: Decimal,
    maximum: Decimal | None,
    label: str,
) -> None:
    if minimum <= 0 or step <= 0:
        raise GatewayRequestRejectedError(
            f"{label} quantity specification is invalid"
        )
    if quantity < minimum:
        raise GatewayRequestRejectedError(
            f"{label} quantity is below the venue minimum"
        )
    if maximum is not None and maximum > 0 and quantity > maximum:
        raise GatewayRequestRejectedError(
            f"{label} quantity exceeds the venue maximum"
        )
    steps = (quantity - minimum) / step
    if steps != steps.to_integral_value():
        raise GatewayRequestRejectedError(
            f"{label} quantity does not match the venue step"
        )
