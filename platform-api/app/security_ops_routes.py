from fastapi import APIRouter, Query

from app.ops import get_reconciliation_summary, list_audit_events
from app.schemas import (
    AuditEventResponse,
    CredentialReferenceResponse,
    ExchangeConnectivityResponse,
    ExchangeVenueReadinessResponse,
    ReconciliationSummaryResponse,
    TradingSafetyResponse,
)
from app.security import (
    get_exchange_connectivity,
    get_exchange_venue_readiness,
    get_trading_safety,
    list_credential_references,
)


def create_security_ops_router(api_prefix: str) -> APIRouter:
    router = APIRouter()

    @router.get(
        f"{api_prefix}/security/trading-safety",
        response_model=TradingSafetyResponse,
        tags=["security"],
    )
    def trading_safety() -> TradingSafetyResponse:
        return get_trading_safety()

    @router.get(
        f"{api_prefix}/security/credential-references",
        response_model=list[CredentialReferenceResponse],
        tags=["security"],
    )
    def credential_references() -> list[CredentialReferenceResponse]:
        return list_credential_references()

    @router.get(
        f"{api_prefix}/security/exchange-connectivity",
        response_model=ExchangeConnectivityResponse,
        tags=["security"],
    )
    def exchange_connectivity() -> ExchangeConnectivityResponse:
        return get_exchange_connectivity()

    @router.get(
        f"{api_prefix}/security/exchange-venue-readiness",
        response_model=ExchangeVenueReadinessResponse,
        tags=["security"],
    )
    def exchange_venue_readiness() -> ExchangeVenueReadinessResponse:
        return get_exchange_venue_readiness()

    @router.get(
        f"{api_prefix}/ops/reconciliation-summary",
        response_model=ReconciliationSummaryResponse,
        tags=["ops"],
    )
    def reconciliation_summary() -> ReconciliationSummaryResponse:
        return get_reconciliation_summary()

    @router.get(
        f"{api_prefix}/ops/audit-events",
        response_model=list[AuditEventResponse],
        tags=["ops"],
    )
    def audit_events(
        subject_type: str | None = Query(default=None, alias="subjectType"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> list[AuditEventResponse]:
        return list_audit_events(subject_type=subject_type, limit=limit)

    return router
