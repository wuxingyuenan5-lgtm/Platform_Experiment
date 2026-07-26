from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from enum import StrEnum
from typing import Literal


class ChaseStatus(StrEnum):
    ACTIVE = "active"
    CANCEL_PENDING = "cancel_pending"
    FILLED = "filled"
    UNFILLED = "unfilled"
    MANUAL_STOPPED = "manual_stopped"
    RECONCILE_REQUIRED = "reconcile_required"


class ChaseActionType(StrEnum):
    NONE = "none"
    AMEND = "amend"
    CANCEL = "cancel"
    REPOST = "repost"
    FILL_DELTA = "fill_delta"
    COMPLETE = "complete"
    RECONCILE = "reconcile"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class ChasePolicy:
    ttl_seconds: float
    min_amend_ticks: int
    max_mutations: int
    cooldown_seconds: float

    def validate(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("PostOnly Chase TTL must be positive")
        if self.min_amend_ticks <= 0:
            raise ValueError("PostOnly amend threshold must be at least one Tick")
        if self.max_mutations < 0:
            raise ValueError("PostOnly maximum mutation count cannot be negative")
        if self.cooldown_seconds < 0:
            raise ValueError("PostOnly cooldown cannot be negative")


@dataclass(frozen=True, slots=True)
class PrivateChaseEvent:
    event_id: str
    sequence: int
    occurred_at: datetime
    kind: Literal["order", "execution", "disconnect"]
    external_order_id: str | None = None
    order_status: Literal[
        "new",
        "partially_filled",
        "filled",
        "cancel_pending",
        "canceled",
        "rejected",
    ] | None = None
    execution_quantity: Decimal = Decimal("0")
    execution_price: Decimal | None = None
    manual_cancel: bool = False
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ChaseAction:
    action_type: ChaseActionType
    price: Decimal | None = None
    fill_delta: Decimal = Decimal("0")
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ChaseState:
    side: Literal["buy", "sell"]
    requested_quantity: Decimal
    hard_limit_price: Decimal
    tick_size: Decimal
    started_at: datetime
    active_order_id: str | None = None
    active_price: Decimal | None = None
    cumulative_fill: Decimal = Decimal("0")
    cumulative_notional: Decimal = Decimal("0")
    status: ChaseStatus = ChaseStatus.ACTIVE
    mutation_count: int = 0
    last_mutation_at: datetime | None = None
    last_sequence: int | None = None
    seen_event_ids: frozenset[str] = frozenset()
    repost_after_cancel: bool = False
    planned_repost_price: Decimal | None = None

    @property
    def average_fill_price(self) -> Decimal | None:
        if self.cumulative_fill <= 0:
            return None
        return self.cumulative_notional / self.cumulative_fill


@dataclass(frozen=True, slots=True)
class ChaseTransition:
    state: ChaseState
    actions: tuple[ChaseAction, ...]


def maker_safe_price(
    *,
    side: Literal["buy", "sell"],
    best_bid: Decimal,
    best_ask: Decimal,
    hard_limit_price: Decimal,
    tick_size: Decimal,
) -> Decimal:
    _validate_prices(best_bid, best_ask, hard_limit_price, tick_size)
    if side == "buy":
        maker_price = _round_down(best_bid, tick_size)
        hard_bound = _round_down(hard_limit_price, tick_size)
        price = min(maker_price, hard_bound)
        if price >= best_ask:
            price = _round_down(best_ask - tick_size, tick_size)
    else:
        maker_price = _round_up(best_ask, tick_size)
        hard_bound = _round_up(hard_limit_price, tick_size)
        price = max(maker_price, hard_bound)
        if price <= best_bid:
            price = _round_up(best_bid + tick_size, tick_size)
    if price <= 0:
        raise ValueError("PostOnly maker-safe price must be positive")
    return price


def next_quote_action(
    state: ChaseState,
    policy: ChasePolicy,
    *,
    best_bid: Decimal,
    best_ask: Decimal,
    now: datetime,
) -> ChaseTransition:
    policy.validate()
    if state.status != ChaseStatus.ACTIVE:
        return ChaseTransition(state, ())
    if _elapsed_seconds(state.started_at, now) >= policy.ttl_seconds:
        next_state = replace(
            state,
            status=ChaseStatus.CANCEL_PENDING,
            repost_after_cancel=False,
            planned_repost_price=None,
        )
        return ChaseTransition(
            next_state,
            (ChaseAction(ChaseActionType.CANCEL, reason="PostOnly Chase TTL expired"),),
        )
    target = maker_safe_price(
        side=state.side,
        best_bid=best_bid,
        best_ask=best_ask,
        hard_limit_price=state.hard_limit_price,
        tick_size=state.tick_size,
    )
    if state.active_price is None or state.active_order_id is None:
        return ChaseTransition(
            replace(state, active_price=target),
            (ChaseAction(ChaseActionType.REPOST, price=target, reason="PostOnly order"),),
        )
    distance_ticks = abs(target - state.active_price) / state.tick_size
    if distance_ticks < policy.min_amend_ticks:
        return ChaseTransition(state, ())
    if state.mutation_count >= policy.max_mutations:
        next_state = replace(
            state,
            status=ChaseStatus.CANCEL_PENDING,
            repost_after_cancel=False,
            planned_repost_price=None,
        )
        return ChaseTransition(
            next_state,
            (
                ChaseAction(
                    ChaseActionType.CANCEL,
                    reason="PostOnly Chase maximum mutation count reached",
                ),
            ),
        )
    if state.last_mutation_at is not None and (
        _elapsed_seconds(state.last_mutation_at, now) < policy.cooldown_seconds
    ):
        return ChaseTransition(state, ())
    next_state = replace(
        state,
        active_price=target,
        mutation_count=state.mutation_count + 1,
        last_mutation_at=now,
    )
    return ChaseTransition(
        next_state,
        (ChaseAction(ChaseActionType.AMEND, price=target),),
    )


def request_cancel_repost(
    state: ChaseState,
    policy: ChasePolicy,
    *,
    replacement_price: Decimal,
    now: datetime,
) -> ChaseTransition:
    policy.validate()
    if state.status != ChaseStatus.ACTIVE or state.active_order_id is None:
        raise ValueError("Cancel/repost requires one active PostOnly order")
    if state.cumulative_fill > 0:
        return _reconcile(
            state,
            state.seen_event_ids,
            "Cancel/repost is blocked after a partial fill",
        )
    if state.mutation_count >= policy.max_mutations:
        return ChaseTransition(
            replace(state, status=ChaseStatus.CANCEL_PENDING),
            (ChaseAction(ChaseActionType.CANCEL, reason="Mutation limit reached"),),
        )
    if state.last_mutation_at is not None and (
        _elapsed_seconds(state.last_mutation_at, now) < policy.cooldown_seconds
    ):
        return ChaseTransition(state, ())
    _validate_bound(state, replacement_price)
    next_state = replace(
        state,
        status=ChaseStatus.CANCEL_PENDING,
        repost_after_cancel=True,
        planned_repost_price=replacement_price,
        mutation_count=state.mutation_count + 1,
        last_mutation_at=now,
    )
    return ChaseTransition(
        next_state,
        (
            ChaseAction(
                ChaseActionType.CANCEL,
                reason="Terminal cancel required before PostOnly repost",
            ),
        ),
    )


def apply_private_event(state: ChaseState, event: PrivateChaseEvent) -> ChaseTransition:
    if event.event_id in state.seen_event_ids:
        return ChaseTransition(state, ())
    seen = state.seen_event_ids | {event.event_id}
    if event.sequence < 0:
        return _reconcile(state, seen, "Private event sequence is invalid")
    if state.last_sequence is not None:
        if event.sequence <= state.last_sequence:
            return _reconcile(state, seen, "Private event sequence regressed")
        if event.sequence != state.last_sequence + 1:
            return _reconcile(state, seen, "Private event sequence gap detected")
    next_state = replace(state, seen_event_ids=seen, last_sequence=event.sequence)
    if state.status in {
        ChaseStatus.FILLED,
        ChaseStatus.UNFILLED,
        ChaseStatus.MANUAL_STOPPED,
        ChaseStatus.RECONCILE_REQUIRED,
    }:
        return ChaseTransition(next_state, ())
    if event.kind == "disconnect":
        return _reconcile(next_state, seen, event.reason or "Private stream disconnected")
    if event.kind == "execution":
        return _apply_execution(next_state, event)
    return _apply_order(next_state, event)


def _apply_execution(state: ChaseState, event: PrivateChaseEvent) -> ChaseTransition:
    quantity = event.execution_quantity
    if quantity <= 0 or event.execution_price is None or event.execution_price <= 0:
        return _reconcile(state, state.seen_event_ids, "Private execution payload is invalid")
    cumulative = state.cumulative_fill + quantity
    if cumulative > state.requested_quantity:
        return _reconcile(state, state.seen_event_ids, "Cumulative execution exceeds request")
    updated = replace(
        state,
        cumulative_fill=cumulative,
        cumulative_notional=state.cumulative_notional + quantity * event.execution_price,
    )
    delta_action = ChaseAction(
        ChaseActionType.FILL_DELTA,
        fill_delta=quantity,
        reason="New deduplicated Bybit execution",
    )
    if cumulative == state.requested_quantity:
        completed = replace(updated, status=ChaseStatus.FILLED)
        return ChaseTransition(
            completed,
            (
                delta_action,
                ChaseAction(
                    ChaseActionType.COMPLETE,
                    fill_delta=cumulative,
                    reason="Requested Bybit quantity is fully filled",
                ),
            ),
        )
    return ChaseTransition(updated, (delta_action,))


def _apply_order(state: ChaseState, event: PrivateChaseEvent) -> ChaseTransition:
    status = event.order_status
    if status is None:
        return _reconcile(state, state.seen_event_ids, "Private order payload is invalid")
    if event.external_order_id is not None and state.active_order_id not in {
        None,
        event.external_order_id,
    }:
        return _reconcile(
            state,
            state.seen_event_ids,
            "Private order identity changed unexpectedly",
        )
    updated = replace(
        state,
        active_order_id=event.external_order_id or state.active_order_id,
    )
    if status in {"new", "partially_filled"}:
        return ChaseTransition(updated, ())
    if status == "filled":
        if updated.cumulative_fill != updated.requested_quantity:
            return _reconcile(
                updated,
                updated.seen_event_ids,
                "Order filled status disagrees with cumulative executions",
            )
        return ChaseTransition(replace(updated, status=ChaseStatus.FILLED), ())
    if status == "cancel_pending":
        return ChaseTransition(replace(updated, status=ChaseStatus.CANCEL_PENDING), ())
    if status == "canceled":
        if event.manual_cancel:
            return ChaseTransition(
                replace(updated, status=ChaseStatus.MANUAL_STOPPED),
                (ChaseAction(ChaseActionType.STOP, reason="Manual cancel confirmed"),),
            )
        if updated.cumulative_fill > 0:
            return _reconcile(
                updated,
                updated.seen_event_ids,
                "PostOnly order canceled after a partial fill",
            )
        if updated.repost_after_cancel and updated.planned_repost_price is not None:
            repost_price = updated.planned_repost_price
            ready = replace(
                updated,
                status=ChaseStatus.ACTIVE,
                active_order_id=None,
                active_price=repost_price,
                repost_after_cancel=False,
                planned_repost_price=None,
            )
            return ChaseTransition(
                ready,
                (
                    ChaseAction(
                        ChaseActionType.REPOST,
                        price=repost_price,
                        reason="Terminal cancel confirmed",
                    ),
                ),
            )
        return ChaseTransition(
            replace(updated, status=ChaseStatus.UNFILLED),
            (ChaseAction(ChaseActionType.STOP, reason="PostOnly order canceled unfilled"),),
        )
    return _reconcile(updated, updated.seen_event_ids, event.reason or "PostOnly order rejected")


def _reconcile(
    state: ChaseState,
    seen: frozenset[str],
    reason: str,
) -> ChaseTransition:
    next_state = replace(
        state,
        seen_event_ids=seen,
        status=ChaseStatus.RECONCILE_REQUIRED,
    )
    return ChaseTransition(
        next_state,
        (ChaseAction(ChaseActionType.RECONCILE, reason=reason),),
    )


def _validate_bound(state: ChaseState, price: Decimal) -> None:
    if price <= 0:
        raise ValueError("PostOnly replacement price must be positive")
    if state.side == "buy" and price > state.hard_limit_price:
        raise ValueError("PostOnly buy replacement exceeds the hard price bound")
    if state.side == "sell" and price < state.hard_limit_price:
        raise ValueError("PostOnly sell replacement is below the hard price bound")
    steps = price / state.tick_size
    if steps != steps.to_integral_value():
        raise ValueError("PostOnly replacement price does not match Tick Size")


def _round_down(value: Decimal, tick_size: Decimal) -> Decimal:
    return (value / tick_size).to_integral_value(rounding=ROUND_FLOOR) * tick_size


def _round_up(value: Decimal, tick_size: Decimal) -> Decimal:
    return (value / tick_size).to_integral_value(rounding=ROUND_CEILING) * tick_size


def _validate_prices(
    best_bid: Decimal,
    best_ask: Decimal,
    hard_limit_price: Decimal,
    tick_size: Decimal,
) -> None:
    if min(best_bid, best_ask, hard_limit_price, tick_size) <= 0:
        raise ValueError("PostOnly prices and Tick Size must be positive")
    if best_bid >= best_ask:
        raise ValueError("Bybit best Bid must be below best Ask")


def _elapsed_seconds(start: datetime, end: datetime) -> float:
    return max(0.0, (end - start).total_seconds())
