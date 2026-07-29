from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ResearchDataStatus = Literal["loading", "ready", "partial", "no_data", "stale", "error"]
StrictThresholdOperator = Literal[">"]


class ResearchSourceMeta(BaseModel):
    source: str = Field(min_length=1, max_length=128)
    source_timestamp: datetime | None = Field(default=None, alias="sourceTimestamp")
    fetched_at: datetime = Field(alias="fetchedAt")
    status: ResearchDataStatus
    is_stale: bool = Field(alias="isStale")
    error_code: str | None = Field(default=None, alias="errorCode", max_length=128)

    @field_validator("source_timestamp", "fetched_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("research timestamps must include a timezone")
        return value


class AShareTurnoverStock(BaseModel):
    security_code: str = Field(alias="securityCode", pattern=r"^\d{6}$")
    security_name: str = Field(alias="securityName", min_length=1, max_length=128)
    turnover_yuan: Decimal = Field(alias="turnoverYuan", ge=0)
    return_pct: Decimal | None = Field(default=None, alias="returnPct")
    net_inflow_yuan: Decimal | None = Field(default=None, alias="netInflowYuan")


class ShenwanMembership(BaseModel):
    security_code: str = Field(alias="securityCode", pattern=r"^\d{6}$")
    sw_l1_code: str = Field(alias="swL1Code", min_length=1, max_length=32)
    sw_l1_name: str = Field(alias="swL1Name", min_length=1, max_length=128)
    sw_l2_code: str = Field(alias="swL2Code", min_length=1, max_length=32)
    sw_l2_name: str = Field(alias="swL2Name", min_length=1, max_length=128)
    classification_version: str = Field(alias="classificationVersion", min_length=1, max_length=64)
    effective_from: date = Field(alias="effectiveFrom")
    effective_to: date | None = Field(default=None, alias="effectiveTo")


class ShenwanLevel2Aggregate(BaseModel):
    rank: int = Field(ge=1)
    sw_l1_code: str = Field(alias="swL1Code")
    sw_l1_name: str = Field(alias="swL1Name")
    sw_l2_code: str = Field(alias="swL2Code")
    sw_l2_name: str = Field(alias="swL2Name")
    return_pct: Decimal | None = Field(default=None, alias="returnPct")
    turnover_yuan: Decimal = Field(alias="turnoverYuan", ge=0)
    market_share_pct: Decimal = Field(alias="marketSharePct", ge=0)
    net_inflow_yuan: Decimal | None = Field(default=None, alias="netInflowYuan")


class TurnoverThresholdIndustryCount(BaseModel):
    sw_l1_code: str = Field(alias="swL1Code")
    sw_l1_name: str = Field(alias="swL1Name")
    sw_l2_code: str = Field(alias="swL2Code")
    sw_l2_name: str = Field(alias="swL2Name")
    stock_count: int = Field(alias="stockCount", ge=1)


class TurnoverThresholdStock(BaseModel):
    security_code: str = Field(alias="securityCode")
    security_name: str = Field(alias="securityName")
    sw_l1_code: str = Field(alias="swL1Code")
    sw_l1_name: str = Field(alias="swL1Name")
    sw_l2_code: str = Field(alias="swL2Code")
    sw_l2_name: str = Field(alias="swL2Name")
    turnover_yuan: Decimal = Field(alias="turnoverYuan", ge=0)
    return_pct: Decimal | None = Field(default=None, alias="returnPct")


class TurnoverThresholdResult(BaseModel):
    threshold_yuan: Decimal = Field(alias="thresholdYuan", gt=0)
    operator: StrictThresholdOperator = ">"
    industries: list[TurnoverThresholdIndustryCount]
    stocks: list[TurnoverThresholdStock]
    unmatched_security_codes: list[str] = Field(alias="unmatchedSecurityCodes")


class AShareResearchAggregation(BaseModel):
    sw2_top: list[ShenwanLevel2Aggregate] = Field(alias="sw2Top")
    threshold: TurnoverThresholdResult
    unmatched_security_codes: list[str] = Field(alias="unmatchedSecurityCodes")
