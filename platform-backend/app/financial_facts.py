from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app import financial_fact_normalization as normalization
from app import financial_fact_repository as repository
from app import financial_projection_service as projection
from app.config import get_settings
from app.financial_fact_schemas import (
    CreateFinancialFactRequest,
    FinancialFactResponse,
    FinancialFactType,
    FinancialProjectionRebuildResponse,
    FormalNavSnapshotResponse,
    FormalPnlResponse,
    FormalPositionResponse,
)

__all__ = [
    "CreateFinancialFactRequest",
    "FinancialFactResponse",
    "FinancialFactType",
    "FinancialProjectionRebuildResponse",
    "FormalNavSnapshotResponse",
    "FormalPnlResponse",
    "FormalPositionResponse",
]

PROJECTED_FACT_TYPES = {"trade_fill", "deal", "funding", "swap", "fee", "fx"}

# Compatibility aliases for callers that previously imported helpers from this module.
ensure_schema = repository.ensure_schema
financial_fact_from_row = repository.financial_fact_from_row
formal_pnl_from_row = repository.formal_pnl_from_row
formal_position_from_row = repository.formal_position_from_row
formal_nav_from_row = repository.formal_nav_from_row
utc_iso = normalization.utc_iso
decimal_text = normalization.decimal_text
optional_decimal = projection.optional_decimal
conversion_rate = projection.conversion_rate
calculate_position_update = projection.calculate_position_update


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_strategy(strategy_instance_id: str):
    row = repository.load_strategy_row(strategy_instance_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy instance not found")
    if row["status"] != "active" or row["v1_scope"] != "closed_loop":
        raise HTTPException(status_code=422, detail="Strategy instance is not active closed-loop")
    return row


def validate_account_binding(strategy_instance_id: str, account_id: str) -> None:
    if not repository.has_active_account_binding(strategy_instance_id, account_id):
        raise HTTPException(status_code=403, detail="Account is not actively bound to strategy")


def load_instrument(instrument_id: str):
    row = repository.load_instrument_row(instrument_id)
    if row is None:
        raise HTTPException(
            status_code=422,
            detail="Instrument or contract specification is unavailable",
        )
    return row


def normalize_fact(
    request: CreateFinancialFactRequest,
) -> normalization.NormalizedFinancialFact:
    strategy = load_strategy(request.strategy_instance_id)
    instrument = None
    if request.account_id is not None:
        validate_account_binding(request.strategy_instance_id, request.account_id)
    if request.instrument_id is not None:
        instrument = load_instrument(request.instrument_id)

    context = normalization.FinancialFactNormalizationContext(
        base_currency=strategy["base_currency"],
        settle_currency=instrument["settle_currency"] if instrument is not None else None,
        quantity_unit=instrument["quantity_unit"] if instrument is not None else None,
        contract_multiplier=(
            Decimal(instrument["contract_multiplier"]) if instrument is not None else None
        ),
    )
    return normalization.normalize_financial_fact(request, context)


def record_financial_fact(request: CreateFinancialFactRequest) -> FinancialFactResponse:
    repository.ensure_schema()
    normalized = normalize_fact(request)
    content_hash = normalization.normalized_content_hash(normalized)
    fact_id = str(uuid4())
    created_at = now_iso()
    status, response = repository.store_financial_fact(
        fact_id=fact_id,
        audit_event_id=str(uuid4()),
        idempotency_key=request.idempotency_key,
        content_hash=content_hash,
        source=request.source,
        external_id=request.external_id,
        fact_type=request.fact_type,
        strategy_instance_id=request.strategy_instance_id,
        normalized=normalized,
        audit_details_json=json.dumps(
            {
                "factType": request.fact_type,
                "strategyInstanceId": request.strategy_instance_id,
                "source": request.source,
                "externalId": request.external_id,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        created_at=created_at,
    )
    if status == "conflict":
        raise HTTPException(
            status_code=409,
            detail="Financial fact identity was reused with a different payload",
        )
    if status == "existing":
        return response

    if request.fact_type in PROJECTED_FACT_TYPES:
        rebuild_account_instrument_projection(
            request.strategy_instance_id,
            request.account_id or "",
            request.instrument_id or "",
        )
    return response


def list_financial_facts(
    strategy_instance_id: str | None = None,
    fact_type: str | None = None,
    limit: int = 200,
) -> list[FinancialFactResponse]:
    repository.ensure_schema()
    return repository.list_financial_facts(strategy_instance_id, fact_type, limit)


def rebuild_account_instrument_projection(
    strategy_instance_id: str,
    account_id: str,
    instrument_id: str,
) -> None:
    projection.rebuild_account_instrument_projection(
        strategy_instance_id,
        account_id,
        instrument_id,
    )


def rebuild_strategy_financials(
    strategy_instance_id: str,
) -> FinancialProjectionRebuildResponse:
    load_strategy(strategy_instance_id)
    return projection.rebuild_strategy_financials(strategy_instance_id)


def list_formal_pnl(strategy_instance_id: str) -> list[FormalPnlResponse]:
    repository.ensure_schema()
    load_strategy(strategy_instance_id)
    return repository.list_formal_pnl(strategy_instance_id)


def list_formal_positions(strategy_instance_id: str) -> list[FormalPositionResponse]:
    repository.ensure_schema()
    load_strategy(strategy_instance_id)
    return repository.list_formal_positions(strategy_instance_id)


def run_formal_nav_snapshot(
    strategy_instance_id: str,
    valuation_time: datetime | None = None,
) -> FormalNavSnapshotResponse:
    strategy = load_strategy(strategy_instance_id)
    try:
        return projection.run_formal_nav_snapshot(
            strategy_instance_id,
            capital_base=optional_decimal(strategy["capital_base"]),
            base_currency=strategy["base_currency"],
            valuation_time=valuation_time,
        )
    except (
        projection.InvalidCapitalBaseError,
        projection.NoActiveAccountBindingsError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def list_formal_nav_snapshots(strategy_instance_id: str) -> list[FormalNavSnapshotResponse]:
    repository.ensure_schema()
    load_strategy(strategy_instance_id)
    return repository.list_formal_nav_snapshots(strategy_instance_id)


router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/financial-facts",
    response_model=FinancialFactResponse,
    tags=["financial-facts"],
    summary="Record one immutable external financial fact",
)
def create_financial_fact(request: CreateFinancialFactRequest) -> FinancialFactResponse:
    return record_financial_fact(request)


@router.get(
    "/financial-facts",
    response_model=list[FinancialFactResponse],
    tags=["financial-facts"],
)
def get_financial_facts(
    strategy_instance_id: str | None = Query(default=None, alias="strategyInstanceId"),
    fact_type: str | None = Query(default=None, alias="factType"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[FinancialFactResponse]:
    return list_financial_facts(strategy_instance_id, fact_type, limit)


@router.post(
    "/strategies/instances/{strategy_instance_id}/financials/rebuild",
    response_model=FinancialProjectionRebuildResponse,
    tags=["financial-facts"],
)
def rebuild_financials(
    strategy_instance_id: str,
) -> FinancialProjectionRebuildResponse:
    return rebuild_strategy_financials(strategy_instance_id)


@router.get(
    "/strategies/instances/{strategy_instance_id}/formal-pnl",
    response_model=list[FormalPnlResponse],
    tags=["pnl"],
)
def get_formal_pnl(strategy_instance_id: str) -> list[FormalPnlResponse]:
    return list_formal_pnl(strategy_instance_id)


@router.get(
    "/strategies/instances/{strategy_instance_id}/formal-positions",
    response_model=list[FormalPositionResponse],
    tags=["pnl"],
)
def get_formal_positions(strategy_instance_id: str) -> list[FormalPositionResponse]:
    return list_formal_positions(strategy_instance_id)


@router.get(
    "/strategies/instances/{strategy_instance_id}/formal-nav-snapshots",
    response_model=list[FormalNavSnapshotResponse],
    tags=["pnl"],
)
def get_formal_nav_snapshots(
    strategy_instance_id: str,
) -> list[FormalNavSnapshotResponse]:
    return list_formal_nav_snapshots(strategy_instance_id)


@router.post(
    "/strategies/instances/{strategy_instance_id}/formal-nav-snapshots/run",
    response_model=FormalNavSnapshotResponse,
    tags=["pnl"],
)
def run_formal_nav(
    strategy_instance_id: str,
    valuation_time: datetime | None = Query(default=None, alias="valuationTime"),
) -> FormalNavSnapshotResponse:
    return run_formal_nav_snapshot(strategy_instance_id, valuation_time)
