from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

import httpx
from pydantic import Field, field_validator

from app.research_data_schemas import (
    MacroExpectationEvent,
    MacroProbabilityPoint,
    ResearchApiModel,
)
from app.research_provider_errors import ResearchProviderError

PLATFORM_DATA_EXPECTATIONS_URL = (
    "https://raw.githubusercontent.com/wuxingyuenan5-lgtm/platform-data/"
    "macro-expectations-phase-1a/public/v1/macro/expectations.json"
)
MacroCategory = Literal["monetary_policy", "macro", "geopolitics", "election"]
MacroExpectationFeedStatus = Literal[
    "ready",
    "no_data",
    "not_configured",
    "stale",
    "error",
]


class MacroExpectationFeedPoint(ResearchApiModel):
    observed_at: datetime
    probability: float = Field(ge=0, le=100)

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("macro expectation timestamps must include a timezone")
        return value


class MacroExpectationFeedEvent(ResearchApiModel):
    id: str = Field(min_length=1, max_length=160)
    label: str = Field(min_length=1, max_length=512)
    category: MacroCategory
    probability: float = Field(ge=0, le=100)
    history: list[MacroExpectationFeedPoint] = Field(default_factory=list)


class MacroExpectationFeedResponse(ResearchApiModel):
    status: MacroExpectationFeedStatus
    source: str = Field(min_length=1, max_length=256)
    updated_at: datetime
    events: list[MacroExpectationFeedEvent] = Field(default_factory=list)

    @field_validator("updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("macro expectation timestamps must include a timezone")
        return value


class MacroResearchProvider:
    """Reads the configuration-driven macro expectation artifact from platform-data.

    Event discovery and probability extraction happen upstream. This provider never scans
    Polymarket markets and never infers event categories from titles.
    """

    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._last_known_good: MacroExpectationFeedResponse | None = None

    async def macro_expectation_contract(self) -> MacroExpectationFeedResponse:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                trust_env=False,
            ) as client:
                response = await client.get(
                    PLATFORM_DATA_EXPECTATIONS_URL,
                    headers={"User-Agent": self._user_agent},
                )
                response.raise_for_status()
                payload = response.json()

            if not isinstance(payload, dict):
                raise ResearchProviderError("macro_expectation_feed_invalid_payload")
            document = cast(dict[str, Any], payload)
            if str(document.get("schemaVersion") or "") != "1.0":
                raise ResearchProviderError("macro_expectation_feed_schema_mismatch")

            contract = MacroExpectationFeedResponse.model_validate(document)
            if contract.status == "ready" and not contract.events:
                raise ResearchProviderError("macro_expectation_feed_ready_without_events")
            if contract.status in {"ready", "stale"} and contract.events:
                self._last_known_good = contract.model_copy(deep=True)
            return contract
        except Exception as exc:
            if self._last_known_good is not None:
                stale = self._last_known_good.model_copy(deep=True)
                stale.status = "stale"
                return stale
            if isinstance(exc, ResearchProviderError):
                raise
            raise ResearchProviderError(
                f"macro_expectation_feed_unavailable:{type(exc).__name__}"
            ) from exc

    async def macro_expectation_events(
        self,
        limit: int = 12,
    ) -> list[MacroExpectationEvent]:
        """Compatibility adapter for the pre-Phase-1A research service."""

        contract = await self.macro_expectation_contract()
        if contract.status not in {"ready", "stale"}:
            return []

        return [
            MacroExpectationEvent(
                event_id=event.id,
                category=event.category,
                title=event.label,
                outcome="Configured outcome",
                current_probability_pct=event.probability,
                history=[
                    MacroProbabilityPoint(
                        observed_at=point.observed_at,
                        probability_pct=point.probability,
                    )
                    for point in event.history
                ],
            )
            for event in contract.events[:limit]
        ]
