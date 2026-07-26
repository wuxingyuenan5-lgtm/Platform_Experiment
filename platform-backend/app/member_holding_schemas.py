from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

HoldingSource = Literal["manual_admin", "migration", "external_import"]
HoldingStatus = Literal["active", "closed"]
NavStatus = Literal["available", "stale", "unavailable"]


class FundSummaryResponse(BaseModel):
    fund_id: str = Field(alias="fundId")
    fund_name: str = Field(alias="fundName")
    fund_code: str | None = Field(default=None, alias="fundCode")
    base_currency: str = Field(alias="baseCurrency")


class FundListResponse(BaseModel):
    items: list[FundSummaryResponse]


class MemberHoldingResponse(BaseModel):
    holding_id: str = Field(alias="holdingId")
    member_user_id: str = Field(alias="memberUserId")
    fund_id: str = Field(alias="fundId")
    fund_name: str = Field(alias="fundName")
    fund_code: str | None = Field(default=None, alias="fundCode")
    currency: str
    share_quantity: str = Field(alias="shareQuantity")
    latest_unit_nav: str | None = Field(default=None, alias="latestUnitNav")
    market_value: str | None = Field(default=None, alias="marketValue")
    cumulative_invested: str = Field(alias="cumulativeInvested")
    cumulative_return: str | None = Field(default=None, alias="cumulativeReturn")
    return_rate: str | None = Field(default=None, alias="returnRate")
    nav_status: NavStatus = Field(alias="navStatus")
    nav_valuation_time: datetime | None = Field(default=None, alias="navValuationTime")
    confirmed_at: datetime | None = Field(default=None, alias="confirmedAt")
    as_of: datetime = Field(alias="asOf")
    source: HoldingSource
    status: HoldingStatus
    row_version: int = Field(alias="rowVersion")
    updated_at: datetime = Field(alias="updatedAt")


class MemberHoldingListResponse(BaseModel):
    items: list[MemberHoldingResponse]


class UpsertMemberHoldingRequest(BaseModel):
    share_quantity: str = Field(alias="shareQuantity", min_length=1, max_length=64)
    cumulative_invested: str = Field(alias="cumulativeInvested", min_length=1, max_length=64)
    confirmed_at: datetime | None = Field(default=None, alias="confirmedAt")
    as_of: datetime = Field(alias="asOf")
    source: HoldingSource = "manual_admin"
    status: HoldingStatus = "active"
    expected_version: int | None = Field(default=None, alias="expectedVersion", ge=1)

    @field_validator("confirmed_at", "as_of")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must include a timezone")
        return value


class UpsertFundNavRequest(BaseModel):
    unit_nav: str = Field(alias="unitNav", min_length=1, max_length=64)
    valuation_time: datetime = Field(alias="valuationTime")
    currency: str = Field(min_length=3, max_length=3)
    source: HoldingSource = "manual_admin"
    fund_code: str | None = Field(default=None, alias="fundCode", max_length=64)

    @field_validator("valuation_time")
    @classmethod
    def require_valuation_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("valuationTime must include a timezone")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        if not value.isalpha():
            raise ValueError("currency must contain three letters")
        return value.upper()

    @field_validator("fund_code")
    @classmethod
    def normalize_fund_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class FundNavMutationResponse(BaseModel):
    fund: FundSummaryResponse
    unit_nav: str = Field(alias="unitNav")
    valuation_time: datetime = Field(alias="valuationTime")
    currency: str
    source: HoldingSource
