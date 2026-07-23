from datetime import UTC, datetime
from decimal import Decimal

from app.config import get_settings
from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayAdapterCapability,
    GatewayCapabilitiesResponse,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.venue_store import (
    cancel_order,
    get_order,
    list_balances,
    list_fills,
    list_positions,
    persist_filled_order,
)


class FakeGateway:
    """Deterministic persistent gateway used before connecting real venues."""

    name = "fake"

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        fill_price = command.price or Decimal("100")
        external_order_id, _ = persist_filled_order(command, fill_price)
        return [
            ExecutionEvent(
                event_id=f"FAKE-ACK-{command.platform_order_id}",
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_acknowledged",
                external_order_id=external_order_id,
                occurred_at=command.received_at,
            ),
            ExecutionEvent(
                event_id=f"FAKE-FILL-{command.platform_order_id}",
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_filled",
                external_order_id=external_order_id,
                fill_price=fill_price,
                fill_quantity=command.quantity,
                occurred_at=command.received_at,
            ),
        ]

    def get_order(
        self,
        *,
        platform_order_id: str | None = None,
        external_order_id: str | None = None,
    ) -> VenueOrderSnapshot | None:
        return get_order(
            platform_order_id=platform_order_id,
            external_id=external_order_id,
        )

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        return list_fills(
            account_id=account_id,
            external_id=external_order_id,
            platform_order_id=platform_order_id,
        )

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        return list_positions(account_id)

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        return list_balances(account_id)

    def list_economic_events(
        self,
        *,
        account_id: str | None = None,
        instrument_id: str | None = None,
        event_type: str | None = None,
    ) -> list[VenueEconomicEventSnapshot]:
        return []

    def cancel_order(
        self,
        external_order_id: str,
        idempotency_key: str,
        reason: str | None,
    ) -> CancelOrderResponse:
        return cancel_order(external_order_id, idempotency_key, reason)

    def capabilities(self) -> GatewayCapabilitiesResponse:
        settings = get_settings()
        return GatewayCapabilitiesResponse(
            gateway=self.name,
            environment=settings.environment,
            liveWriteEnabled=False,
            adapters=[
                GatewayAdapterCapability(
                    adapter=self.name,
                    environment="simulation",
                    configured=True,
                    operational=True,
                    writeEnabled=True,
                    accountIds=[],
                    capabilities=[
                        "submit_order",
                        "cancel_order",
                        "order_query",
                        "fill_query",
                        "position_query",
                        "balance_query",
                    ],
                    missingRequirements=[],
                    checkedAt=datetime.now(UTC),
                )
            ],
        )
