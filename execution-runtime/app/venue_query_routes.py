from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.gateway import VenueGateway
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.models import (
    CancelOrderRequest,
    CancelOrderResponse,
    InternalCapitalTransferReadinessResponse,
    InternalCapitalTransferStepCommand,
    InternalCapitalTransferStepResponse,
    VenueAccountRiskSnapshot,
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillHistoryPage,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueMarketQuoteSnapshot,
    VenueOrderHistoryPage,
    VenueOrderMarginEstimate,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.route_errors import history_window, query_gateway


class BybitLeverageRequest(BaseModel):
    account_id: str = Field(alias="accountId")
    symbol: str
    leverage: Decimal = Field(ge=1, le=100, allow_inf_nan=False)


def create_venue_query_router(*, gateway: VenueGateway) -> APIRouter:
    router = APIRouter()

    @router.get("/venue/capital-flows", tags=["venue-query"])
    def capital_flows(
        account_id: str = Query(alias="accountId"),
        start_time: datetime = Query(alias="startTime"),
        end_time: datetime = Query(alias="endTime"),
    ) -> dict:
        start, end = history_window(start_time, end_time)
        reader = getattr(gateway, "get_capital_flows", None)
        if reader is None:
            raise HTTPException(status_code=501, detail="Capital history unavailable")
        return query_gateway(lambda: reader(account_id=account_id, start_time=start, end_time=end))

    @router.get("/venue/bybit/leverage", tags=["venue-query"])
    def get_bybit_leverage(
        account_id: str = Query(alias="accountId"), symbol: str = "XAUTUSDT"
    ) -> dict[str, object]:
        adapter = getattr(gateway, "bybit", None)
        if adapter is None or not hasattr(adapter, "get_leverage"):
            raise HTTPException(status_code=501, detail="Bybit leverage query is unavailable")
        return query_gateway(lambda: adapter.get_leverage(account_id=account_id, symbol=symbol))

    @router.post("/venue/bybit/leverage", tags=["venue-write"])
    def set_bybit_leverage(request: BybitLeverageRequest) -> dict[str, object]:
        setter = getattr(gateway, "set_bybit_leverage", None)
        if setter is None:
            raise HTTPException(status_code=501, detail="Bybit leverage update is unavailable")
        return query_gateway(
            lambda: setter(
                account_id=request.account_id,
                symbol=request.symbol,
                leverage=request.leverage,
            )
        )

    @router.get("/venue/orders", response_model=list[VenueOrderSnapshot], tags=["venue-query"])
    def venue_orders(
        account_id: str | None = Query(default=None, alias="accountId"),
        symbol: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
    ) -> list[VenueOrderSnapshot]:
        return query_gateway(
            lambda: gateway.list_orders(account_id=account_id, symbol=symbol, limit=limit)
        )

    @router.get(
        "/venue/order-history",
        response_model=VenueOrderHistoryPage,
        tags=["venue-query"],
    )
    def venue_order_history(
        account_id: str = Query(alias="accountId"),
        symbol: str | None = None,
        start_time: Annotated[
            datetime | None,
            Query(alias="startTime"),
        ] = None,
        end_time: Annotated[
            datetime | None,
            Query(alias="endTime"),
        ] = None,
        cursor: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        scope: Literal["active", "closed"] = "closed",
    ) -> VenueOrderHistoryPage:
        bounded_start, bounded_end = history_window(start_time, end_time)
        return query_gateway(
            lambda: gateway.get_order_history(
                account_id=account_id,
                symbol=symbol,
                start_time=bounded_start,
                end_time=bounded_end,
                cursor=cursor,
                limit=limit,
                scope=scope,
            )
        )

    @router.get(
        "/venue/orders/by-platform/{platform_order_id}",
        response_model=VenueOrderSnapshot,
        tags=["venue-query"],
    )
    def venue_order_by_platform(platform_order_id: str) -> VenueOrderSnapshot:
        snapshot = query_gateway(lambda: gateway.get_order(platform_order_id=platform_order_id))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="External order not found")
        return snapshot

    @router.get(
        "/venue/orders/{external_order_id}",
        response_model=VenueOrderSnapshot,
        tags=["venue-query"],
    )
    def venue_order(external_order_id: str) -> VenueOrderSnapshot:
        snapshot = query_gateway(lambda: gateway.get_order(external_order_id=external_order_id))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="External order not found")
        return snapshot

    @router.get("/venue/fills", response_model=list[VenueFillSnapshot], tags=["venue-query"])
    def venue_fills(
        account_id: str | None = Query(default=None, alias="accountId"),
        external_order_id: str | None = Query(default=None, alias="externalOrderId"),
        platform_order_id: str | None = Query(default=None, alias="platformOrderId"),
    ) -> list[VenueFillSnapshot]:
        return query_gateway(
            lambda: gateway.list_fills(
                account_id=account_id,
                external_order_id=external_order_id,
                platform_order_id=platform_order_id,
            )
        )

    @router.get(
        "/venue/fill-history",
        response_model=VenueFillHistoryPage,
        tags=["venue-query"],
    )
    def venue_fill_history(
        account_id: str = Query(alias="accountId"),
        symbol: str | None = None,
        start_time: Annotated[
            datetime | None,
            Query(alias="startTime"),
        ] = None,
        end_time: Annotated[
            datetime | None,
            Query(alias="endTime"),
        ] = None,
        cursor: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
    ) -> VenueFillHistoryPage:
        bounded_start, bounded_end = history_window(start_time, end_time)
        return query_gateway(
            lambda: gateway.get_fill_history(
                account_id=account_id,
                symbol=symbol,
                start_time=bounded_start,
                end_time=bounded_end,
                cursor=cursor,
                limit=limit,
            )
        )

    @router.get(
        "/venue/positions",
        response_model=list[VenuePositionSnapshot],
        tags=["venue-query"],
    )
    def venue_positions(
        account_id: str | None = Query(default=None, alias="accountId"),
    ) -> list[VenuePositionSnapshot]:
        return query_gateway(lambda: gateway.get_positions(account_id))

    @router.get("/venue/balances", response_model=list[VenueBalanceSnapshot], tags=["venue-query"])
    def venue_balances(
        account_id: str | None = Query(default=None, alias="accountId"),
    ) -> list[VenueBalanceSnapshot]:
        return query_gateway(lambda: gateway.list_balances(account_id))

    @router.get(
        "/venue/account-risk",
        response_model=VenueAccountRiskSnapshot,
        tags=["venue-query"],
    )
    def venue_account_risk(
        account_id: str = Query(alias="accountId"),
    ) -> VenueAccountRiskSnapshot:
        return query_gateway(lambda: gateway.get_account_risk(account_id))

    @router.get(
        "/venue/account-snapshot",
        response_model=VenueAccountSnapshot,
        tags=["venue-query"],
    )
    def venue_account_snapshot(
        account_id: str = Query(alias="accountId"),
    ) -> VenueAccountSnapshot:
        return query_gateway(lambda: gateway.get_account(account_id))

    @router.post(
        "/venue/internal-capital-transfers",
        response_model=InternalCapitalTransferStepResponse,
        tags=["venue-write"],
    )
    def venue_internal_capital_transfer(
        request: InternalCapitalTransferStepCommand,
    ) -> InternalCapitalTransferStepResponse:
        return query_gateway(lambda: gateway.transfer_internal_capital(request))

    @router.get(
        "/venue/internal-capital-transfers/readiness",
        response_model=InternalCapitalTransferReadinessResponse,
        tags=["venue-query"],
    )
    def venue_internal_capital_transfer_readiness(
        source_account_id: str = Query(alias="sourceAccountId"),
        destination_account_id: str = Query(alias="destinationAccountId"),
        currency: str = Query(default="USDT"),
    ) -> InternalCapitalTransferReadinessResponse:
        return query_gateway(
            lambda: gateway.get_internal_capital_transfer_readiness(
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                currency=currency,
            )
        )

    @router.get(
        "/venue/internal-capital-transfers/{external_transfer_id}",
        response_model=InternalCapitalTransferStepResponse,
        tags=["venue-query"],
    )
    def venue_internal_capital_transfer_status(
        external_transfer_id: str,
        amount: Annotated[Decimal, Query(gt=0)],
        idempotency_key: str = Query(alias="idempotencyKey"),
        source_account_id: str = Query(alias="sourceAccountId"),
        destination_account_id: str = Query(alias="destinationAccountId"),
        source_currency: str = Query(alias="sourceCurrency"),
        destination_currency: str = Query(alias="destinationCurrency"),
    ) -> InternalCapitalTransferStepResponse:
        command = InternalCapitalTransferStepCommand(
            idempotencyKey=idempotency_key,
            sourceAccountId=source_account_id,
            destinationAccountId=destination_account_id,
            sourceCurrency=source_currency,
            destinationCurrency=destination_currency,
            amount=amount,
        )
        return query_gateway(
            lambda: gateway.query_internal_capital_transfer(
                command,
                external_transfer_id=external_transfer_id,
            )
        )

    @router.get(
        "/venue/instruments/{symbol}",
        response_model=VenueInstrumentSpecification,
        tags=["venue-query"],
    )
    def venue_instrument_specification(
        symbol: str,
        account_id: str = Query(alias="accountId"),
        instrument_type: str | None = Query(default=None, alias="instrumentType"),
        category: str | None = Query(default=None),
    ) -> VenueInstrumentSpecification:
        return query_gateway(
            lambda: gateway.get_instrument_specification(
                account_id=account_id,
                symbol=symbol,
                instrument_type=instrument_type,
                category=category,
            )
        )

    @router.get(
        "/venue/quotes/{symbol}",
        response_model=VenueMarketQuoteSnapshot,
        tags=["venue-query"],
    )
    def venue_market_quote(
        symbol: str,
        account_id: str = Query(alias="accountId"),
        instrument_type: str | None = Query(default=None, alias="instrumentType"),
        category: str | None = Query(default=None),
    ) -> VenueMarketQuoteSnapshot:
        return query_gateway(
            lambda: gateway.get_market_quote(
                account_id=account_id,
                symbol=symbol,
                instrument_type=instrument_type,
                category=category,
            )
        )

    @router.get(
        "/venue/order-margin-estimate/{symbol}",
        response_model=VenueOrderMarginEstimate,
        tags=["venue-query"],
    )
    def venue_order_margin_estimate(
        symbol: str,
        account_id: Annotated[str, Query(alias="accountId")],
        side: Annotated[Literal["buy", "sell"], Query()],
        quantity: Annotated[Decimal, Query(gt=0)],
        reference_price: Annotated[Decimal, Query(alias="referencePrice", gt=0)],
    ) -> VenueOrderMarginEstimate:
        return query_gateway(
            lambda: gateway.estimate_order_margin(
                account_id=account_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                reference_price=reference_price,
            )
        )

    @router.get(
        "/venue/economic-events",
        response_model=list[VenueEconomicEventSnapshot],
        tags=["venue-query"],
    )
    def venue_economic_events(
        account_id: str | None = Query(default=None, alias="accountId"),
        instrument_id: str | None = Query(default=None, alias="instrumentId"),
        event_type: str | None = Query(default=None, alias="eventType"),
    ) -> list[VenueEconomicEventSnapshot]:
        return query_gateway(
            lambda: gateway.list_economic_events(
                account_id=account_id,
                instrument_id=instrument_id,
                event_type=event_type,
            )
        )

    @router.post(
        "/venue/orders/{external_order_id}/cancel",
        response_model=CancelOrderResponse,
        tags=["venue-query"],
    )
    def cancel_venue_order(
        external_order_id: str,
        request: CancelOrderRequest,
    ) -> CancelOrderResponse:
        try:
            return gateway.cancel_order(
                external_order_id,
                request.idempotency_key,
                request.reason,
            )
        except GatewayConfigurationError as exc:
            raise HTTPException(status_code=423, detail=str(exc)) from exc
        except GatewayRequestRejectedError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except GatewayResultUnknownError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router
