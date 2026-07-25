from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ObservabilityState = Literal["complete", "partial", "unavailable"]
SectionState = Literal["complete", "unavailable"]


class CrossSpreadVenueObservabilityResponse(BaseModel):
    venue: str
    account_id: str = Field(alias="accountId")
    symbol: str
    status: ObservabilityState
    section_states: dict[str, SectionState] = Field(alias="sectionStates")
    account_risk: dict[str, Any] | None = Field(default=None, alias="accountRisk")
    positions: list[dict[str, Any]] = Field(default_factory=list)
    active_orders: list[dict[str, Any]] = Field(default_factory=list, alias="activeOrders")
    recent_orders: list[dict[str, Any]] = Field(default_factory=list, alias="recentOrders")
    recent_fills: list[dict[str, Any]] = Field(default_factory=list, alias="recentFills")
    warnings: list[str] = Field(default_factory=list)


class CrossSpreadObservabilityResponse(BaseModel):
    status: ObservabilityState
    history_hours: int = Field(alias="historyHours")
    bybit: CrossSpreadVenueObservabilityResponse
    mt5: CrossSpreadVenueObservabilityResponse
    warnings: list[str] = Field(default_factory=list)
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="asOf")
