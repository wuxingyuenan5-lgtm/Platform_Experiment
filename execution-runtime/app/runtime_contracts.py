from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

RUNTIME_COMMAND_CONTRACT_NAME = "runtime-command"
RUNTIME_EVENT_CONTRACT_NAME = "runtime-event"
RUNTIME_CONTRACT_VERSION = "1.0"
RUNTIME_PAYLOAD_VERSION = "1.0"


class RuntimeSubmitOrderCommandV1(BaseModel):
    contract_name: Literal["runtime-command"] = RUNTIME_COMMAND_CONTRACT_NAME
    contract_version: Literal["1.0"] = RUNTIME_CONTRACT_VERSION
    payload_version: Literal["1.0"] = RUNTIME_PAYLOAD_VERSION
    command_id: str
    platform_order_id: str
    strategy_instance_id: str | None = None
    account_id: str
    instrument_id: str
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = "market"
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    reduce_only: bool = False
    position_id: str | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_position_target(self) -> RuntimeSubmitOrderCommandV1:
        if self.position_id is not None and not self.reduce_only:
            raise ValueError("position_id requires reduce_only")
        return self


class RuntimeExecutionEventV1(BaseModel):
    contract_name: Literal["runtime-event"] = RUNTIME_EVENT_CONTRACT_NAME
    contract_version: Literal["1.0"] = RUNTIME_CONTRACT_VERSION
    payload_version: Literal["1.0"] = RUNTIME_PAYLOAD_VERSION
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    command_id: str
    platform_order_id: str
    event_type: Literal["order_acknowledged", "order_filled", "order_rejected"]
    external_order_id: str | None = None
    fill_price: Decimal | None = None
    fill_quantity: Decimal | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: str | None = None


def version_execution_events(events: list[BaseModel]) -> list[RuntimeExecutionEventV1]:
    return [
        RuntimeExecutionEventV1.model_validate(event.model_dump())
        for event in events
    ]


def runtime_contract_signature() -> dict[str, dict[str, object]]:
    return {
        "command": {
            "contractName": RUNTIME_COMMAND_CONTRACT_NAME,
            "contractVersion": RUNTIME_CONTRACT_VERSION,
            "payloadVersion": RUNTIME_PAYLOAD_VERSION,
            "fields": list(RuntimeSubmitOrderCommandV1.model_fields),
        },
        "event": {
            "contractName": RUNTIME_EVENT_CONTRACT_NAME,
            "contractVersion": RUNTIME_CONTRACT_VERSION,
            "payloadVersion": RUNTIME_PAYLOAD_VERSION,
            "fields": list(RuntimeExecutionEventV1.model_fields),
        },
    }
