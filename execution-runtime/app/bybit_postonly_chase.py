from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
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


class FundingHedgeStatus(StrEnum):
    ACTIVE = "active"
    COMPLETE = "complete"
    RECONCILE_REQUIRED = "reconcile_required"


@dataclass(frozen=True, slots=True)
class FundingHedgeEvent:
    event_id: str
    kind: Literal[
        "execution",
        "disconnect",
        "result_unknown",
        "order_unknown",
        "sequence_mismatch",
        "identity_mismatch",
        "cancel_unconfirmed",
    ]
    cumulative_perpetual_fill: Decimal | None = None


@dataclass(frozen=True, slots=True)
class FundingSpotRelease:
    child_id: str
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class FundingHedgeState:
    batch_id: str
    perpetual_quantity: Decimal
    spot_quantity: Decimal
    spot_step: Decimal
    perpetual_cumulative_fill: Decimal = Decimal("0")
    spot_released: Decimal = Decimal("0")
    quantization_remainder: Decimal = Decimal("0")
    status: FundingHedgeStatus = FundingHedgeStatus.ACTIVE
    seen_exec_ids: frozenset[str] = frozenset()
    reconciliation_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.batch_id:
            raise ValueError("Funding hedge batch identity is required")
        if min(self.perpetual_quantity, self.spot_quantity, self.spot_step) <= 0:
            raise ValueError("Funding hedge quantities and Spot step must be positive")
        if _integer_step_count(self.spot_quantity, self.spot_step) is None:
            raise ValueError("Funding Spot quantity must match the configured quantity step")
        if not Decimal("0") <= self.perpetual_cumulative_fill <= self.perpetual_quantity:
            raise ValueError("Funding perpetual cumulative fill exceeds its instruction quantity")
        if not Decimal("0") <= self.spot_released <= self.spot_quantity:
            raise ValueError("Funding Spot release exceeds its instruction quantity")
        if _integer_step_count(self.spot_released, self.spot_step) is None:
            raise ValueError("Funding Spot release must match the configured quantity step")


@dataclass(frozen=True, slots=True)
class FundingHedgeTransition:
    state: FundingHedgeState
    actions: tuple[FundingSpotRelease, ...]


def apply_funding_hedge_event(
    state: FundingHedgeState,
    event: FundingHedgeEvent,
) -> FundingHedgeTransition:
    if state.status != FundingHedgeStatus.ACTIVE:
        return FundingHedgeTransition(state, ())
    if not event.event_id:
        return FundingHedgeTransition(
            replace(
                state,
                status=FundingHedgeStatus.RECONCILE_REQUIRED,
                reconciliation_reason="Funding hedge event identity is missing",
            ),
            (),
        )
    if event.kind != "execution":
        return FundingHedgeTransition(
            replace(
                state,
                status=FundingHedgeStatus.RECONCILE_REQUIRED,
                reconciliation_reason=f"Funding hedge stopped on {event.kind}",
            ),
            (),
        )
    if event.event_id in state.seen_exec_ids:
        return FundingHedgeTransition(state, ())
    cumulative_fill = event.cumulative_perpetual_fill
    if (
        cumulative_fill is None
        or cumulative_fill <= state.perpetual_cumulative_fill
        or cumulative_fill > state.perpetual_quantity
    ):
        return FundingHedgeTransition(
            replace(
                state,
                status=FundingHedgeStatus.RECONCILE_REQUIRED,
                reconciliation_reason=(
                    "Funding perpetual cumulative fill is non-monotonic or exceeds the instruction"
                ),
            ),
            (),
        )

    entitlement_steps, releasable_spot, quantization_remainder = (
        _funding_spot_entitlement(
            cumulative_fill=cumulative_fill,
            perpetual_quantity=state.perpetual_quantity,
            spot_quantity=state.spot_quantity,
            spot_step=state.spot_step,
        )
    )
    released_steps = _integer_step_count(state.spot_released, state.spot_step)
    if released_steps is None:
        return FundingHedgeTransition(
            replace(
                state,
                status=FundingHedgeStatus.RECONCILE_REQUIRED,
                reconciliation_reason="Funding Spot release is not aligned to its quantity step",
            ),
            (),
        )
    release_steps = entitlement_steps - released_steps
    if release_steps < 0 or releasable_spot > state.spot_quantity:
        return FundingHedgeTransition(
            replace(
                state,
                status=FundingHedgeStatus.RECONCILE_REQUIRED,
                reconciliation_reason="Funding Spot release would exceed its instruction ceiling",
            ),
            (),
        )
    release_quantity = _decimal_times_int_exact(state.spot_step, release_steps)

    status = (
        FundingHedgeStatus.COMPLETE
        if cumulative_fill == state.perpetual_quantity
        and releasable_spot == state.spot_quantity
        else FundingHedgeStatus.ACTIVE
    )
    updated = replace(
        state,
        perpetual_cumulative_fill=cumulative_fill,
        spot_released=releasable_spot,
        quantization_remainder=quantization_remainder,
        status=status,
        seen_exec_ids=state.seen_exec_ids | {event.event_id},
    )
    if release_quantity == 0:
        return FundingHedgeTransition(updated, ())
    return FundingHedgeTransition(
        updated,
        (
            FundingSpotRelease(
                child_id=f"{state.batch_id}:spot:{_canonical_decimal(releasable_spot)}",
                quantity=release_quantity,
            ),
        ),
    )


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


def _funding_spot_entitlement(
    *,
    cumulative_fill: Decimal,
    perpetual_quantity: Decimal,
    spot_quantity: Decimal,
    spot_step: Decimal,
) -> tuple[int, Decimal, Decimal]:
    cumulative_numerator, cumulative_denominator = cumulative_fill.as_integer_ratio()
    perpetual_numerator, perpetual_denominator = perpetual_quantity.as_integer_ratio()
    spot_numerator, spot_denominator = spot_quantity.as_integer_ratio()
    step_numerator, step_denominator = spot_step.as_integer_ratio()
    entitlement_steps = (
        cumulative_numerator
        * spot_numerator
        * perpetual_denominator
        * step_denominator
    ) // (
        cumulative_denominator
        * spot_denominator
        * perpetual_numerator
        * step_numerator
    )

    precision = (
        sum(
            len(value.as_tuple().digits)
            for value in (
                cumulative_fill,
                perpetual_quantity,
                spot_quantity,
                spot_step,
            )
        )
        + len(str(entitlement_steps))
        + 16
    )
    with localcontext() as context:
        context.prec = max(context.prec, precision)
        context.rounding = ROUND_FLOOR
        releasable_spot = _decimal_times_int_exact(spot_step, entitlement_steps)
        proportional_spot = cumulative_fill * spot_quantity / perpetual_quantity
        remainder = max(Decimal("0"), proportional_spot - releasable_spot)
    return entitlement_steps, releasable_spot, remainder


def _integer_step_count(quantity: Decimal, step: Decimal) -> int | None:
    quantity_numerator, quantity_denominator = quantity.as_integer_ratio()
    step_numerator, step_denominator = step.as_integer_ratio()
    numerator = quantity_numerator * step_denominator
    denominator = quantity_denominator * step_numerator
    quotient, remainder = divmod(numerator, denominator)
    return quotient if remainder == 0 else None


def _decimal_times_int_exact(value: Decimal, multiplier: int) -> Decimal:
    if multiplier < 0:
        raise ValueError("Decimal multiplier cannot be negative")
    precision = len(value.as_tuple().digits) + len(str(multiplier)) + 1
    with localcontext() as context:
        context.prec = max(context.prec, precision)
        return value * multiplier


def _canonical_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


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
