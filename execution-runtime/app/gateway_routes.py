from __future__ import annotations

from fastapi import APIRouter, Query

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
    def cross_spread_snapshot(
        bybit_account_id: str = Query(alias="bybitAccountId"),
        mt5_account_id: str = Query(alias="mt5AccountId"),
    ) -> CrossSpreadSnapshotResponse:
        return build_cross_spread_snapshot(
            gateway=gateway,
            bybit_account_id=bybit_account_id,
            mt5_account_id=mt5_account_id,
            bybit_symbol=settings.bybit_contract_symbol,
            mt5_symbol=settings.mt5_symbol,
        )

    return router
