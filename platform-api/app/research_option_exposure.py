from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.research_data_schemas import ResearchApiModel


class OptionExposureLeg(ResearchApiModel):
    symbol: str
    expiry: datetime
    strike: Decimal = Field(gt=0, allow_inf_nan=False)
    side: Literal["call", "put"]
    open_interest: Decimal = Field(ge=0, allow_inf_nan=False)
    gamma: Decimal = Field(ge=0, allow_inf_nan=False)
    underlying_price: Decimal = Field(gt=0, allow_inf_nan=False)
    multiplier: Decimal = Field(gt=0, allow_inf_nan=False)
    exposure_usd: Decimal = Field(ge=0, allow_inf_nan=False)
    input_as_of: datetime | None = None
    mark_iv: Decimal | None = None

    @field_validator("expiry", "input_as_of")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("option timestamps require timezone")
        return value


class OptionExposureSnapshot(ResearchApiModel):
    market: Literal["deribit", "ibit"]
    status: Literal["ready", "partial", "stale", "degraded"]
    source: str
    source_url: str
    collected_at: datetime
    as_of: datetime | None = None
    underlying_last_trade_at: datetime | None = None
    underlying_price: Decimal = Field(gt=0, allow_inf_nan=False)
    model: Literal["black76_forward_gamma", "cboe_published_gamma"]
    oi_unit: Literal["BTC", "contracts"]
    total_contracts: int = Field(gt=0)
    excluded_contracts: int = Field(ge=0)
    total_open_interest: Decimal = Field(gt=0, allow_inf_nan=False)
    included_open_interest: Decimal = Field(ge=0, allow_inf_nan=False)
    quality_flags: list[str] = Field(default_factory=list)
    legs: list[OptionExposureLeg] = Field(min_length=1)

    @field_validator("collected_at", "as_of", "underlying_last_trade_at")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("snapshot timestamps require timezone")
        return value

    @model_validator(mode="after")
    def reconcile(self):
        if len(self.legs) + self.excluded_contracts != self.total_contracts or len(
            {x.symbol for x in self.legs}
        ) != len(self.legs):
            raise ValueError("option coverage inconsistent")
        if (
            sum(x.open_interest for x in self.legs) != self.included_open_interest
            or self.included_open_interest > self.total_open_interest
        ):
            raise ValueError("option OI inconsistent")
        return self

    def apply_freshness(self, now: datetime):
        # Scheduled research snapshots: six-hour collection plus one hour grace.
        # This is freshness of the saved snapshot, not a real-time quote promise.
        limit = 7 * 3600 if self.market == "deribit" else 86400
        if (now - (self.as_of or self.collected_at)).total_seconds() > limit:
            self.status = "stale"
            if "snapshot_refresh_due" not in self.quality_flags:
                self.quality_flags.append("snapshot_refresh_due")
