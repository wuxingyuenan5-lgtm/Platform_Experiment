from __future__ import annotations

from decimal import Decimal

import pytest

from app.member_holding_decimal import (
    HoldingDecimalError,
    calculate_holding,
    canonical_decimal,
    parse_non_negative_decimal,
)


@pytest.mark.unit
def test_plain_decimal_parser_and_canonical_form() -> None:
    assert parse_non_negative_decimal("0", field="value") == Decimal("0")
    assert parse_non_negative_decimal("000.1000", field="value") == Decimal("0.1000")
    assert canonical_decimal(Decimal("000.1000")) == "0.1"
    assert canonical_decimal(Decimal("100.000")) == "100"
    assert canonical_decimal(Decimal("-0")) == "0"


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "",
        "-1",
        "+1",
        ".1",
        "1.",
        "1e-3",
        "NaN",
        "Infinity",
        " 1",
        "1 ",
        "1,000",
    ],
)
def test_decimal_parser_rejects_ambiguous_or_non_finite_values(value: str) -> None:
    with pytest.raises(HoldingDecimalError):
        parse_non_negative_decimal(value, field="value")


@pytest.mark.unit
def test_binary_float_trap_vector_is_exact() -> None:
    calculation = calculate_holding(
        share_quantity=Decimal("0.1"),
        cumulative_invested=Decimal("0.01"),
        unit_nav=Decimal("0.2"),
    )
    assert canonical_decimal(calculation.market_value) == "0.02"
    assert canonical_decimal(calculation.cumulative_return) == "0.01"
    assert canonical_decimal(calculation.return_rate) == "1"


@pytest.mark.unit
def test_missing_nav_and_zero_investment_have_null_semantics() -> None:
    unavailable = calculate_holding(
        share_quantity=Decimal("12.5"),
        cumulative_invested=Decimal("100"),
        unit_nav=None,
    )
    assert unavailable.market_value is None
    assert unavailable.cumulative_return is None
    assert unavailable.return_rate is None

    zero_investment = calculate_holding(
        share_quantity=Decimal("10"),
        cumulative_invested=Decimal("0"),
        unit_nav=Decimal("1.25"),
    )
    assert canonical_decimal(zero_investment.market_value) == "12.5"
    assert canonical_decimal(zero_investment.cumulative_return) == "12.5"
    assert zero_investment.return_rate is None


@pytest.mark.unit
def test_high_precision_vector_does_not_round_at_authority_boundary() -> None:
    calculation = calculate_holding(
        share_quantity=Decimal("123456789.123456789123456789"),
        cumulative_invested=Decimal("100000000.000000000000000001"),
        unit_nav=Decimal("1.234567891234567891"),
    )
    assert calculation.market_value == (
        Decimal("123456789.123456789123456789")
        * Decimal("1.234567891234567891")
    )
    assert calculation.cumulative_return == (
        calculation.market_value - Decimal("100000000.000000000000000001")
    )
