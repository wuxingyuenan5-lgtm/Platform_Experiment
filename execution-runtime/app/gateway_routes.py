from __future__ import annotations

from fastapi import APIRouter

from app.config import Settings
from app.cross_spread_market import build_cross_spread_snapshot
from app.gateway import VenueGateway
from app.models import (
    CrossSpreadSnapshotResponse,
    GatewayCapabilitiesResponse,
    GatewayConnectivityResponse,
    VenueReadinessResponse,
)
from app.secret_resolver import inspect_credential_reference
from app.venue_readiness import get_venue_readiness


def _preferred_mt5_symbol(settings: Settings) -> str | None:
    """Return the explicitly mapped MT5 symbol, if any, else None (auto-resolve)."""
    mapped = settings.mt5_instruments
    if mapped:
        return next(iter(mapped))
    return None


def _credential_required_fields(
    settings: Settings, credential_ref: str
) -> tuple[str, ...]:
    mt5_credential_refs = {
        settings.mt5_credential_ref,
        *settings.mt5_account_credentials.values(),
    }
    if credential_ref in mt5_credential_refs:
        return ("LOGIN", "PASSWORD", "SERVER")
    return ("API_KEY", "SECRET")


def create_gateway_router(*, settings: Settings, gateway: VenueGateway) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/gateway/capabilities",
        response_model=GatewayCapabilitiesResponse,
        tags=["gateway"],
    )
    def gateway_capabilities() -> GatewayCapabilitiesResponse:
        return gateway.capabilities()

    @router.get(
        "/gateway/connectivity",
        response_model=GatewayConnectivityResponse,
        tags=["gateway"],
    )
    def gateway_connectivity() -> GatewayConnectivityResponse:
        credentials = [
            inspect_credential_reference(
                credential_ref,
                required_fields=_credential_required_fields(settings, credential_ref),
            )
            for credential_ref in settings.configured_credential_refs
        ]
        return GatewayConnectivityResponse(
            gateway=gateway.name,
            credentialCount=len(credentials),
            configuredCredentialCount=sum(1 for item in credentials if item.configured),
            credentials=credentials,
        )

    @router.get(
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
            bybit_credential_ref=settings.bybit_credential_ref,
            mt5_credential_ref=settings.mt5_credential_ref,
        )

    @router.get(
        "/gateway/cross-spread/snapshot",
        response_model=CrossSpreadSnapshotResponse,
        tags=["gateway"],
    )
    def cross_spread_snapshot() -> CrossSpreadSnapshotResponse:
        return build_cross_spread_snapshot(
            bybit_symbol=settings.bybit_contract_symbol,
            mt5_symbol=settings.mt5_symbol,
            bybit_credential_ref=settings.bybit_credential_ref,
            mt5_credential_ref=settings.mt5_credential_ref,
            bybit_demo=settings.bybit_demo_mode,
            bybit_recv_window=settings.bybit_recv_window,
            mt5_terminal_path=settings.mt5_terminal_path,
            mt5_bridge_file_path=settings.mt5_bridge_file_path,
            mt5_timeout_seconds=settings.mt5_check_timeout_seconds,
            mt5_preferred_symbol=_preferred_mt5_symbol(settings),
            bybit_timestamp_offset_ms=settings.bybit_timestamp_offset_ms,
        )

    return router
