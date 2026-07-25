from __future__ import annotations

from decimal import Decimal

from app.gateway_errors import GatewayRequestRejectedError
from app.models import SubmitOrderCommand
from app.mt5_live_adapter import Mt5LiveAdapter


class Mt5PositionClosingAdapter(Mt5LiveAdapter):
    """MT5 adapter that turns reduce-only intent into a ticket-bound close deal."""

    def _build_order_request(
        self,
        mt5,
        command: SubmitOrderCommand,
        reference_price: Decimal,
        comment: str,
    ) -> dict[str, object]:
        request = super()._build_order_request(mt5, command, reference_price, comment)
        if not command.reduce_only:
            return request
        if command.order_type != "market":
            raise GatewayRequestRejectedError("MT5 close execution currently supports market only")
        if command.position_id is None:
            raise GatewayRequestRejectedError("MT5 reduce-only close requires a Position Ticket")
        try:
            ticket = int(command.position_id)
        except ValueError as exc:
            raise GatewayRequestRejectedError("MT5 Position Ticket is invalid") from exc

        rows = mt5.positions_get(ticket=ticket) or ()
        if len(rows) != 1:
            raise GatewayRequestRejectedError(
                "MT5 reduce-only close requires exactly one matching live Position Ticket"
            )
        position = rows[0]
        if str(getattr(position, "symbol", "")).upper() != command.symbol.upper():
            raise GatewayRequestRejectedError("MT5 Position Ticket symbol does not match the order")

        position_type = int(getattr(position, "type", -1))
        sell_type = int(getattr(mt5, "POSITION_TYPE_SELL", 1))
        expected_close_side = "buy" if position_type == sell_type else "sell"
        if command.side != expected_close_side:
            raise GatewayRequestRejectedError(
                "MT5 reduce-only order side would not close the target position"
            )

        live_volume = Decimal(str(getattr(position, "volume", 0) or 0))
        if live_volume <= 0 or command.quantity > live_volume:
            raise GatewayRequestRejectedError(
                "MT5 reduce-only quantity exceeds the target live position"
            )
        request["position"] = ticket
        return request
