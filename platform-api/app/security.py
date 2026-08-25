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
LOCAL_TEST_STATUSES = {"simulation", "testnet", "demo"}


def get_trading_safety() -> TradingSafetyResponse:
    settings = get_settings()
    return TradingSafetyResponse(
        liveTradingEnabled=settings.live_trading_enabled,
        defaultTradingEnvironment=settings.default_trading_environment,
        founderDemoLocalSelfApprovalEnabled=(
            settings.founder_demo_live_acceptance_enabled
            and settings.environment.lower() == "development"
            and settings.auth_mode.lower() == "development"
        ),
        secretStoragePolicy="database_stores_references_only",
        liveGuardPolicy=(
            "all_accounts_fail_closed_live_requires_global_switch_authentication_"
            "and_two_person_session"
        ),
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
    *,
    strategy_instance_id: str | None = None,
    symbol: str | None = None,
    side: str | None = None,
    order_type: str | None = None,
    command_id: str | None = None,
) -> None:
    account = get_account_security_row(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if not _account_is_order_eligible(account["status"], account["environment"]):
        raise HTTPException(status_code=403, detail="Account is not active")

    credential_ref = account["credential_ref"]
    if credential_ref is not None and not str(credential_ref).startswith("secret://"):
        raise HTTPException(status_code=403, detail="Account credential reference is unsafe")

    instrument = get_instrument_security_row(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    if instrument["contract_version"] is None:
        raise HTTPException(
            status_code=422,
            detail="Instrument has no active contract specification",
        )

    min_order_quantity = Decimal(instrument["min_order_quantity"])
    quantity_step = Decimal(instrument["quantity_step"])
    price_tick = Decimal(instrument["price_tick"])

    if quantity < min_order_quantity:
        raise HTTPException(status_code=422, detail="Order quantity is below minimum")
    if quantity_step <= 0 or quantity % quantity_step != 0:
        raise HTTPException(
            status_code=422,
            detail="Order quantity is not aligned to quantity step",
        )
    if price is not None and (price_tick <= 0 or price % price_tick != 0):
        raise HTTPException(
            status_code=422,
            detail="Order price is not aligned to price tick",
        )

    if account["environment"] != LIVE_ENVIRONMENT:
        return

    settings = get_settings()
    if not settings.live_trading_enabled:
        raise HTTPException(
            status_code=403,
            detail="Live trading is disabled by global safety switch",
        )
    founder_demo_acceptance = (
        settings.founder_demo_live_acceptance_enabled
        and settings.environment.lower() == "development"
        and settings.auth_mode.lower() == "development"
    )
    if settings.auth_mode.lower() != "api_key" and not founder_demo_acceptance:
        raise HTTPException(
            status_code=503,
            detail="Live trading requires production authentication",
        )
    if not settings.require_live_trading_session:
        raise HTTPException(
            status_code=503,
            detail="LiveTradingSession enforcement cannot be disabled in live trading",
        )
    if None in {strategy_instance_id, symbol, side, order_type, command_id}:
        raise HTTPException(
            status_code=403,
            detail="Live order lacks an approved-session identity boundary",
        )

    from app.live_session_claims import validate_and_claim_live_session_atomic

    validate_and_claim_live_session_atomic(
        command_id=str(command_id),
        strategy_instance_id=str(strategy_instance_id),
        account_id=account_id,
        symbol=str(symbol),
        side=str(side),
        order_type=str(order_type),
        quantity=quantity,
        price=price,
    )


def _account_is_order_eligible(status: str, environment: str) -> bool:
    if status == ACTIVE_STATUS:
        return True
    return status == "paused" and environment in LOCAL_TEST_STATUSES


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
