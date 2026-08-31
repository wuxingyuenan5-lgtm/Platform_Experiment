from datetime import datetime
from typing import Literal, Protocol

from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayCapabilitiesResponse,
    InternalCapitalTransferReadinessResponse,
    InternalCapitalTransferStepCommand,
    InternalCapitalTransferStepResponse,
    SubmitOrderCommand,
    VenueAccountRiskSnapshot,
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillHistoryPage,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueMarketQuoteSnapshot,
    VenueOrderHistoryPage,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)


class VenueGateway(Protocol):
    """Single normalized execution boundary used by every strategy and venue.

    Venue adapters may keep SDK-shaped method names internally. Platform-facing
    execution, recovery, and reconciliation use this contract only.
    """

    name: str

    def place_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        """Submit one normalized platform order command to the configured venue."""
        ...

    def get_account(self, account_id: str) -> VenueAccountSnapshot:
        """Return one authoritative account snapshot for one sync cycle."""
        ...

    def get_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        """Return current authoritative positions."""
        ...

    def get_open_orders(
        self,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[VenueOrderSnapshot]:
        """Return only accepted or partially-filled orders."""
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

    def get_order_history(
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
        """Return one bounded page of active or historical orders."""
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

    def get_fill_history(
        self,
        *,
        account_id: str,
        symbol: str | None,
        start_time: datetime,
        end_time: datetime,
        cursor: str | None,
        limit: int,
    ) -> VenueFillHistoryPage:
        """Return one bounded page of Fill or Deal history."""
        ...

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        """Return current external balance snapshots."""
        ...

    def get_account_risk(self, account_id: str) -> VenueAccountRiskSnapshot:
        """Return account-level authoritative margin and stop-out evidence."""
        ...

    def transfer_internal_capital(
        self,
        command: InternalCapitalTransferStepCommand,
    ) -> InternalCapitalTransferStepResponse:
        """Move capital between verified internal accounts idempotently."""
        ...

    def get_internal_capital_transfer_readiness(
        self,
        *,
        source_account_id: str,
        destination_account_id: str,
        currency: str,
    ) -> InternalCapitalTransferReadinessResponse:
        """Return authoritative transfer permission and transferable balance."""
        ...

    def query_internal_capital_transfer(
        self,
        command: InternalCapitalTransferStepCommand,
        *,
        external_transfer_id: str,
    ) -> InternalCapitalTransferStepResponse:
        """Query one existing transfer identity without creating a new transfer."""
        ...

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None = None,
        category: str | None = None,
    ) -> VenueInstrumentSpecification:
        """Return current venue sizing and access evidence for one symbol."""
        ...

    def get_market_quote(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None = None,
        category: str | None = None,
    ) -> VenueMarketQuoteSnapshot:
        """Return one authoritative market quote for the supplied symbol."""
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

    def health(self) -> GatewayCapabilitiesResponse:
        """Return account/adapter readiness without causing an external write."""
        ...


# Compatibility import for code outside Runtime. Runtime routes and recovery use
# VenueGateway; venue-specific adapters remain implementation details.
ExecutionGateway = VenueGateway
