from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.research_data_schemas import ResearchApiModel
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError


class MacroDashboardObservation(ResearchApiModel):
    date: str
    value: Decimal | None = None


class MacroDashboardSeries(ResearchApiModel):
    series_id: str
    label: str
    status: str
    latest_value: Decimal | None = None
    unit: str
    frequency: str
    timezone: str
    source: str
    source_series_id: str | None = None
    source_url: str | None = None
    observation_date: str | None = None
    as_of: str | None = None
    retrieved_at: datetime | None = None
    is_stale: bool = False
    methodology_version: str
    quality_flags: list[str] = Field(default_factory=list)
    observations: list[MacroDashboardObservation] = Field(default_factory=list)

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("macro dashboard timestamps must include a timezone")
        return value


class MacroDashboardResponse(ResearchApiModel):
    schema_version: Literal["1.0"] = "1.0"
    status: str
    as_of: str
    groups: dict[str, list[MacroDashboardSeries]]


class MacroDashboardProvider:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._last_known_good: MacroDashboardResponse | None = None

    async def get(self) -> MacroDashboardResponse:
        try:
            document = read_local_json("public/v1/macro/dashboard.json")
            if document.get("schemaVersion") != "1.0":
                raise ResearchProviderError("macro_dashboard_schema_mismatch")
            contract = MacroDashboardResponse.model_validate(document)
            if not any(contract.groups.values()):
                raise ResearchProviderError("macro_dashboard_without_series")
            self._last_known_good = contract.model_copy(deep=True)
            return contract
        except Exception as exc:
            if self._last_known_good is not None:
                return self._last_known_good.model_copy(deep=True)
            if isinstance(exc, ResearchProviderError):
                raise
            raise ResearchProviderError(
                f"macro_dashboard_unavailable:{type(exc).__name__}"
            ) from exc
