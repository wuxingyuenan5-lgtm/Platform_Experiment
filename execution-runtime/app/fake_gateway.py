from datetime import UTC, datetime
from decimal import Decimal

from app.config import get_settings
from app.journal import connection
from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayAdapterCapability,
    GatewayCapabilitiesResponse,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.venue_store import (
    cancel_order,
    ensure_store,
    get_order,
    list_balances,
    list_fills,
    list_positions,
    order_from_row,
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

    def list_orders(
        self,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[VenueOrderSnapshot]:
        ensure_store()
        clauses: list[str] = []
        parameters: list[object] = []
        if account_id is not None:
            clauses.append("account_id = ?")
            parameters.append(account_id)
        if symbol is not None:
            clauses.append("UPPER(symbol) = ?")
            parameters.append(symbol.upper())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        bounded_limit = max(1, min(limit, 100))
        with connection() as db:
            rows = db.execute(
                f"""
                SELECT * FROM fake_venue_orders
                {where}
                ORDER BY updated_at DESC, external_order_id DESC
                LIMIT ?
                """,
                (*parameters, bounded_limit),
            ).fetchall()
        return [order_from_row(row) for row in rows]

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

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
    ) -> VenueInstrumentSpecification:
        normalized = symbol.upper()
        contract_size = Decimal("100") if normalized.startswith("XAUUSD") else Decimal("1")
        minimum = Decimal("0.01") if contract_size == Decimal("100") else Decimal("0.001")
        return VenueInstrumentSpecification(
            source=self.name,
            accountId=account_id,
            instrumentId=f"fake:{normalized}",
            symbol=normalized,
            status="available",
            minQuantity=minimum,
            quantityStep=minimum,
            maxMarketQuantity=Decimal("100"),
            contractSize=contract_size,
            trade_mode="simulation",
            filling_mode="deterministic",
            accessChecks={"simulation": True},
            asOf=datetime.now(UTC),
        )

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
                        "order_list",
                        "fill_query",
                        "position_query",
                        "balance_query",
                        "instrument_specification_query",
                    ],
                    missingRequirements=[],
                    checkedAt=datetime.now(UTC),
                )
            ],
        )
