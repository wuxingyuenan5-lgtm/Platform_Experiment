from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.execution_risk_models import (
    FailureAction,
    OrderSide,
    RiskDisposition,
    RiskStatus,
)


@dataclass(frozen=True)
class RiskEvaluation:
    status: RiskStatus
    exceeded: bool
    reason: str | None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def evaluate_leg_deadline(
    first_fill_at: datetime | None,
    current: datetime,
    max_leg_delay_seconds: int,
) -> RiskEvaluation:
    if first_fill_at is None:
        return RiskEvaluation(status="clear", exceeded=False, reason=None)
    elapsed = (_as_utc(current) - _as_utc(first_fill_at)).total_seconds()
    if elapsed <= max_leg_delay_seconds:
        return RiskEvaluation(status="clear", exceeded=False, reason=None)
    return RiskEvaluation(
        status="residual_exposure",
        exceeded=True,
        reason=f"Leg delay {elapsed:.3f}s exceeded policy limit {max_leg_delay_seconds}s",
    )


def evaluate_residual_exposure(
    residual: Decimal,
    currency: str,
    data_quality_state: str,
    max_residual_notional: Decimal,
) -> RiskEvaluation:
    if data_quality_state != "complete":
        return RiskEvaluation(
            status="residual_exposure",
            exceeded=True,
            reason=(
                "Residual exposure cannot be compared reliably because "
                "currency data is mixed"
            ),
        )
    if residual > max_residual_notional:
        return RiskEvaluation(
            status="residual_exposure",
            exceeded=True,
            reason=(
                f"Residual exposure {residual} {currency} exceeded policy limit "
                f"{max_residual_notional}"
            ),
        )
    return RiskEvaluation(
        status="residual_exposure" if residual > 0 else "clear",
        exceeded=False,
        reason=None,
    )


def evaluate_batch_completion(
    residual: Decimal,
    data_quality_state: str,
) -> RiskEvaluation:
    if residual == 0 and data_quality_state == "complete":
        return RiskEvaluation(status="clear", exceeded=False, reason=None)
    return RiskEvaluation(
        status="residual_exposure",
        exceeded=True,
        reason="Batch completed with unresolved residual exposure",
    )


def select_failure_disposition(
    residual: Decimal,
    data_quality_state: str,
    failure_action: FailureAction,
) -> RiskDisposition:
    if residual == 0 and data_quality_state == "complete":
        return "resolved"
    if failure_action == "auto_flatten":
        return "auto_flatten"
    return "escalated"


def opposite_side(side: OrderSide) -> OrderSide:
    return "sell" if side == "buy" else "buy"
