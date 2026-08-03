from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

SpreadDirection = Literal["LONG_SPREAD", "SHORT_SPREAD"]
SyntheticAction = Literal[
    "OPEN_LONG_SPREAD",
    "CLOSE_LONG_SPREAD",
    "OPEN_SHORT_SPREAD",
    "CLOSE_SHORT_SPREAD",
]
SyntheticExecutionType = Literal["MARKET", "LIMIT"]
SyntheticTriggerReason = Literal[
    "MANUAL",
    "STRATEGY",
    "TAKE_PROFIT",
    "STOP_LOSS",
    "KILL_SWITCH",
    "RISK_REDUCTION",
]
LegacyMarketAction = Literal["OPEN_LONG", "CLOSE_LONG", "OPEN_SHORT", "CLOSE_SHORT"]


@dataclass(frozen=True, slots=True)
class SyntheticOrderIntent:
    action: SyntheticAction
    execution_type: SyntheticExecutionType
    trigger_reason: SyntheticTriggerReason

    @property
    def direction(self) -> SpreadDirection:
        return "LONG_SPREAD" if "LONG" in self.action else "SHORT_SPREAD"

    @property
    def is_open(self) -> bool:
        return self.action.startswith("OPEN_")

    @property
    def is_close(self) -> bool:
        return not self.is_open


_ACTION_TO_COMMAND: dict[SyntheticAction, LegacyMarketAction] = {
    "OPEN_LONG_SPREAD": "OPEN_LONG",
    "CLOSE_LONG_SPREAD": "CLOSE_LONG",
    "OPEN_SHORT_SPREAD": "OPEN_SHORT",
    "CLOSE_SHORT_SPREAD": "CLOSE_SHORT",
}
_OPEN_ACTIONS: set[SyntheticAction] = {"OPEN_LONG_SPREAD", "OPEN_SHORT_SPREAD"}
_OPEN_TRIGGER_REASONS: set[SyntheticTriggerReason] = {"MANUAL", "STRATEGY"}
_EXECUTION_TYPES: set[SyntheticExecutionType] = {"MARKET", "LIMIT"}
_TRIGGER_REASONS: set[SyntheticTriggerReason] = {
    "MANUAL",
    "STRATEGY",
    "TAKE_PROFIT",
    "STOP_LOSS",
    "KILL_SWITCH",
    "RISK_REDUCTION",
}


def build_open_intent(
    direction: SpreadDirection,
    execution_type: str,
    *,
    trigger_reason: str = "MANUAL",
) -> SyntheticOrderIntent:
    action: SyntheticAction = (
        "OPEN_LONG_SPREAD" if direction == "LONG_SPREAD" else "OPEN_SHORT_SPREAD"
    )
    return build_intent(
        action,
        execution_type=execution_type,
        trigger_reason=trigger_reason,
    )


def build_close_intent(
    direction: SpreadDirection,
    execution_type: str,
    *,
    trigger_reason: str,
) -> SyntheticOrderIntent:
    action: SyntheticAction = (
        "CLOSE_LONG_SPREAD" if direction == "LONG_SPREAD" else "CLOSE_SHORT_SPREAD"
    )
    return build_intent(
        action,
        execution_type=execution_type,
        trigger_reason=trigger_reason,
    )


def build_intent(
    action: SyntheticAction,
    *,
    execution_type: str,
    trigger_reason: str,
) -> SyntheticOrderIntent:
    normalized_execution_type = normalize_execution_type(execution_type)
    normalized_trigger_reason = normalize_trigger_reason(trigger_reason)
    if action in _OPEN_ACTIONS and normalized_trigger_reason not in _OPEN_TRIGGER_REASONS:
        raise ValueError(
            f"Open action {action} cannot use trigger reason {normalized_trigger_reason}"
        )
    return SyntheticOrderIntent(
        action=action,
        execution_type=normalized_execution_type,
        trigger_reason=normalized_trigger_reason,
    )


def normalize_execution_type(value: str) -> SyntheticExecutionType:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    if normalized not in _EXECUTION_TYPES:
        raise ValueError(f"Unsupported synthetic execution type: {value}")
    return cast(SyntheticExecutionType, normalized)


def normalize_trigger_reason(value: str | None) -> SyntheticTriggerReason:
    normalized = (value or "MANUAL").strip().upper().replace("-", "_").replace(" ", "_")
    if normalized not in _TRIGGER_REASONS:
        raise ValueError(f"Unsupported synthetic trigger reason: {value}")
    return cast(SyntheticTriggerReason, normalized)


def command_action(intent: SyntheticOrderIntent) -> LegacyMarketAction:
    """Map a business action to the existing four-action execution command vocabulary."""

    return _ACTION_TO_COMMAND[intent.action]


def market_command_action(intent: SyntheticOrderIntent) -> LegacyMarketAction:
    if intent.execution_type != "MARKET":
        raise ValueError("Only MARKET synthetic intents map to the existing Market executor")
    return command_action(intent)
