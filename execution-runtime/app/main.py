from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from app.config import get_settings
from app.cross_spread_market import build_cross_spread_snapshot
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayQueryUnsupportedError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.gateway_factory import create_gateway
from app.journal import (
    claim_command,
    get_events,
    initialize_journal,
    journal_status,
    save_command_events,
)
from app.live_route_store import ensure_live_store
from app.models import (
    CancelOrderRequest,
    CancelOrderResponse,
    CrossSpreadSnapshotResponse,
    ExecutionEvent,
    GatewayCapabilitiesResponse,
    GatewayConnectivityResponse,
    RuntimeStatusResponse,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
    VenueReadinessResponse,
)
from app.runtime_contracts import (
    RuntimeExecutionEventV1,
    RuntimeSubmitOrderCommandV1,
    version_execution_events,
)
from app.secret_resolver import inspect_credential_reference
from app.venue_readiness import get_venue_readiness
from app.venue_store import ensure_store

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_journal()
    ensure_store()
    ensure_live_store()
    yield


app = FastAPI(title=settings.app_name, version="0.5.0", lifespan=lifespan)
gateway = create_gateway(settings.gateway_name)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "execution-runtime",
        "gateway": gateway.name,
    }


@app.get("/status", response_model=RuntimeStatusResponse, tags=["system"])
def status() -> RuntimeStatusResponse:
    return RuntimeStatusResponse(
        status="available",
        service="execution-runtime",
        environment=settings.environment,
        gateway=gateway.name,
        journal=journal_status(),
    )


@app.get(
    "/gateway/capabilities",
    response_model=GatewayCapabilitiesResponse,
    tags=["gateway"],
)
def gateway_capabilities() -> GatewayCapabilitiesResponse:
    return gateway.capabilities()


@app.get(
    "/gateway/connectivity",
    response_model=GatewayConnectivityResponse,
    tags=["gateway"],
)
def gateway_connectivity() -> GatewayConnectivityResponse:
    credentials = [
        inspect_credential_reference(credential_ref)
        for credential_ref in settings.configured_credential_refs
    ]
    return GatewayConnectivityResponse(
        gateway=gateway.name,
        credentialCount=len(credentials),
        configuredCredentialCount=sum(1 for item in credentials if item.configured),
        credentials=credentials,
    )


@app.get(
    "/gateway/venue-readiness",
    response_model=VenueReadinessResponse,
    tags=["gateway"],
)
def venue_readiness() -> VenueReadinessResponse:
    return get_venue_readiness(
        bybit_symbol=settings.bybit_contract_symbol,
        bybit_demo=settings.bybit_demo_mode,
        bybit_recv_window=settings.bybit_recv_window,
        bybit_timeout_seconds=settings.bybit_check_timeout_seconds,
        mt5_symbol=settings.mt5_symbol,
        mt5_terminal_path=settings.mt5_terminal_path,
        mt5_timeout_seconds=settings.mt5_check_timeout_seconds,
    )


@app.get(
    "/gateway/cross-spread/snapshot",
    response_model=CrossSpreadSnapshotResponse,
    tags=["gateway"],
)
def cross_spread_snapshot() -> CrossSpreadSnapshotResponse:
    return build_cross_spread_snapshot(
        bybit_symbol=settings.bybit_contract_symbol,
        mt5_symbol=settings.mt5_symbol,
        bybit_demo=settings.bybit_demo_mode,
        bybit_recv_window=settings.bybit_recv_window,
        mt5_terminal_path=settings.mt5_terminal_path,
        mt5_bridge_file_path=settings.mt5_bridge_file_path,
    )


@app.post(
    "/commands/orders",
    response_model=list[RuntimeExecutionEventV1],
    tags=["commands"],
)
def submit_order(command: RuntimeSubmitOrderCommandV1) -> list[RuntimeExecutionEventV1]:
    if not claim_command(command):
        events = get_events(command.command_id)
        if not events:
            raise HTTPException(
                status_code=409,
                detail="Command is already processing and has no persisted events yet",
            )
        return version_execution_events(events)

    try:
        events = gateway.submit_order(command)
    except (GatewayConfigurationError, GatewayRequestRejectedError) as exc:
        events = [
            ExecutionEvent(
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_rejected",
                reason=str(exc),
            )
        ]
    except GatewayResultUnknownError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    save_command_events(command, events)
    return version_execution_events(events)


@app.get(
    "/commands/{command_id}/events",
    response_model=list[RuntimeExecutionEventV1],
    tags=["commands"],
)
def command_events(command_id: str) -> list[RuntimeExecutionEventV1]:
    events = get_events(command_id)
    if not events:
        raise HTTPException(status_code=404, detail="Command events not found")
    return version_execution_events(events)


@app.get(
    "/venue/orders",
    response_model=list[VenueOrderSnapshot],
    tags=["venue-query"],
)
def venue_orders(
    account_id: str | None = Query(default=None, alias="accountId"),
    symbol: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[VenueOrderSnapshot]:
    return _query(
        lambda: gateway.list_orders(
            account_id=account_id,
            symbol=symbol,
            limit=limit,
        )
    )


@app.get(
    "/venue/orders/by-platform/{platform_order_id}",
    response_model=VenueOrderSnapshot,
    tags=["venue-query"],
)
def venue_order_by_platform(platform_order_id: str) -> VenueOrderSnapshot:
    snapshot = _query(lambda: gateway.get_order(platform_order_id=platform_order_id))
    if snapshot is None:
        raise HTTPException(status_code=404, detail="External order not found")
    return snapshot


@app.get(
    "/venue/orders/{external_order_id}",
    response_model=VenueOrderSnapshot,
    tags=["venue-query"],
)
def venue_order(external_order_id: str) -> VenueOrderSnapshot:
    snapshot = _query(lambda: gateway.get_order(external_order_id=external_order_id))
    if snapshot is None:
        raise HTTPException(status_code=404, detail="External order not found")
    return snapshot


@app.get(
    "/venue/fills",
    response_model=list[VenueFillSnapshot],
    tags=["venue-query"],
)
def venue_fills(
    account_id: str | None = Query(default=None, alias="accountId"),
    external_order_id: str | None = Query(default=None, alias="externalOrderId"),
    platform_order_id: str | None = Query(default=None, alias="platformOrderId"),
) -> list[VenueFillSnapshot]:
    return _query(
        lambda: gateway.list_fills(
            account_id=account_id,
            external_order_id=external_order_id,
            platform_order_id=platform_order_id,
        )
    )


@app.get(
    "/venue/positions",
    response_model=list[VenuePositionSnapshot],
    tags=["venue-query"],
)
def venue_positions(
    account_id: str | None = Query(default=None, alias="accountId"),
) -> list[VenuePositionSnapshot]:
    return _query(lambda: gateway.list_positions(account_id))


@app.get(
    "/venue/balances",
    response_model=list[VenueBalanceSnapshot],
    tags=["venue-query"],
)
def venue_balances(
    account_id: str | None = Query(default=None, alias="accountId"),
) -> list[VenueBalanceSnapshot]:
    return _query(lambda: gateway.list_balances(account_id))


@app.get(
    "/venue/instruments/{symbol}",
    response_model=VenueInstrumentSpecification,
    tags=["venue-query"],
)
def venue_instrument_specification(
    symbol: str,
    account_id: str = Query(alias="accountId"),
) -> VenueInstrumentSpecification:
    return _query(
        lambda: gateway.get_instrument_specification(
            account_id=account_id,
            symbol=symbol,
        )
    )


@app.get(
    "/venue/economic-events",
    response_model=list[VenueEconomicEventSnapshot],
    tags=["venue-query"],
)
def venue_economic_events(
    account_id: str | None = Query(default=None, alias="accountId"),
    instrument_id: str | None = Query(default=None, alias="instrumentId"),
    event_type: str | None = Query(default=None, alias="eventType"),
) -> list[VenueEconomicEventSnapshot]:
    return _query(
        lambda: gateway.list_economic_events(
            account_id=account_id,
            instrument_id=instrument_id,
            event_type=event_type,
        )
    )


@app.post(
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


def _query(callback):
    try:
        return callback()
    except GatewayConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GatewayQueryUnsupportedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except GatewayRequestRejectedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GatewayResultUnknownError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
