from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.strategies import funding_workspace


def test_funding_execution_context_uses_explicit_spot_and_perp_runtime_scopes(
    monkeypatch,
) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_runtime_get(path: str, *, params=None):
        calls.append((path, params))
        if path.startswith("/venue/quotes/"):
            return {
                "mid": "100",
                "asOf": "2026-08-25T00:00:00Z",
                "dataQualityState": "complete",
                "fundingRate": "0.0001" if params["instrumentType"] == "crypto_perp" else None,
                "nextFundingTime": "2026-08-25T08:00:00Z"
                if params["instrumentType"] == "crypto_perp"
                else None,
            }
        if path.startswith("/venue/instruments/"):
            return {
                "priceTick": "0.1",
                "quantityStep": "0.001",
                "minQuantity": "0.001",
                "contractMultiplier": "1",
            }
        if path == "/venue/economic-events":
            return []
        if path == "/status":
            return {
                "status": "available",
                "capabilities": {"liveWriteEnabled": False, "adapters": []},
            }
        raise AssertionError(path)

    monkeypatch.setattr(
        funding_workspace,
        "_funding_account_binding",
        lambda role: {
            "account_id": "bybit-live-main",
            "venue_id": "venue-bybit",
            "venue_code": "CRYPTO_TEST",
        },
    )
    monkeypatch.setattr(
        funding_workspace,
        "_resolve_pair",
        lambda perpetual_symbol, spot_symbol: {
            "perpetualSymbol": "BTCUSDT",
            "spotSymbol": "BTCUSDT",
        },
    )
    monkeypatch.setattr(funding_workspace, "list_funding_pairs", lambda: [])
    monkeypatch.setattr(funding_workspace, "_runtime_get", fake_runtime_get)
    monkeypatch.setattr(
        funding_workspace,
        "_balance_snapshot",
        lambda account_id, currency: {
            "currency": currency,
            "equity": "500",
            "availableBalance": "300",
            "dataQualityState": "complete",
            "asOf": "2026-08-25T00:00:00Z",
        },
    )
    monkeypatch.setattr(
        funding_workspace,
        "_reservation_summary",
        lambda account_id, currency: {
            "activeReserved": Decimal("25"),
            "fundingReserved": Decimal("10"),
            "crossReserved": Decimal("15"),
            "claims": [],
        },
    )
    monkeypatch.setattr(
        funding_workspace,
        "get_funding_controlled_live_readiness",
        lambda strategy_instance_id, account_id: {"ready": False},
    )

    payload = funding_workspace.get_funding_execution_context(
        perpetual_symbol="BTCUSDT",
        spot_symbol="BTCUSDT",
        notional=Decimal("100"),
    )

    assert payload["activeReservation"]["fundingAvailable"] == "275"
    assert calls[:4] == [
        (
            "/venue/quotes/BTCUSDT",
            {"accountId": "bybit-live-main", "instrumentType": "crypto_perp", "category": "linear"},
        ),
        (
            "/venue/quotes/BTCUSDT",
            {"accountId": "bybit-live-main", "instrumentType": "crypto_spot", "category": "spot"},
        ),
        (
            "/venue/instruments/BTCUSDT",
            {"accountId": "bybit-live-main", "instrumentType": "crypto_perp", "category": "linear"},
        ),
        (
            "/venue/instruments/BTCUSDT",
            {"accountId": "bybit-live-main", "instrumentType": "crypto_spot", "category": "spot"},
        ),
    ]


def test_close_summary_and_group_snapshot_track_remaining_closable_quantity(monkeypatch) -> None:
    instructions = [
        {
            "instructionId": "open-1",
            "action": "open",
            "status": "completed",
            "executionBatchId": "batch-open-1",
            "updatedAt": "2026-08-25T00:00:00Z",
            "executionPlan": {
                "legs": [
                    {
                        "role": "perpetual_leg",
                        "externalSymbol": "BTCUSDT",
                        "side": "sell",
                        "maximumQuantity": "0.020",
                    },
                    {
                        "role": "spot_leg",
                        "externalSymbol": "BTCUSDT",
                        "side": "buy",
                        "maximumQuantity": "0.020",
                    },
                ]
            },
        },
        {
            "instructionId": "close-1",
            "action": "close",
            "status": "completed",
            "requestedParameters": {
                "targetOpenInstructionId": "open-1",
                "perpetualQuantity": "0.005",
            },
        },
    ]

    monkeypatch.setattr(
        funding_workspace,
        "get_instruction",
        lambda instruction_id: instructions[0],
    )
    def workspace_state(instruction):
        if instruction["instructionId"] == "close-1":
            return {
                "executionState": "completed",
                "spotReleases": [{"cumulativeSpotQuantity": "0.003"}],
                "cumulativePerpetualFill": "0.003",
            }
        return {
            "executionState": "completed",
            "spotReleases": [{"cumulativeSpotQuantity": "0.020"}],
            "cumulativePerpetualFill": "0.020",
        }

    monkeypatch.setattr(funding_workspace, "_workspace_state_from_instruction", workspace_state)
    monkeypatch.setattr(
        funding_workspace,
        "_funding_fees_for_batch",
        lambda batch_id: (Decimal("1"), Decimal("2")),
    )

    summary = funding_workspace._close_summary_by_open_instruction(instructions)
    group = funding_workspace._funding_group_snapshot(
        instruction_id="open-1",
        batch_id="batch-open-1",
        close_summary=summary["open-1"],
    )

    assert group["alreadyClosedQuantity"] == "0.003"
    assert group["authoritativeClosedQuantity"] == "0.003"
    assert group["resultUnknownReservedQuantity"] == "0.002"
    assert group["remainingClosableQuantity"] == "0.015"
    assert group["hedgedQuantity"] == "0.020"


@pytest.mark.parametrize(
    (
        "execution_state",
        "spot_fill",
        "order_id",
        "expected_pending",
        "expected_unknown",
        "expected_remaining",
    ),
    [
        ("executing", "0.002", None, "0.003", "0", "0.015"),
        ("result_unknown", "0.002", "order-1", "0", "0.003", "0.015"),
        ("manual_intervention", "0.002", "order-1", "0", "0.003", "0.015"),
        ("failed", "0.002", "order-1", "0", "0.003", "0.015"),
        ("failed", "0", None, "0", "0", "0.020"),
    ],
)
def test_close_summary_separates_authoritative_pending_and_uncertain_quantity(
    monkeypatch,
    execution_state: str,
    spot_fill: str,
    order_id: str | None,
    expected_pending: str,
    expected_unknown: str,
    expected_remaining: str,
) -> None:
    instructions = [
        {
            "instructionId": "close-1",
            "action": "close",
            "status": execution_state,
            "requestedParameters": {
                "targetOpenInstructionId": "open-1",
                "perpetualQuantity": "0.005",
            },
        }
    ]
    monkeypatch.setattr(
        funding_workspace,
        "_workspace_state_from_instruction",
        lambda instruction: {
            "executionState": execution_state,
            "attempts": [{"orderId": order_id}] if order_id else [],
            "spotReleases": [{"cumulativeSpotQuantity": spot_fill, "orderId": order_id}],
            "cumulativePerpetualFill": spot_fill,
        },
    )

    summary = funding_workspace._close_summary_by_open_instruction(instructions)["open-1"]

    expected_authoritative = Decimal(spot_fill)
    assert summary["authoritativeClosedQuantity"] == expected_authoritative
    assert summary["pendingCloseQuantity"] == Decimal(expected_pending)
    assert summary["resultUnknownReservedQuantity"] == Decimal(expected_unknown)
    reserved = sum(summary.values(), Decimal("0"))
    assert Decimal("0.020") - reserved == Decimal(expected_remaining)


def test_position_groups_exclude_fully_closed_group_from_active_scope(monkeypatch) -> None:
    instructions = [
        {
            "instructionId": "open-1",
            "action": "open",
            "status": "completed",
            "executionBatchId": "batch-open-1",
        }
    ]
    monkeypatch.setattr(funding_workspace, "list_instructions", lambda strategy_id: instructions)
    monkeypatch.setattr(
        funding_workspace,
        "_close_summary_by_open_instruction",
        lambda rows: {"open-1": {}},
    )
    monkeypatch.setattr(
        funding_workspace,
        "_funding_group_snapshot",
        lambda **kwargs: {"lifecycleState": "history", "instructionId": "open-1"},
    )

    assert funding_workspace.list_funding_position_groups(scope="active") == []
    assert funding_workspace.list_funding_position_groups(scope="history") == [
        {"lifecycleState": "history", "instructionId": "open-1"}
    ]


def test_workspace_lookup_recovers_instruction_by_idempotency(monkeypatch) -> None:
    monkeypatch.setattr(
        funding_workspace,
        "get_instruction_by_idempotency",
        lambda strategy_id, key: {"instructionId": "instruction-1"},
    )
    monkeypatch.setattr(
        funding_workspace,
        "get_funding_instruction_workspace",
        lambda instruction_id: {"instruction": {"instructionId": instruction_id}},
    )

    assert funding_workspace.get_funding_instruction_workspace_by_idempotency(
        "funding:recover-1"
    ) == {"instruction": {"instructionId": "instruction-1"}}


def test_submit_close_rejects_quantity_above_remaining(monkeypatch) -> None:
    monkeypatch.setattr(
        funding_workspace,
        "get_instruction",
        lambda instruction_id: {"executionBatchId": "batch-open-1"},
    )
    monkeypatch.setattr(
        funding_workspace,
        "list_instructions",
        lambda strategy_instance_id: [],
    )
    monkeypatch.setattr(
        funding_workspace,
        "_funding_group_snapshot",
        lambda **kwargs: {
            "remainingClosableQuantity": "0.010",
            "perpetualSymbol": "BTCUSDT",
            "spotSymbol": "BTCUSDT",
        },
    )

    with pytest.raises(HTTPException, match="exceeds remaining hedged quantity"):
        funding_workspace.submit_funding_instruction(
            action="close",
            idempotency_key="funding:test-close",
            perpetual_symbol="BTCUSDT",
            spot_symbol="BTCUSDT",
            quantity=Decimal("0.020"),
            requested_by="demo_ceo",
            target_open_instruction_id="open-1",
        )
