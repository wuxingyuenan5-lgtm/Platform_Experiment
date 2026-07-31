from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol, cast

from app.member_holding_decimal import (
    HoldingDecimalError,
    calculate_holding,
    canonical_decimal,
    parse_non_negative_decimal,
)
from app.member_holding_schemas import (
    HoldingSource,
    HoldingStatus,
    MemberHoldingResponse,
    NavStatus,
)


class FundValuationRecord(Protocol):
    id: str
    name: str
    fund_code: str | None
    base_currency: str


class HoldingValuationRecord(Protocol):
    id: str
    member_user_id: str
    fund_id: str
    share_quantity: str
    cumulative_invested: str
    confirmed_at: str | None
    as_of: str
    source: str
    status: str
    row_version: int
    updated_at: str


class NavValuationRecord(Protocol):
    unit_nav: str
    valuation_time: str
    currency: str


class HoldingValuationError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _parse_aware(value: str, *, field: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise HoldingValuationError("invalid_timestamp", f"{field} lacks timezone")
    return parsed.astimezone(UTC)


def build_holding_response(
    *,
    fund: FundValuationRecord,
    holding: HoldingValuationRecord,
    nav: NavValuationRecord | None,
    current: datetime,
    stale_after_hours: int,
) -> MemberHoldingResponse:
    try:
        share_quantity = parse_non_negative_decimal(
            holding.share_quantity,
            field="shareQuantity",
        )
        cumulative_invested = parse_non_negative_decimal(
            holding.cumulative_invested,
            field="cumulativeInvested",
        )
    except HoldingDecimalError as exc:
        raise HoldingValuationError("holding_decimal_invalid", str(exc)) from exc

    unit_nav = None
    nav_status: NavStatus = "unavailable"
    nav_valuation_time = None
    currency = fund.base_currency
    if nav is not None:
        try:
            unit_nav = parse_non_negative_decimal(nav.unit_nav, field="unitNav")
        except HoldingDecimalError as exc:
            raise HoldingValuationError("fund_nav_decimal_invalid", str(exc)) from exc
        nav_valuation_time = _parse_aware(nav.valuation_time, field="valuationTime")
        if nav_valuation_time > current + timedelta(minutes=5):
            raise HoldingValuationError(
                "fund_nav_timestamp_invalid",
                "Fund NAV valuation time is unexpectedly in the future",
            )
        if nav.currency != fund.base_currency:
            raise HoldingValuationError(
                "fund_nav_currency_mismatch",
                "Fund NAV currency does not match fund base currency",
            )
        stale_after = timedelta(hours=stale_after_hours)
        nav_status = "stale" if current - nav_valuation_time > stale_after else "available"
        currency = nav.currency

    calculation = calculate_holding(
        share_quantity=share_quantity,
        cumulative_invested=cumulative_invested,
        unit_nav=unit_nav,
    )
    return MemberHoldingResponse(
        holdingId=holding.id,
        memberUserId=holding.member_user_id,
        fundId=fund.id,
        fundName=fund.name,
        fundCode=fund.fund_code,
        currency=currency,
        shareQuantity=canonical_decimal(share_quantity),
        latestUnitNav=canonical_decimal(unit_nav) if unit_nav is not None else None,
        marketValue=(
            canonical_decimal(calculation.market_value)
            if calculation.market_value is not None
            else None
        ),
        cumulativeInvested=canonical_decimal(cumulative_invested),
        cumulativeReturn=(
            canonical_decimal(calculation.cumulative_return)
            if calculation.cumulative_return is not None
            else None
        ),
        returnRate=(
            canonical_decimal(calculation.return_rate)
            if calculation.return_rate is not None
            else None
        ),
        navStatus=nav_status,
        navValuationTime=nav_valuation_time,
        confirmedAt=(
            _parse_aware(holding.confirmed_at, field="confirmedAt")
            if holding.confirmed_at is not None
            else None
        ),
        asOf=_parse_aware(holding.as_of, field="asOf"),
        source=cast(HoldingSource, holding.source),
        status=cast(HoldingStatus, holding.status),
        rowVersion=holding.row_version,
        updatedAt=_parse_aware(holding.updated_at, field="updatedAt"),
    )
