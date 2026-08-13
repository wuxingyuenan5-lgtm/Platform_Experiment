from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

import app.bybit_postonly_chase as chase
from app.bybit_postonly_chase import (
    ChaseActionType,
    ChasePolicy,
    ChaseState,
    ChaseStatus,
    PrivateChaseEvent,
    apply_private_event,
    maker_safe_price,
    next_quote_action,
)
from app.config import Settings

NOW = datetime(2026, 7, 26, tzinfo=UTC)
POLICY = ChasePolicy(
    ttl_seconds=10,
    min_amend_ticks=2,
    max_mutations=2,
    cooldown_seconds=1,
)


def state(**updates) -> ChaseState:
    values = {
        "side": "buy",
        "requested_quantity": Decimal("1"),
        "hard_limit_price": Decimal("2500.5"),
        "tick_size": Decimal("0.1"),
        "started_at": NOW,
        "active_order_id": "order-1",
        "active_price": Decimal("2500.0"),
    }
    values.update(updates)
    return ChaseState(**values)


def test_maker_safe_prices_respect_post_only_and_hard_bound() -> None:
    buy = maker_safe_price(
        side="buy",
        best_bid=Decimal("2500.4"),
        best_ask=Decimal("2500.5"),
        hard_limit_price=Decimal("2500.3"),
        tick_size=Decimal("0.1"),
    )
    sell = maker_safe_price(
        side="sell",
        best_bid=Decimal("2500.4"),
        best_ask=Decimal("2500.5"),
        hard_limit_price=Decimal("2500.7"),
        tick_size=Decimal("0.1"),
    )

    assert buy == Decimal("2500.3")
    assert buy < Decimal("2500.5")
    assert sell == Decimal("2500.7")
    assert sell > Decimal("2500.4")


def test_quote_amend_is_bounded_by_threshold_cooldown_and_maximum() -> None:
    first = next_quote_action(
        state(),
        POLICY,
        best_bid=Decimal("2500.3"),
        best_ask=Decimal("2500.4"),
        now=NOW + timedelta(seconds=2),
    )
    assert first.actions[0].action_type == ChaseActionType.AMEND
    assert first.actions[0].price == Decimal("2500.3")
    assert first.state.mutation_count == 1

    cooldown = next_quote_action(
        first.state,
        POLICY,
        best_bid=Decimal("2500.5"),
        best_ask=Decimal("2500.6"),
        now=NOW + timedelta(seconds=2, milliseconds=500),
    )
    assert cooldown.actions == ()

    second = next_quote_action(
        first.state,
        POLICY,
        best_bid=Decimal("2500.5"),
        best_ask=Decimal("2500.6"),
        now=NOW + timedelta(seconds=4),
    )
    assert second.actions[0].action_type == ChaseActionType.AMEND
    assert second.state.mutation_count == 2

    capped = next_quote_action(
        second.state,
        POLICY,
        best_bid=Decimal("2499.9"),
        best_ask=Decimal("2500.0"),
        now=NOW + timedelta(seconds=6),
    )
    assert capped.state.status == ChaseStatus.CANCEL_PENDING
    assert capped.actions[0].action_type == ChaseActionType.CANCEL


def test_ttl_stops_chase_with_cancel() -> None:
    result = next_quote_action(
        state(),
        POLICY,
        best_bid=Decimal("2500.2"),
        best_ask=Decimal("2500.3"),
        now=NOW + timedelta(seconds=10),
    )

    assert result.state.status == ChaseStatus.CANCEL_PENDING
    assert result.actions[0].action_type == ChaseActionType.CANCEL


def test_duplicate_execution_event_does_not_duplicate_fill_delta() -> None:
    event = PrivateChaseEvent(
        event_id="exec-1",
        sequence=1,
        occurred_at=NOW,
        kind="execution",
        external_order_id="order-1",
        execution_quantity=Decimal("0.4"),
        execution_price=Decimal("2500"),
    )

    first = apply_private_event(state(last_sequence=None), event)
    replay = apply_private_event(first.state, event)

    assert first.state.cumulative_fill == Decimal("0.4")
    assert first.actions[0].action_type == ChaseActionType.FILL_DELTA
    assert first.actions[0].fill_delta == Decimal("0.4")
    assert replay.state.cumulative_fill == Decimal("0.4")
    assert replay.actions == ()


def test_full_fill_completes_only_at_exact_requested_quantity() -> None:
    first = apply_private_event(
        state(last_sequence=None),
        PrivateChaseEvent(
            event_id="exec-1",
            sequence=1,
            occurred_at=NOW,
            kind="execution",
            execution_quantity=Decimal("0.4"),
            execution_price=Decimal("2500"),
        ),
    )
    second = apply_private_event(
        first.state,
        PrivateChaseEvent(
            event_id="exec-2",
            sequence=2,
            occurred_at=NOW + timedelta(milliseconds=1),
            kind="execution",
            execution_quantity=Decimal("0.6"),
            execution_price=Decimal("2500.2"),
        ),
    )

    assert second.state.status == ChaseStatus.FILLED
    assert second.state.cumulative_fill == Decimal("1.0")
    assert [action.action_type for action in second.actions] == [
        ChaseActionType.FILL_DELTA,
        ChaseActionType.COMPLETE,
    ]
    assert second.state.average_fill_price == Decimal("2500.12")


def test_sequence_gap_and_disconnect_require_reconciliation() -> None:
    gap = apply_private_event(
        state(last_sequence=3),
        PrivateChaseEvent(
            event_id="event-5",
            sequence=5,
            occurred_at=NOW,
            kind="order",
            order_status="new",
        ),
    )
    disconnect = apply_private_event(
        state(last_sequence=None),
        PrivateChaseEvent(
            event_id="disconnect-1",
            sequence=1,
            occurred_at=NOW,
            kind="disconnect",
            reason="socket closed",
        ),
    )

    assert gap.state.status == ChaseStatus.RECONCILE_REQUIRED
    assert gap.actions[0].action_type == ChaseActionType.RECONCILE
    assert disconnect.state.status == ChaseStatus.RECONCILE_REQUIRED
    assert disconnect.actions[0].action_type == ChaseActionType.RECONCILE


def test_cancel_after_partial_fill_requires_reconciliation() -> None:
    partial = apply_private_event(
        state(last_sequence=None),
        PrivateChaseEvent(
            event_id="exec-1",
            sequence=1,
            occurred_at=NOW,
            kind="execution",
            execution_quantity=Decimal("0.2"),
            execution_price=Decimal("2500"),
        ),
    )
    canceled = apply_private_event(
        partial.state,
        PrivateChaseEvent(
            event_id="order-canceled",
            sequence=2,
            occurred_at=NOW + timedelta(milliseconds=1),
            kind="order",
            external_order_id="order-1",
            order_status="canceled",
        ),
    )

    assert canceled.state.status == ChaseStatus.RECONCILE_REQUIRED
    assert canceled.actions[0].action_type == ChaseActionType.RECONCILE


def test_filled_order_without_execution_total_requires_reconciliation() -> None:
    result = apply_private_event(
        state(last_sequence=None),
        PrivateChaseEvent(
            event_id="order-filled",
            sequence=1,
            occurred_at=NOW,
            kind="order",
            external_order_id="order-1",
            order_status="filled",
        ),
    )

    assert result.state.status == ChaseStatus.RECONCILE_REQUIRED


def test_invalid_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="TTL"):
        ChasePolicy(0, 1, 1, 0).validate()


def test_initial_funding_chase_parameters_are_bounded() -> None:
    settings = Settings(_env_file=None)

    assert settings.bybit_postonly_chase_ttl_seconds == 15
    assert settings.bybit_postonly_chase_cooldown_seconds == 1
    assert settings.bybit_postonly_chase_max_mutations == 5
    assert settings.bybit_postonly_chase_min_amend_ticks == 1


def funding_state(**updates):
    values = {
        "batch_id": "funding-batch-1",
        "perpetual_quantity": Decimal("8"),
        "spot_quantity": Decimal("1"),
        "spot_step": Decimal("0.1"),
    }
    values.update(updates)
    return chase.FundingHedgeState(**values)


def funding_execution(exec_id: str, cumulative_fill: str):
    return chase.FundingHedgeEvent(
        event_id=exec_id,
        kind="execution",
        cumulative_perpetual_fill=Decimal(cumulative_fill),
    )


def test_funding_fill_releases_only_new_quantized_proportional_spot() -> None:
    first = chase.apply_funding_hedge_event(
        funding_state(),
        funding_execution("exec-1", "1"),
    )
    second = chase.apply_funding_hedge_event(
        first.state,
        funding_execution("exec-2", "3"),
    )
    complete = chase.apply_funding_hedge_event(
        second.state,
        funding_execution("exec-3", "8"),
    )

    assert first.actions == (
        chase.FundingSpotRelease(
            child_id="funding-batch-1:spot:0.1",
            quantity=Decimal("0.1"),
        ),
    )
    assert first.state.quantization_remainder == Decimal("0.025")
    assert second.actions[0].quantity == Decimal("0.2")
    assert second.state.spot_released == Decimal("0.3")
    assert second.state.quantization_remainder == Decimal("0.075")
    assert complete.actions[0].quantity == Decimal("0.7")
    assert complete.state.perpetual_cumulative_fill == Decimal("8")
    assert complete.state.spot_released == Decimal("1.0")
    assert complete.state.quantization_remainder == Decimal("0")
    assert complete.state.status == chase.FundingHedgeStatus.COMPLETE


def test_funding_release_never_exceeds_exact_proportional_entitlement() -> None:
    exact_entitlement = Decimal("0.099999999999999999999999999999")

    result = chase.apply_funding_hedge_event(
        funding_state(
            perpetual_quantity=Decimal("1"),
            spot_quantity=Decimal("1"),
        ),
        funding_execution("exec-precision-boundary", str(exact_entitlement)),
    )

    assert result.state.perpetual_cumulative_fill == exact_entitlement
    assert result.state.spot_released == Decimal("0")
    assert result.state.quantization_remainder == exact_entitlement
    assert result.actions == ()


def test_funding_duplicate_exec_id_releases_nothing() -> None:
    event = funding_execution("exec-1", "2")
    first = chase.apply_funding_hedge_event(funding_state(), event)
    replay = chase.apply_funding_hedge_event(first.state, event)

    assert first.state.spot_released == Decimal("0.2")
    assert replay.state == first.state
    assert replay.actions == ()


def test_funding_missing_exec_id_freezes_without_release() -> None:
    result = chase.apply_funding_hedge_event(
        funding_state(),
        funding_execution("", "2"),
    )

    assert result.state.status == chase.FundingHedgeStatus.RECONCILE_REQUIRED
    assert result.state.spot_released == Decimal("0")
    assert result.actions == ()


def test_funding_child_identity_is_stable_across_decimal_scale() -> None:
    result = chase.apply_funding_hedge_event(
        funding_state(spot_step=Decimal("0.10")),
        funding_execution("exec-1", "1"),
    )

    assert result.actions[0].child_id == "funding-batch-1:spot:0.1"


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"perpetual_cumulative_fill": Decimal("8.1")}, "perpetual"),
        ({"spot_released": Decimal("1.1")}, "Spot release"),
        ({"spot_released": Decimal("0.05")}, "quantity step"),
    ],
)
def test_funding_state_rejects_ceiling_or_step_violations(updates, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        funding_state(**updates)


@pytest.mark.parametrize("cumulative_fill", ["1", "9"])
def test_funding_non_monotonic_or_excess_fill_freezes_without_release(
    cumulative_fill: str,
) -> None:
    initial = funding_state(
        perpetual_cumulative_fill=Decimal("2"),
        spot_released=Decimal("0.2"),
    )

    result = chase.apply_funding_hedge_event(
        initial,
        funding_execution("exec-invalid", cumulative_fill),
    )

    assert result.state.status == chase.FundingHedgeStatus.RECONCILE_REQUIRED
    assert result.state.perpetual_cumulative_fill == Decimal("2")
    assert result.state.spot_released == Decimal("0.2")
    assert result.actions == ()


@pytest.mark.parametrize("kind", ["disconnect", "result_unknown", "order_unknown"])
def test_funding_unknown_state_freezes_future_side_effects(kind: str) -> None:
    frozen = chase.apply_funding_hedge_event(
        funding_state(),
        chase.FundingHedgeEvent(event_id=f"{kind}-1", kind=kind),
    )
    after_freeze = chase.apply_funding_hedge_event(
        frozen.state,
        funding_execution("exec-after-freeze", "8"),
    )

    assert frozen.state.status == chase.FundingHedgeStatus.RECONCILE_REQUIRED
    assert frozen.actions == ()
    assert after_freeze.state.spot_released == Decimal("0")
    assert after_freeze.actions == ()
