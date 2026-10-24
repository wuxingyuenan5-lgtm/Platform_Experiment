from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal, Any

from pydantic import Field, field_validator

from app.research_data_schemas import ResearchApiModel
from app.research_local_data import read_local_json
from app.research_option_exposure import OptionExposureSnapshot
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
    price_lower: Decimal | None = None
    price_upper: Decimal | None = None
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
    option_distribution: dict[str, Any] = Field(default_factory=dict)
    option_exposure: dict[str, OptionExposureSnapshot] = Field(default_factory=dict)

    def apply_freshness(self, now: datetime | None = None) -> None:
        """Recheck observation age even when the producer leaves a valid old file.

        Retrieval times may deliberately stay unchanged for unchanged releases.
        Low-frequency periods therefore use their own publication tolerance.
        Unknown disclosure schedules retain producer status, never a daily SLA.
        """
        now = now or datetime.now(UTC)
        limits = {
            "daily": 7,
            "daily_business_day": 7,
            "exchange_trading_day": 7,
            "weekly": 14,
            "monthly": 75,
            "quarterly": 200,
            "daily_last_collected_snapshot": 2,
        }
        for group_id, group in self.groups.items():
            if group_id == "shfeGoldCurveHistory":
                continue  # Expired contracts are historical observations, not a current feed.
            for series in group:
                if series.status in {"error", "no_data"}:
                    continue
                limit = limits.get(series.frequency)
                if limit is None:
                    continue
                observed = (
                    series.observation_date
                    or series.as_of
                    or (series.observations[-1].date if series.observations else None)
                )
                try:
                    day = datetime.fromisoformat((observed or "").replace("Z", "+00:00")).date()
                except ValueError:
                    series.status = "degraded"
                    if "missing_observation_date" not in series.quality_flags:
                        series.quality_flags.append("missing_observation_date")
                    continue
                if now.date() - day > timedelta(days=limit):
                    series.status = "stale"
                    series.is_stale = True
                    if "stale_latest_observation" not in series.quality_flags:
                        series.quality_flags.append("stale_latest_observation")
        for snapshot in self.option_exposure.values():
            snapshot.apply_freshness(now)
        if any(s.status != "ready" for group_id, group in self.groups.items()
               if group_id != "shfeGoldCurveHistory" for s in group) or any(
            s.status != "ready" for s in self.option_exposure.values()
        ):
            if self.status == "ready":
                self.status = "partial"

    def stale_copy(self) -> MacroDashboardResponse:
        result = self.model_copy(deep=True)
        result.status = "stale"
        for snapshot in result.option_exposure.values():
            snapshot.status = "stale"
        for series in (item for group in result.groups.values() for item in group):
            if series.status not in {"error", "no_data"}:
                series.status = "stale"
                series.is_stale = True
                if "local_artifact_unavailable" not in series.quality_flags:
                    series.quality_flags.append("local_artifact_unavailable")
        return result


class MacroDashboardProvider:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._last_known_good: MacroDashboardResponse | None = None

    async def get(self) -> MacroDashboardResponse:
        try:
            document = await asyncio.to_thread(read_local_json, "public/v1/macro/dashboard.json")
            if document.get("schemaVersion") != "1.0":
                raise ResearchProviderError("macro_dashboard_schema_mismatch")
            contract = MacroDashboardResponse.model_validate(document)
            contract.apply_freshness()
            if not any(contract.groups.values()):
                raise ResearchProviderError("macro_dashboard_without_series")
            # The route only serializes this contract; stale_copy owns mutation isolation.
            self._last_known_good = contract
            return contract
        except Exception as exc:
            if self._last_known_good is not None:
                return self._last_known_good.stale_copy()
            if isinstance(exc, ResearchProviderError):
                raise
            raise ResearchProviderError(
                f"macro_dashboard_unavailable:{type(exc).__name__}"
            ) from exc
