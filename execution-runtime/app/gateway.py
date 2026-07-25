from typing import Protocol

from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayCapabilitiesResponse,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)


class ExecutionGateway(Protocol):
    name: str

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        """Submit one normalized platform order command to the configured venue."""
        ...

    def get_order(
        self,
        *,
        platform_order_id: str | None = None,
        external_order_id: str | None = None,
    ) -> VenueOrderSnapshot | None:
        """Query one external order without creating a new side effect."""
        ...

    def list_orders(
        self,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[VenueOrderSnapshot]:
        """Return bounded current and recent external orders."""
        ...

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        """Return external fills matching the supplied filters."""
        ...

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        """Return current external position snapshots."""
        ...

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        """Return current external balance snapshots."""
        ...

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
    ) -> VenueInstrumentSpecification:
        """Return current venue sizing and access evidence for one symbol."""
        ...

    def list_economic_events(
        self,
        *,
        account_id: str | None = None,
        instrument_id: str | None = None,
        event_type: str | None = None,
    ) -> list[VenueEconomicEventSnapshot]:
        """Return Funding, Swap, and Fee facts from the external venue."""
        ...

    def cancel_order(
        self,
        external_order_id: str,
        idempotency_key: str,
        reason: str | None,
    ) -> CancelOrderResponse:
        """Cancel an external order idempotently when the venue supports it."""
        ...

    def capabilities(self) -> GatewayCapabilitiesResponse:
        """Return fail-closed adapter readiness without exposing secrets."""
        ...
