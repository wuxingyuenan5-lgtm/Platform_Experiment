from fastapi import APIRouter, Query

from app.config import get_settings
from app.cross_spread_observability_schemas import CrossSpreadObservabilityResponse
from app.cross_spread_observability_service import get_cross_spread_observability

settings = get_settings()

router = APIRouter(prefix=f"{settings.api_prefix}/trading/cross-spread")


@router.get(
    "/observability",
    response_model=CrossSpreadObservabilityResponse,
    tags=["trading"],
)
def cross_spread_observability(
    history_hours: int = Query(default=24, alias="historyHours", ge=1, le=168),
    limit: int = Query(default=20, ge=1, le=100),
) -> CrossSpreadObservabilityResponse:
    return get_cross_spread_observability(
        history_hours=history_hours,
        limit=limit,
    )
