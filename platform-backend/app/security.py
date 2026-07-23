from __future__ import annotations

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.database import connection
from app.schemas import (
    CredentialReferenceResponse,
    ExchangeConnectivityResponse,
    ExchangeVenueReadinessResponse,
    TradingSafetyResponse,
)

LIVE_ENVIRONMENT = "live"


def get_trading_safety() -> TradingSafetyResponse:
    settings = get_settings()
    return TradingSafetyResponse(
        liveTradingEnabled=settings.live_trading_enabled,
        defaultTradingEnvironment=settings.default_trading_environment,
        secretStoragePolicy="database_stores_references_only",
        liveGuardPolicy="live_accounts_require_global_switch_and_active_account",
    )


def list_credential_references() -> list[CredentialReferenceResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT cr.id, cr.credential_ref, cr.venue_id, v.venue_code,
                   cr.environment, cr.purpose, cr.status, cr.created_at
            FROM credential_references cr
            JOIN venues v ON v.id = cr.venue_id
            ORDER BY cr.environment, v.venue_code, cr.credential_ref
            """
        ).fetchall()
    return [
        CredentialReferenceResponse(
            credentialId=row["id"],
            credentialRef=row["credential_ref"],
            venueId=row["venue_id"],
            venueCode=row["venue_code"],
            environment=row["environment"],
            purpose=row["purpose"],
            status=row["status"],
            createdAt=row["created_at"],
        )
        for row in rows
    ]


def get_exchange_connectivity() -> ExchangeConnectivityResponse:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.runtime_base_url}/gateway/connectivity",
            timeout=settings.runtime_timeout_seconds,
        )
        if response.status_code >= 400:
            return ExchangeConnectivityResponse(status="not_connected")
    except httpx.HTTPError:
        return ExchangeConnectivityResponse(status="not_connected")

    payload = response.json()
    return ExchangeConnectivityResponse(status="available", **payload)


def get_exchange_venue_readiness() -> ExchangeVenueReadinessResponse:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.runtime_base_url}/gateway/venue-readiness",
            timeout=max(settings.runtime_timeout_seconds, 20.0),
        )
        if response.status_code >= 400:
            return ExchangeVenueReadinessResponse(status="not_connected")
    except httpx.HTTPError:
        return ExchangeVenueReadinessResponse(status="not_connected")

    payload = response.json()
    return ExchangeVenueReadinessResponse(**payload)


def enforce_order_safety(account_id: str) -> None:
    account = get_account_security_row(account_id)
    if account is None:
        return

    if account["credential_ref"] is not None and not str(account["credential_ref"]).startswith(
        "secret://"
    ):
        raise HTTPException(status_code=403, detail="Account credential reference is unsafe")

    if account["environment"] != LIVE_ENVIRONMENT:
        return

    settings = get_settings()
    if not settings.live_trading_enabled:
        raise HTTPException(
            status_code=403,
            detail="Live trading is disabled by global safety switch",
        )
    if account["status"] != "active":
        raise HTTPException(status_code=403, detail="Live account is not active")


def get_account_security_row(account_id: str):
    with connection() as db:
        return db.execute(
            """
            SELECT id, environment, status, credential_ref
            FROM accounts
            WHERE id = ?
            """,
            (account_id,),
        ).fetchone()
