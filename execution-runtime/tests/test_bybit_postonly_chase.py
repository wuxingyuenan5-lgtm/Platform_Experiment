from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

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
