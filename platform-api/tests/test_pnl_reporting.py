from datetime import UTC, date, datetime

import pytest

from app.pnl_reporting import day_start, reporting_date


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        ("2026-09-30T15:59:59+00:00", "2026-09-30"),
        ("2026-09-30T16:00:00+00:00", "2026-10-01"),
        ("2026-12-31T16:00:00+00:00", "2027-01-01"),
        ("2027-01-01T00:00:00+08:00", "2027-01-01"),
    ],
)
def test_reporting_boundary_is_beijing_not_venue_clock(instant, expected):
    at = datetime.fromisoformat(instant)
    assert reporting_date(at).isoformat() == expected
    assert day_start(reporting_date(at)) <= at


def test_calendar_start_is_an_aware_utc_instant():
    assert day_start(date(2026, 10, 1)) == datetime(2026, 9, 30, 16, tzinfo=UTC)
    with pytest.raises(ValueError, match="timezone-aware"):
        reporting_date(datetime(2026, 10, 1))
