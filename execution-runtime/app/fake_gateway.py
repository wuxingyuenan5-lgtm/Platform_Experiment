from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from app.config import get_settings
from app.journal import connection
from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayAdapterCapability,
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
    VenueOrderHistoryPage,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.venue_store import (
    cancel_order,
    claim_order_script,
    ensure_store,
    get_internal_capital_transfer,
    get_market_quote,
    get_order,
    list_balances,
    list_fills,
    list_positions,
    order_from_row,
    persist_filled_order,
    persist_order,
    transfer_internal_capital,
)


class FakeGateway:
    """Deterministic persistent gateway used before connecting real venues."""

    name = "fake"

    def place_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        return self.submit_order(command)

    def get_account(self, account_id: str) -> VenueAccountSnapshot:
        return self.get_account_snapshot(account_id)

    def get_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        return self.list_positions(account_id)

    def get_open_orders(
        self,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[VenueOrderSnapshot]:
        return [
            order
            for order in self.list_orders(account_id=account_id, symbol=symbol, limit=limit)
            if order.status in {"accepted", "partially_filled"}
        ][:limit]

    def get_order_history(self, **kwargs) -> VenueOrderHistoryPage:
        return self.query_order_history(**kwargs)

    def get_fill_history(self, **kwargs) -> VenueFillHistoryPage:
        return self.query_fill_history(**kwargs)

    def health(self) -> GatewayCapabilitiesResponse:
        return self.capabilities()

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        ensure_store()
        script = None
        if command.order_type == "limit":
            with connection() as db:
                script = claim_order_script(db, command.symbol.upper())
        if script is not None and script["behavior"] == "result_unknown":
            from app.gateway_errors import GatewayResultUnknownError

            raise GatewayResultUnknownError("Fake scripted result is unknown")
        if script is not None and script["behavior"] == "accepted_no_fill":
            external_order_id, _ = persist_order(
                command,
                status="accepted",
                fill_price=None,
                fill_quantity=Decimal("0"),
                cancel_terminal_after_queries=int(script["cancel_terminal_after_queries"]),
            )
            return [
                ExecutionEvent(
                    event_id=f"FAKE-ACK-{command.platform_order_id}",
                    command_id=command.command_id,
                    platform_order_id=command.platform_order_id,
                    event_type="order_acknowledged",
                    external_order_id=external_order_id,
                    occurred_at=command.received_at,
                )
            ]
        if script is not None and script["behavior"] == "partial_fill":
            fill_price = Decimal(
                str(script["partial_fill_price"] or command.price or Decimal("100"))
            )
            scripted_quantity = Decimal(str(script["partial_fill_quantity"]))
            fill_quantity = min(scripted_quantity, command.quantity)
            if fill_quantity < Decimal("0"):
                fill_quantity = Decimal("0")
            external_order_id, _ = persist_order(
                command,
                status="partially_filled" if fill_quantity > 0 else "accepted",
                fill_price=fill_price,
                fill_quantity=fill_quantity,
                cancel_terminal_after_queries=int(script["cancel_terminal_after_queries"]),
            )
            return [
                ExecutionEvent(
                    event_id=f"FAKE-ACK-{command.platform_order_id}",
                    command_id=command.command_id,
                    platform_order_id=command.platform_order_id,
                    event_type="order_acknowledged",
                    external_order_id=external_order_id,
                    occurred_at=command.received_at,
                )
            ]
        fill_price = command.price or self._estimate_market_fill_price(command)
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

    def _estimate_market_fill_price(self, command: SubmitOrderCommand) -> Decimal:
        from app.cross_spread_market import estimate_cached_fill_price

        estimated = estimate_cached_fill_price(symbol=command.symbol, side=command.side)
        return estimated or Decimal("100")

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
        items = [
            item
            for item in self.list_orders(account_id=account_id, symbol=symbol, limit=100)
            if start_time <= item.as_of <= end_time
        ]
        offset = _cursor_offset(cursor)
        page_size = max(1, min(limit, 100))
        page_items = items[offset : offset + page_size]
        next_offset = offset + len(page_items)
        return VenueOrderHistoryPage(
            source=self.name,
            accountId=account_id,
            items=page_items,
            nextCursor=str(next_offset) if next_offset < len(items) else None,
            startTime=start_time,
            endTime=end_time,
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
        items = [
            item
            for item in self.list_fills(account_id=account_id)
            if start_time <= item.occurred_at <= end_time
            and (symbol is None or item.symbol == symbol.upper())
        ]
        items.sort(key=lambda item: item.occurred_at, reverse=True)
        offset = _cursor_offset(cursor)
        page_size = max(1, min(limit, 100))
        page_items = items[offset : offset + page_size]
        next_offset = offset + len(page_items)
        return VenueFillHistoryPage(
            source=self.name,
            accountId=account_id,
            items=page_items,
            nextCursor=str(next_offset) if next_offset < len(items) else None,
            startTime=start_time,
            endTime=end_time,
        )

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        return list_positions(account_id)

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        return list_balances(account_id)

    def get_account_risk(self, account_id: str) -> VenueAccountRiskSnapshot:
        balances = self.list_balances(account_id)
        balance = balances[0] if balances else None
        return VenueAccountRiskSnapshot(
            source=self.name,
            accountId=account_id,
            currency=balance.currency if balance else "USD",
            equity=balance.equity if balance else Decimal("0"),
            walletBalance=balance.equity if balance else Decimal("0"),
            marginBalance=balance.equity if balance else Decimal("0"),
            availableBalance=(balance.available_balance if balance else Decimal("0")),
            initialMargin=Decimal("0"),
            maintenanceMargin=Decimal("0"),
            unrealizedPnl=Decimal("0"),
            marginLevel=None,
            marginCallLevel=None,
            stopOutLevel=None,
            marginMode="simulation",
            tradeAllowed=False,
            expertTradingAllowed=False,
            fieldAvailability={"simulation": "deterministic"},
            asOf=datetime.now(UTC),
        )

    def transfer_internal_capital(
        self,
        command: InternalCapitalTransferStepCommand,
    ) -> InternalCapitalTransferStepResponse:
        return transfer_internal_capital(command)

    def get_internal_capital_transfer_readiness(
        self,
        *,
        source_account_id: str,
        destination_account_id: str,
        currency: str,
    ) -> InternalCapitalTransferReadinessResponse:
        risk = self.get_account_risk(source_account_id)
        return InternalCapitalTransferReadinessResponse(
            ready=True,
            sourceAccountId=source_account_id,
            destinationAccountId=destination_account_id,
            currency=currency.upper(),
            transferableBalance=risk.available_balance,
            fromAccountType="simulation",
            toAccountType="simulation",
        )

    def query_internal_capital_transfer(
        self,
        command: InternalCapitalTransferStepCommand,
        *,
        external_transfer_id: str,
    ) -> InternalCapitalTransferStepResponse:
        return get_internal_capital_transfer(
            command,
            external_transfer_id=external_transfer_id,
        )

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None = None,
        category: str | None = None,
    ) -> VenueInstrumentSpecification:
        normalized = symbol.upper()
        contract_size = Decimal("100") if normalized.startswith("XAUUSD") else Decimal("1")
        minimum = Decimal("0.01") if contract_size == Decimal("100") else Decimal("0.001")
        return VenueInstrumentSpecification(
            source=self.name,
            accountId=account_id,
            instrumentId=f"fake:{normalized}",
            instrumentType=instrument_type or "simulation",
            category=category or "simulation",
            symbol=normalized,
            status="available",
            priceTick=minimum,
            minQuantity=minimum,
            quantityStep=minimum,
            maxMarketQuantity=Decimal("100"),
            contractMultiplier=contract_size,
            contractSize=contract_size,
            trade_mode="simulation",
            filling_mode="deterministic",
            accessChecks={"simulation": True},
            asOf=datetime.now(UTC),
        )

    def get_account_snapshot(self, account_id: str) -> VenueAccountSnapshot:
        balances = self.list_balances(account_id)
        positions = self.list_positions(account_id)
        orders = self.list_orders(account_id=account_id, limit=100)
        fills = self.list_fills(account_id=account_id)
        risk = self.get_account_risk(account_id)
        as_of = max(
            [risk.as_of, *(balance.as_of for balance in balances)] or [datetime.now(UTC)]
        )
        return VenueAccountSnapshot(
            source=self.name,
            accountId=account_id,
            venue="fake",
            identity={"accountId": account_id},
            balances=balances,
            positions=positions,
            orders=orders,
            fills=fills,
            accountRisk=risk,
            asOf=as_of,
            dataQualityState="complete",
        )

    def get_market_quote(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None = None,
        category: str | None = None,
    ):
        return get_market_quote(
            account_id=account_id,
            symbol=symbol,
            instrument_type=instrument_type or "simulation",
            category=category or "simulation",
        )

    def list_economic_events(
        self,
        *,
        account_id: str | None = None,
        instrument_id: str | None = None,
        event_type: str | None = None,
    ) -> list[VenueEconomicEventSnapshot]:
        from app.venue_store import list_economic_events as _list_events

        return _list_events(
            account_id=account_id,
            instrument_id=instrument_id,
            event_type=event_type,
        )

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
                        "post_only_single_attempt_submit",
                        "cancel_order",
                        "cancel_order_gated",
                        "order_query",
                        "order_list",
                        "paged_order_history",
                        "fill_query",
                        "paged_fill_history",
                        "position_query",
                        "balance_query",
                        "account_risk_query",
                        "internal_capital_transfer",
                        "instrument_specification_query",
                        "market_quote_query",
                    ],
                    missingRequirements=[],
                    checkedAt=datetime.now(UTC),
                )
            ],
        )


def _cursor_offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    return max(0, int(cursor))
