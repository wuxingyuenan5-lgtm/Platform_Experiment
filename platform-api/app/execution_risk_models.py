from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

KillSwitchScope = Literal["global", "strategy", "account"]
FailureAction = Literal["hold_and_escalate", "auto_flatten"]
RiskStatus = Literal[
    "clear",
    "residual_exposure",
    "disposition_in_progress",
    "resolved",
    "escalated",
]
RiskActionName = Literal[
    "hold_and_escalate",
    "flatten_filled_legs",
    "cancel_open_legs",
    "substitute_hedge",
]
OrderSide = Literal["buy", "sell"]
RiskDisposition = Literal["resolved", "auto_flatten", "escalated"]

DEFAULT_MAX_LEG_DELAY_SECONDS = 10
DEFAULT_MAX_RESIDUAL_NOTIONAL = Decimal("100000")
DEFAULT_FAILURE_ACTION: FailureAction = "hold_and_escalate"


class KillSwitchUpdateRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    enabled: bool
    reason: str | None = Field(default=None, max_length=512)
    actor: str = Field(min_length=1, max_length=128)


class KillSwitchResponse(BaseModel):
    scope_type: KillSwitchScope = Field(alias="scopeType")
    scope_id: str = Field(alias="scopeId")
    enabled: bool
    reason: str | None = None
    actor: str
    version: int
    updated_at: datetime = Field(alias="updatedAt")


class ExecutionRiskPolicyUpdateRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    max_leg_delay_seconds: int = Field(alias="maxLegDelaySeconds", ge=1, le=3600)
    max_residual_notional: Decimal = Field(alias="maxResidualNotional", gt=0)
    failure_action: FailureAction = Field(alias="failureAction")
    actor: str = Field(min_length=1, max_length=128)


class ExecutionRiskPolicyResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    max_leg_delay_seconds: int = Field(alias="maxLegDelaySeconds")
    max_residual_notional: Decimal = Field(alias="maxResidualNotional")
    failure_action: FailureAction = Field(alias="failureAction")
    source: Literal["default", "configured"]
    actor: str
    updated_at: datetime = Field(alias="updatedAt")


class BatchRiskResponse(BaseModel):
    batch_id: str = Field(alias="batchId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    max_leg_delay_seconds: int = Field(alias="maxLegDelaySeconds")
    max_residual_notional: Decimal = Field(alias="maxResidualNotional")
    failure_action: FailureAction = Field(alias="failureAction")
    risk_status: RiskStatus = Field(alias="riskStatus")
    residual_exposure_notional: Decimal = Field(alias="residualExposureNotional")
    residual_currency: str = Field(alias="residualCurrency")
    data_quality_state: str = Field(alias="dataQualityState")
    first_fill_at: datetime | None = Field(default=None, alias="firstFillAt")
    last_leg_at: datetime | None = Field(default=None, alias="lastLegAt")
    risk_reason: str | None = Field(default=None, alias="riskReason")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class RiskActionRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    action: RiskActionName
    actor: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=512)
    replacement_account_id: str | None = Field(default=None, alias="replacementAccountId")
    replacement_instrument_id: str | None = Field(
        default=None, alias="replacementInstrumentId"
    )
    replacement_symbol: str | None = Field(default=None, alias="replacementSymbol")
    replacement_side: OrderSide | None = Field(default=None, alias="replacementSide")
    replacement_quantity: Decimal | None = Field(
        default=None, alias="replacementQuantity", gt=0
    )
    replacement_price: Decimal | None = Field(default=None, alias="replacementPrice", gt=0)

    @model_validator(mode="after")
    def validate_replacement(self) -> "RiskActionRequest":
        if self.action == "substitute_hedge":
            required = (
                self.replacement_account_id,
                self.replacement_instrument_id,
                self.replacement_symbol,
                self.replacement_side,
                self.replacement_quantity,
            )
            if any(value is None for value in required):
                raise ValueError("substitute_hedge requires a complete replacement leg")
        return self


class RiskActionResponse(BaseModel):
    risk_action_id: str = Field(alias="riskActionId")
    idempotency_key: str = Field(alias="idempotencyKey")
    batch_id: str = Field(alias="batchId")
    action: RiskActionName
    status: str
    actor: str
    reason: str | None = None
    generated_order_ids: list[str] = Field(alias="generatedOrderIds")
    failure_reason: str | None = Field(default=None, alias="failureReason")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class TradeCommandResult(Protocol):
    @property
    def platform_order_id(self) -> str | None: ...

    @property
    def status(self) -> str: ...
