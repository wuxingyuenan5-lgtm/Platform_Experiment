from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.member_holding_repository import FundNavRecord, FundRecord, MemberHoldingRecord
from app.member_holding_valuation import HoldingValuationError, build_holding_response

CURRENT = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


def fund() -> FundRecord:
    return FundRecord(
        id="fund-1",
        name="Test Fund",
        fund_code="TEST-1",
        base_currency="USDT",
    )


def holding(*, invested: str = "0.01") -> MemberHoldingRecord:
    return MemberHoldingRecord(
        id="holding-1",
        member_user_id="member-1",
        fund_id="fund-1",
        share_quantity="0.1",
        cumulative_invested=invested,
        confirmed_at="2026-07-30T08:00:00+00:00",
        as_of="2026-07-31T08:00:00+00:00",
        source="manual_admin",
        status="active",
        row_version=3,
        updated_by="owner-1",
        created_at="2026-07-30T08:00:00+00:00",
        updated_at="2026-07-31T08:00:00+00:00",
    )


def nav(
    *,
    valuation_time: datetime = CURRENT,
    unit_nav: str = "0.2",
    currency: str = "USDT",
) -> FundNavRecord:
    return FundNavRecord(
        id="nav-1",
        fund_id="fund-1",
        valuation_time=valuation_time.isoformat(),
        unit_nav=unit_nav,
        currency=currency,
        source="manual_admin",
        status="available",
        created_at=CURRENT.isoformat(),
    )


@pytest.mark.unit
def test_available_nav_preserves_exact_decimal_response_contract() -> None:
    response = build_holding_response(
        fund=fund(),
        holding=holding(),
        nav=nav(),
        current=CURRENT,
        stale_after_hours=36,
    )

    assert response.nav_status == "available"
    assert response.share_quantity == "0.1"
    assert response.latest_unit_nav == "0.2"
    assert response.market_value == "0.02"
    assert response.cumulative_invested == "0.01"
    assert response.cumulative_return == "0.01"
    assert response.return_rate == "1"
    assert response.row_version == 3
    assert response.model_dump(by_alias=True)["memberUserId"] == "member-1"


@pytest.mark.unit
def test_missing_and_stale_nav_are_explicit_and_zero_invested_has_no_rate() -> None:
    missing = build_holding_response(
        fund=fund(),
        holding=holding(),
        nav=None,
        current=CURRENT,
        stale_after_hours=36,
    )
    assert missing.nav_status == "unavailable"
    assert missing.latest_unit_nav is None
    assert missing.market_value is None
    assert missing.cumulative_return is None
    assert missing.return_rate is None

    stale = build_holding_response(
        fund=fund(),
        holding=holding(invested="0"),
        nav=nav(valuation_time=CURRENT - timedelta(hours=48), unit_nav="1.25"),
        current=CURRENT,
        stale_after_hours=36,
    )
    assert stale.nav_status == "stale"
    assert stale.market_value == "0.125"
    assert stale.cumulative_return == "0.125"
    assert stale.return_rate is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("candidate", "expected_code"),
    [
        (nav(unit_nav="1e-3"), "fund_nav_decimal_invalid"),
        (nav(currency="CNY"), "fund_nav_currency_mismatch"),
        (nav(valuation_time=CURRENT + timedelta(minutes=6)), "fund_nav_timestamp_invalid"),
    ],
)
def test_nav_validation_preserves_error_codes(
    candidate: FundNavRecord,
    expected_code: str,
) -> None:
    with pytest.raises(HoldingValuationError) as captured:
        build_holding_response(
            fund=fund(),
            holding=holding(),
            nav=candidate,
            current=CURRENT,
            stale_after_hours=36,
        )
    assert captured.value.code == expected_code


@pytest.mark.unit
def test_holding_decimal_and_timezone_validation_preserve_error_codes() -> None:
    invalid_decimal = replace(holding(), share_quantity="1e-3")
    with pytest.raises(HoldingValuationError) as decimal_error:
        build_holding_response(
            fund=fund(),
            holding=invalid_decimal,
            nav=None,
            current=CURRENT,
            stale_after_hours=36,
        )
    assert decimal_error.value.code == "holding_decimal_invalid"

    invalid_time = replace(holding(), as_of="2026-07-31T08:00:00")
    with pytest.raises(HoldingValuationError) as timestamp_error:
        build_holding_response(
            fund=fund(),
            holding=invalid_time,
            nav=None,
            current=CURRENT,
            stale_after_hours=36,
        )
    assert timestamp_error.value.code == "invalid_timestamp"
