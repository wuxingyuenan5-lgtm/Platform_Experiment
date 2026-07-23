from __future__ import annotations

from decimal import Decimal

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
ACTIVE_STATUS = "active"


def get_trading_safety() -> TradingSafetyResponse:
    settings = get_settings()
    return TradingSafetyResponse(
        liveTradingEnabled=settings.live_trading_enabled,
        defaultTradingEnvironment=settings.default_trading_environment,
        secretStoragePolicy="database_stores_references_only",
        liveGuardPolicy="all_accounts_fail_closed_and_live_requires_global_switch",
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


def enforce_order_safety(
    account_id: str,
    instrument_id: str,
    quantity: Decimal,
    price: Decimal | None,
) -> None:
    account = get_account_security_row(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if account["status"] != ACTIVE_STATUS:
        raise HTTPException(status_code=403, detail="Account is not active")

    credential_ref = account["credential_ref"]
    if credential_ref is not None and not str(credential_ref).startswith("secret://"):
        raise HTTPException(status_code=403, detail="Account credential reference is unsafe")

    instrument = get_instrument_security_row(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    if instrument["contract_version"] is None:
        raise HTTPException(status_code=422, detail="Instrument has no active contract specification")

    min_order_quantity = Decimal(instrument["min_order_quantity"])
    quantity_step = Decimal(instrument["quantity_step"])
    price_tick = Decimal(instrument["price_tick"])

    if quantity < min_order_quantity:
        raise HTTPException(status_code=422, detail="Order quantity is below minimum")
    if quantity_step <= 0 or quantity % quantity_step != 0:
        raise HTTPException(status_code=422, detail="Order quantity is not aligned to quantity step")
    if price is not None and (price_tick <= 0 or price % price_tick != 0):
        raise HTTPException(status_code=422, detail="Order price is not aligned to price tick")

    if account["environment"] != LIVE_ENVIRONMENT:
        return

    settings = get_settings()
    if not settings.live_trading_enabled:
        raise HTTPException(
            status_code=403,
            detail="Live trading is disabled by global safety switch",
        )


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


def get_instrument_security_row(instrument_id: str):
    with connection() as db:
        return db.execute(
            """
            SELECT i.id,
                   cs.version AS contract_version,
                   cs.price_tick,
                   cs.min_order_quantity,
                   cs.quantity_step
            FROM instruments i
            LEFT JOIN contract_specifications cs ON cs.instrument_id = i.id
            WHERE i.id = ?
            ORDER BY cs.effective_from DESC
            LIMIT 1
            """,
            (instrument_id,),
        ).fetchone()
