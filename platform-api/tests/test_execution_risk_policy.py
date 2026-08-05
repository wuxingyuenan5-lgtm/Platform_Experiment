from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.execution_risk_policy import (
    evaluate_batch_completion,
    evaluate_leg_deadline,
    evaluate_residual_exposure,
    opposite_side,
    select_failure_disposition,
)

pytestmark = pytest.mark.unit


def test_leg_deadline_is_inclusive_and_deterministic() -> None:
    first_fill = datetime(2026, 8, 4, 1, 2, 3, tzinfo=UTC)
    at_limit = first_fill + timedelta(seconds=10)
    after_limit = first_fill + timedelta(seconds=10, milliseconds=1)

    allowed = evaluate_leg_deadline(first_fill, at_limit, 10)
    repeated = evaluate_leg_deadline(first_fill, at_limit, 10)
    exceeded = evaluate_leg_deadline(first_fill, after_limit, 10)

    assert allowed == repeated
    assert allowed.exceeded is False
    assert exceeded.exceeded is True
    assert exceeded.status == "residual_exposure"
    assert exceeded.reason == "Leg delay 10.001s exceeded policy limit 10s"


def test_residual_policy_distinguishes_threshold_and_data_quality() -> None:
    within_limit = evaluate_residual_exposure(
        Decimal("50"), "USDT", "complete", Decimal("100")
    )
    over_limit = evaluate_residual_exposure(
        Decimal("100.01"), "USDT", "complete", Decimal("100")
    )
    mixed = evaluate_residual_exposure(
        Decimal("0"), "MIXED", "mixed_currency", Decimal("100")
    )

    assert within_limit.status == "residual_exposure"
    assert within_limit.exceeded is False
    assert over_limit.exceeded is True
    assert "100.01 USDT" in (over_limit.reason or "")
    assert mixed.exceeded is True
    assert mixed.reason == (
        "Residual exposure cannot be compared reliably because currency data is mixed"
    )


def test_completion_failure_disposition_and_side_are_pure() -> None:
    assert evaluate_batch_completion(Decimal("0"), "complete").status == "clear"
    assert (
        evaluate_batch_completion(Decimal("0.01"), "complete").status
        == "residual_exposure"
    )
    assert select_failure_disposition(
        Decimal("0"), "complete", "auto_flatten"
    ) == "resolved"
    assert select_failure_disposition(
        Decimal("1"), "complete", "auto_flatten"
    ) == "auto_flatten"
    assert select_failure_disposition(
        Decimal("1"), "complete", "hold_and_escalate"
    ) == "escalated"
    assert opposite_side("buy") == "sell"
    assert opposite_side("sell") == "buy"
