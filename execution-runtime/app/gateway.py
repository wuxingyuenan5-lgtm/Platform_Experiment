from datetime import datetime
from typing import Literal, Protocol

from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayCapabilitiesResponse,
    InternalCapitalTransferStepCommand,
    InternalCapitalTransferStepResponse,
    SubmitOrderCommand,
    VenueAccountRiskSnapshot,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillHistoryPage,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueOrderHistoryPage,
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
        """Return one bounded page of Fill or Deal history."""
        ...

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        """Return current external position snapshots."""
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
