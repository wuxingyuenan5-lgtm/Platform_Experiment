from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class VenueEconomicEventSnapshot(BaseModel):
    source: str
    external_event_id: str = Field(alias="externalEventId")
    event_type: Literal["funding", "swap", "fee"] = Field(alias="eventType")
    account_id: str = Field(alias="accountId")
    instrument_id: str | None = Field(default=None, alias="instrumentId")
    symbol: str | None = None
    amount: Decimal
    currency: str
    occurred_at: datetime = Field(alias="occurredAt")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")
    payload: dict[str, object] = Field(default_factory=dict)


class GatewayAdapterCapability(BaseModel):
    adapter: str
    environment: str
    configured: bool
    operational: bool
    account_ids: list[str] = Field(default_factory=list, alias="accountIds")
    capabilities: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(
        default_factory=list,
        alias="missingRequirements",
    )
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="checkedAt")


class GatewayCapabilitiesResponse(BaseModel):
    gateway: str
    environment: str
    adapters: list[GatewayAdapterCapability]
