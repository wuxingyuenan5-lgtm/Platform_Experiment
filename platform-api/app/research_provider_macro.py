from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.research_data_schemas import (
    MacroExpectationEvent,
    MacroProbabilityPoint,
    ResearchApiModel,
)
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

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
    original_label: str | None = Field(default=None, max_length=512)
    category: MacroCategory
    probability: float = Field(ge=0, le=100)
    source_url: str | None = Field(default=None, max_length=512)
    expiry_at: datetime | None = None
    history: list[MacroExpectationFeedPoint] = Field(default_factory=list)


class FomcOutcome(ResearchApiModel):
    id: str
    label: str
    probability: float = Field(ge=0, le=100)
    history: list[MacroExpectationFeedPoint] = Field(default_factory=list)


class FomcMeeting(ResearchApiModel):
    id: str
    slug: str
    label: str
    meeting_date: str
    expiry_at: datetime
    updated_at: datetime
    closed: bool
    status: str
    source_url: str
    outcomes: list[FomcOutcome]


class MacroExpectationFeedResponse(ResearchApiModel):
    status: MacroExpectationFeedStatus
    source: str = Field(min_length=1, max_length=256)
    updated_at: datetime
    source_url: str | None = Field(default=None, max_length=512)
    events: list[MacroExpectationFeedEvent] = Field(default_factory=list)
    fomc_status: MacroExpectationFeedStatus = "not_configured"
    fomc_meetings: list[FomcMeeting] = Field(default_factory=list)

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

    def _with_fomc(self, contract: MacroExpectationFeedResponse) -> MacroExpectationFeedResponse:
        try:
            document = read_local_json("public/v1/macro/fomc-meetings.json")
            contract.fomc_meetings = [FomcMeeting.model_validate(item) for item in document.get("meetings", [])]
            contract.fomc_status = document.get("status", "not_configured")
        except ResearchProviderError:
            contract.fomc_status = "not_configured"
        except (ValueError, TypeError):
            contract.fomc_status = "error"
        return contract

    async def macro_expectation_contract(self) -> MacroExpectationFeedResponse:
        try:
            document = read_local_json("public/v1/macro/expectations.json")
            if str(document.get("schemaVersion") or "") != "1.0":
                raise ResearchProviderError("macro_expectation_feed_schema_mismatch")

            contract = MacroExpectationFeedResponse.model_validate(document)
            if contract.status == "ready" and not contract.events:
                raise ResearchProviderError("macro_expectation_feed_ready_without_events")
            if contract.status in {"ready", "stale"} and contract.events:
                self._last_known_good = contract.model_copy(deep=True)
            return self._with_fomc(contract)
        except Exception as exc:
            if self._last_known_good is not None:
                stale = self._last_known_good.model_copy(deep=True)
                stale.status = "stale"
                return self._with_fomc(stale)
            if isinstance(exc, ResearchProviderError) and str(exc).startswith(
                "local_data_not_found:"
            ):
                return self._with_fomc(MacroExpectationFeedResponse(
                    status="not_configured",
                    source="local macro expectation feed",
                    updated_at=datetime.now(UTC),
                    source_url="https://polymarket.com/markets",
                    events=[],
                ))
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
                current_probability_pct=Decimal(str(event.probability)),
                history=[
                    MacroProbabilityPoint(
                        observed_at=point.observed_at,
                        probability_pct=Decimal(str(point.probability)),
                    )
                    for point in event.history
                ],
            )
            for event in contract.events[:limit]
        ]
