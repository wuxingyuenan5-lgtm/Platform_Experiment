from __future__ import annotations

import json
from decimal import Decimal

import httpx
from fastapi import HTTPException

from app import runtime_transport
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
        founderDemoLocalSelfApprovalEnabled=False,
        secretStoragePolicy="database_stores_references_only",
        liveGuardPolicy="authenticated_trading_account_binding_and_risk_checks",
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
        response = runtime_transport.get(
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
        response = runtime_transport.get(
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

    specification = dict(instrument)
    if account["environment"] == LIVE_ENVIRONMENT and instrument["instrument_type"] in {
        "crypto_spot",
        "crypto_perp",
    }:
        if not get_settings().live_trading_enabled:
            raise HTTPException(403, "Live trading is disabled by global safety switch")
        category = "spot" if instrument["instrument_type"] == "crypto_spot" else "linear"
        try:
            response = runtime_transport.get(
                f"{get_settings().runtime_base_url}/venue/instruments/{symbol}",
                params={
                    "accountId": account_id,
                    "instrumentType": instrument["instrument_type"],
                    "category": category,
                },
            )
            response.raise_for_status()
            native = response.json()
            if (
                any(
                    native.get(field) != value
                    for field, value in (
                        ("accountId", account_id),
                        ("symbol", symbol),
                        ("instrumentType", instrument["instrument_type"]),
                        ("category", category),
                        ("dataQualityState", "complete"),
                    )
                )
                or str(native.get("status", "")).lower() != "trading"
            ):
                raise ValueError("Native specification identity or state is invalid")
            for target, field in (
                ("min_order_quantity", "minQuantity"),
                ("quantity_step", "quantityStep"),
                ("price_tick", "priceTick"),
            ):
                value = Decimal(str(native[field]))
                if not value.is_finite() or value <= 0:
                    raise ValueError("Native specification quantity or price is invalid")
                specification[target] = value
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise HTTPException(409, "Native order specification is unavailable") from exc

    min_order_quantity = Decimal(specification["min_order_quantity"])
    quantity_step = Decimal(specification["quantity_step"])
    price_tick = Decimal(specification["price_tick"])

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
    if None in {strategy_instance_id, symbol, side, order_type, command_id}:
        raise HTTPException(
            status_code=403,
            detail="Live order lacks a strategy and command identity boundary",
        )

    assert_live_account_execution_allowed(account_id, str(strategy_instance_id))


def assert_live_account_execution_allowed(account_id: str, strategy_instance_id: str) -> None:
    """Shared batch preflight and last-moment per-order live account checks."""
    account = get_account_security_row(account_id)
    if account is None:
        raise HTTPException(404, "Account not found")
    if account["environment"] != LIVE_ENVIRONMENT:
        return
    if not get_settings().live_trading_enabled:
        raise HTTPException(403, "Live trading is disabled by global safety switch")
    from app.execution_risk import assert_execution_allowed
    from app.venue_reconciliation_repository import effective_venue_event
    from app.venue_reconciliation_repository import ensure_schema as ensure_reconciliation_schema

    assert_execution_allowed(str(strategy_instance_id), [account_id])
    ensure_reconciliation_schema()
    with connection() as db:
        binding = db.execute(
            """
            SELECT 1 FROM strategy_account_bindings
            WHERE strategy_instance_id = ? AND account_id = ?
              AND status = 'active' AND capability = 'trade_and_read'
            """,
            (strategy_instance_id, account_id),
        ).fetchone()
        if binding is None:
            raise HTTPException(
                status_code=403, detail="Account has no active strategy trading binding"
            )
        differences = db.execute(
            """
            SELECT rd.* FROM reconciliation_differences rd
            JOIN venue_reconciliation_runs vr ON vr.id = rd.run_id
            WHERE vr.strategy_instance_id = ? AND vr.account_id = ?
              AND rd.status IN ('open', 'accepted')
              AND NOT (
                  rd.status = 'accepted' AND rd.difference_type = 'missing_external'
                  AND EXISTS (
                      SELECT 1 FROM orders o
                      WHERE o.id = rd.local_reference AND o.status = 'rejected'
                  )
              )
            """,
            (strategy_instance_id, account_id),
        ).fetchall()
        for difference in differences:
            if (
                difference["status"] == "accepted"
                and difference["difference_type"] == "timestamp_mismatch"
                and difference["entity_type"] == "venue_event"
            ):
                # Use the same exact-receipt, time-only evidence as ingestion.
                # Acceptance alone never waives an amount or identity conflict.
                try:
                    original = json.loads(difference["local_value_json"])
                    corrected = json.loads(difference["external_value_json"])
                    event_type = str(difference["external_reference"]).split(":", 1)[0]
                    if (
                        original.get("accountId") == account_id
                        and original != corrected
                        and effective_venue_event(db, account_id, event_type, original) == corrected
                    ):
                        continue
                except (ValueError, TypeError, AttributeError):
                    pass  # Invalid accepted evidence remains a blocking difference.
            raise HTTPException(
                status_code=423,
                detail="Outstanding open or accepted reconciliation differences exist",
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
            SELECT i.id, i.instrument_type,
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
