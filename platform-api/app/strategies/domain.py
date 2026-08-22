from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrategyInstructionAction(StrEnum):
    OPEN = "open"
    CLOSE = "close"
    RISK_DISPOSITION = "risk_disposition"


class StrategyInstructionStatus(StrEnum):
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    RECONCILING = "reconciling"
    COMPLETED = "completed"
    MANUAL_INTERVENTION = "manual_intervention"
    REJECTED = "rejected"
    FAILED = "failed"


class ExecutionPolicy(StrEnum):
    MARKET = "market"
    FOK = "fok"
    POST_ONLY_CHASE = "post_only_chase"


class ReleaseCondition(StrEnum):
    TERMINAL_FULL_FILL = "terminal_full_fill"
    INCREMENTAL_CUMULATIVE_FILL = "incremental_cumulative_fill"


class SimulationCompatibilityPolicy(StrEnum):
    FAKE_GATEWAY_MARKET = "fake_gateway_market"


class ExecutionPlanLeg(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    account_id: str
    instrument_id: str
    external_symbol: str
    side: Literal["buy", "sell"]
    maximum_quantity: Decimal = Field(gt=0)
    sequence: int = Field(ge=1)
    execution_policy: ExecutionPolicy
    depends_on: str | None = None
    release_condition: ReleaseCondition | None = None
    release_ratio: Decimal | None = Field(default=None, gt=0)
    release_cap: Decimal | None = Field(default=None, gt=0)
    quantity_step: Decimal = Field(gt=0)
    price_tick: Decimal = Field(default=Decimal("0.01"), gt=0)
    rounding_rule: str = "floor_to_step"
    contract_multiplier: Decimal = Field(gt=0)
    minimum_quantity: Decimal = Field(gt=0)
    ttl_seconds: int = Field(default=15, gt=0)
    check_interval_seconds: int = Field(default=1, gt=0)
    max_mutations: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_release(self) -> ExecutionPlanLeg:
        if self.depends_on is None:
            if any(
                value is not None
                for value in (self.release_condition, self.release_ratio, self.release_cap)
            ):
                raise ValueError("root plan legs cannot define release fields")
        elif None in (self.release_condition, self.release_ratio, self.release_cap):
            raise ValueError("dependent plan legs require release fields")
        return self


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    adapter_version: str
    strategy_key: str
    action: StrategyInstructionAction
    legs: tuple[ExecutionPlanLeg, ...] = Field(min_length=2)
    failure_rule: str = "manual_intervention_and_reconcile"
    simulation_compatibility_policy: SimulationCompatibilityPolicy | None = None
    account_capability_snapshot: dict[str, str]
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_sequence(self) -> ExecutionPlan:
        roles = [leg.role for leg in self.legs]
        if len(set(roles)) != len(roles):
            raise ValueError("plan leg roles must be unique")
        if [leg.sequence for leg in self.legs] != list(range(1, len(self.legs) + 1)):
            raise ValueError("plan legs must have consecutive execution sequence")
        return self
