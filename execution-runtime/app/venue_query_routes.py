from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.gateway import ExecutionGateway
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.models import (
    CancelOrderRequest,
    CancelOrderResponse,
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
from app.route_errors import history_window, query_gateway


def create_venue_query_router(*, gateway: ExecutionGateway) -> APIRouter:
    router = APIRouter()

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
            lambda: gateway.query_order_history(
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
            lambda: gateway.query_fill_history(
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
        return query_gateway(lambda: gateway.list_positions(account_id))

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
        "/venue/instruments/{symbol}",
        response_model=VenueInstrumentSpecification,
        tags=["venue-query"],
    )
    def venue_instrument_specification(
        symbol: str,
        account_id: str = Query(alias="accountId"),
    ) -> VenueInstrumentSpecification:
        return query_gateway(
            lambda: gateway.get_instrument_specification(account_id=account_id, symbol=symbol)
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
