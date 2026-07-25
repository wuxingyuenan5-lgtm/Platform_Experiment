from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

import app.cross_spread_synthetic_service as synthetic_service
from app.config import get_settings
from app.cross_spread_exit_schemas import (
    CrossSpreadExitPlanResponse,
    CrossSpreadMarketOpenRequest,
)
from app.cross_spread_limit_policy import CrossSpreadFokPrice
from app.execution_schemas import ExecutionBatchResponse
from app.schemas import CrossSpreadSnapshotResponse

NOW = datetime(2026, 7, 26, tzinfo=UTC)


def batch_response(batch_id: str, *, status: str) -> ExecutionBatchResponse:
    return ExecutionBatchResponse(
        batchId=batch_id,
        idempotencyKey=f"key:{batch_id}",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        accountId="account_crypto_test",
        strategyKey="cross_venue_spread",
        direction="CLOSE_LONG",
        status=status,
        requiresManualIntervention=status == "manual_intervention",
        failureReason="test outcome" if status != "hedged" else None,
        legs=[],
        createdAt=NOW,
        updatedAt=NOW,
    )


def plan(status: str, *, trigger_reason: str | None = None) -> CrossSpreadExitPlanResponse:
    return CrossSpreadExitPlanResponse(
        planId="plan-fok-1",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        openBatchId="open-batch-1",
        closeBatchId=None,
        direction="LONG_SPREAD",
        quantityOz="1",
        mt5PositionId="778899",
        entrySpread="-2",
        takeProfitSpread="0",
        stopLossSpread="-3",
        status=status,
        triggerReason=trigger_reason,
        triggerSpread=None,
        createdAt=NOW,
        updatedAt=NOW,
        triggeredAt=None,
        closedAt=None,
    )


def pricing() -> CrossSpreadFokPrice:
    return CrossSpreadFokPrice(
        direction="SELL_BYBIT_BUY_MT5",
        limit_spread=Decimal("-1.1"),
        executable_spread=Decimal("-1.0"),
        mt5_reference_price=Decimal("2501.1"),
        hedge_reserve=Decimal("0"),
        bybit_tick_size=Decimal("0.1"),
        raw_bybit_limit_price=Decimal("2500.0"),
        bybit_limit_price=Decimal("2500.0"),
        currently_executable=True,
    )


def available_snapshot() -> CrossSpreadSnapshotResponse:
    return CrossSpreadSnapshotResponse.model_validate(
        {
            "status": "available",
            "bybit": {
                "venue": "bybit",
                "symbol": "XAUTUSDT",
                "status": "available",
                "quote": {
                    "bid": "2500.1",
                    "ask": "2500.2",
                    "mid": "2500.15",
                    "currency": "USDT",
                },
                "positions": [],
            },
            "mt5": {
                "venue": "mt5",
                "symbol": "XAUUSD+",
                "status": "available",
                "quote": {
                    "bid": "2501.0",
                    "ask": "2501.1",
                    "mid": "2501.05",
                    "currency": "USD",
                },
                "positions": [],
            },
            "longSpread": "-0.8",
            "shortSpread": "-1.0",
            "metrics": {},
            "asOf": NOW,
        }
    )


def test_non_executable_limit_rejects_before_any_batch_submission(monkeypatch) -> None:
    monkeypatch.setattr(
        synthetic_service.market_helpers,
        "_assert_acceptance_open_allowed",
        lambda: None,
    )
    monkeypatch.setattr(
        synthetic_service,
        "get_cross_spread_snapshot",
        available_snapshot,
    )
    monkeypatch.setattr(
        synthetic_service,
        "get_bybit_catalog_tick_size",
        lambda: Decimal("0.1"),
    )
    monkeypatch.setattr(
        synthetic_service,
        "submit_cross_spread_fok_command",
        lambda *_args, **_kwargs: pytest.fail(
            "Non-executable FOK must not create a batch"
        ),
    )
    get_settings().cross_spread_limit_hedge_reserve_price = Decimal("0")

    with pytest.raises(HTTPException) as exc_info:
        synthetic_service.open_cross_spread_market(
            CrossSpreadMarketOpenRequest(
                direction="LONG_SPREAD",
                quantityOz="1",
                takeProfitSpread="0",
                stopLossSpread="-3",
                executionMode="limit",
                limitSpread="-1.0",
            )
        )

    assert exc_info.value.status_code == 409
    assert "no order was submitted" in str(exc_info.value.detail)


def test_clean_fok_close_no_fill_releases_plan_back_to_active(monkeypatch) -> None:
    captured = {}
    active = plan("active")
    triggered = plan("triggered", trigger_reason="manual")
    released = plan("active")
    monkeypatch.setattr(synthetic_service, "get_exit_plan", lambda _plan_id: active)
    monkeypatch.setattr(
        synthetic_service,
        "claim_exit_plan",
        lambda *_args, **_kwargs: triggered,
    )
    monkeypatch.setattr(
        synthetic_service,
        "_prepare_limit_execution",
        lambda *_args, **_kwargs: pricing(),
    )

    def fake_submit(request, **kwargs):
        captured["request"] = request
        captured["kwargs"] = kwargs
        return batch_response("fok-close-no-fill", status="failed")

    monkeypatch.setattr(
        synthetic_service,
        "submit_cross_spread_fok_command",
        fake_submit,
    )
    monkeypatch.setattr(
        synthetic_service,
        "load_batch_fill_summaries",
        lambda _batch_id: {},
    )
    monkeypatch.setattr(
        synthetic_service,
        "release_exit_plan_claim",
        lambda _plan_id: released,
    )
    monkeypatch.setattr(
        synthetic_service,
        "mark_plan_closing",
        lambda *_args: pytest.fail("Clean no-fill must not move the plan to closing"),
    )

    result = synthetic_service.close_cross_spread_market(
        active.plan_id,
        execution_mode="limit",
        limit_spread=Decimal("-1.1"),
    )

    assert captured["request"].action == "CLOSE_LONG"
    assert captured["kwargs"]["bybit_reduce_only"] is True
    assert captured["kwargs"]["mt5_reduce_only"] is True
    assert captured["kwargs"]["mt5_position_id"] == "778899"
    assert result.execution_batch.status == "failed"
    assert result.exit_plan.status == "active"


def test_uncertain_fok_close_enters_manual_intervention(monkeypatch) -> None:
    active = plan("active")
    triggered = plan("triggered", trigger_reason="manual")
    manual = plan("manual_intervention", trigger_reason="manual")
    closing_calls = []
    monkeypatch.setattr(synthetic_service, "get_exit_plan", lambda _plan_id: active)
    monkeypatch.setattr(
        synthetic_service,
        "claim_exit_plan",
        lambda *_args, **_kwargs: triggered,
    )
    monkeypatch.setattr(
        synthetic_service,
        "_prepare_limit_execution",
        lambda *_args, **_kwargs: pricing(),
    )
    monkeypatch.setattr(
        synthetic_service,
        "submit_cross_spread_fok_command",
        lambda *_args, **_kwargs: batch_response(
            "fok-close-unknown",
            status="manual_intervention",
        ),
    )
    monkeypatch.setattr(
        synthetic_service,
        "release_exit_plan_claim",
        lambda *_args: pytest.fail("Unknown FOK outcome must not release the plan"),
    )
    monkeypatch.setattr(
        synthetic_service,
        "mark_plan_closing",
        lambda plan_id, batch_id: closing_calls.append((plan_id, batch_id)),
    )
    monkeypatch.setattr(
        synthetic_service,
        "mark_plan_manual_intervention",
        lambda *_args, **_kwargs: manual,
    )

    result = synthetic_service.close_cross_spread_market(
        active.plan_id,
        execution_mode="limit",
        limit_spread=Decimal("-1.1"),
    )

    assert closing_calls == [("plan-fok-1", "fok-close-unknown")]
    assert result.execution_batch.status == "manual_intervention"
    assert result.exit_plan.status == "manual_intervention"
