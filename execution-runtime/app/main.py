from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.gateway_factory import create_gateway
from app.journal import (
    command_exists,
    get_events,
    initialize_journal,
    journal_status,
    save_command_events,
    save_command_started,
)
from app.models import (
    CrossSpreadSnapshotResponse,
    ExecutionEvent,
    GatewayConnectivityResponse,
    RuntimeStatusResponse,
    SubmitOrderCommand,
    VenueReadinessResponse,
)
from app.cross_spread_market import build_cross_spread_snapshot
from app.secret_resolver import inspect_credential_reference
from app.venue_readiness import get_venue_readiness

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_journal()
    yield


app = FastAPI(title=settings.app_name, version="0.3.0", lifespan=lifespan)
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


@app.post("/commands/orders", response_model=list[ExecutionEvent], tags=["commands"])
def submit_order(command: SubmitOrderCommand) -> list[ExecutionEvent]:
    if command_exists(command.command_id):
        events = get_events(command.command_id)
        if not events:
            raise HTTPException(
                status_code=409,
                detail="Command is already processing and has no persisted events yet",
            )
        return events

    save_command_started(command)
    events = gateway.submit_order(command)
    save_command_events(command, events)
    return events


@app.get(
    "/commands/{command_id}/events",
    response_model=list[ExecutionEvent],
    tags=["commands"],
)
def command_events(command_id: str) -> list[ExecutionEvent]:
    events = get_events(command_id)
    if not events:
        raise HTTPException(status_code=404, detail="Command events not found")
    return events
