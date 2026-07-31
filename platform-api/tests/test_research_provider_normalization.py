from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.research_provider_normalization import (
    as_date,
    as_decimal,
    as_non_negative_integer,
    closest_prior_close,
    first_present,
    frame_records,
    percentage_change,
    trend_marker,
)

pytestmark = pytest.mark.unit


class _Frame:
    empty = False

    def to_dict(self, orient: str) -> list[dict[str, Any]]:
        assert orient == "records"
        return [{"代码": "600000", "成交额": "12,345"}]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12,345.60", Decimal("12345.60")),
        (0, Decimal("0")),
        (False, None),
        ("--", None),
        ("NaN", None),
        ("Infinity", None),
        ("not-a-number", None),
    ],
)
def test_as_decimal_handles_public_source_values(value: Any, expected: Decimal | None) -> None:
    assert as_decimal(value) == expected


def test_integer_date_and_record_normalization() -> None:
    assert as_non_negative_integer("9.9") == 9
    assert as_non_negative_integer("-3") == 0
    assert as_date("2026-07-31T08:00:00") == date(2026, 7, 31)
    assert as_date("invalid") is None
    assert frame_records(None) == []
    assert frame_records(_Frame()) == [{"代码": "600000", "成交额": "12,345"}]


def test_field_selection_and_market_calculations() -> None:
    row = {"primary": "", "secondary": Decimal("8")}
    assert first_present(row, "primary", "secondary") == Decimal("8")
    assert percentage_change(Decimal("110"), Decimal("100")) == Decimal("10.0")
    assert percentage_change(Decimal("110"), Decimal("0")) is None
    assert trend_marker(Decimal("100"), Decimal("100")) == "▲"
    assert trend_marker(Decimal("99"), Decimal("100")) == "▼"


def test_closest_prior_close_preserves_ordered_history_semantics() -> None:
    rows = [
        {"date": date(2026, 1, 2), "close": Decimal("10")},
        {"date": date(2026, 1, 5), "close": Decimal("12")},
    ]
    assert closest_prior_close(rows, date(2026, 1, 4)) == Decimal("10")
    assert closest_prior_close(rows, date(2025, 12, 31)) is None
