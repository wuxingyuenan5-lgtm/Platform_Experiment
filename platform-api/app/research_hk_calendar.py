"""Bounded HKEX securities calendar; unknown years never imply a session.

Source: HKEX ce_SEHK_CT_075_2025.pdf (2026 securities-market holidays).
Weekend closures are additional to these published weekday holidays.
"""

from datetime import date, timedelta

_HOLIDAYS_2026 = {
    "2026-01-01",
    "2026-02-17",
    "2026-02-18",
    "2026-02-19",
    "2026-04-03",
    "2026-04-06",
    "2026-04-07",
    "2026-05-01",
    "2026-05-25",
    "2026-06-19",
    "2026-07-01",
    "2026-10-01",
    "2026-10-19",
    "2026-12-25",
}


def hk_last_session(day: date) -> date | None:
    if day.year != 2026:
        return None
    while day.weekday() >= 5 or day.isoformat() in _HOLIDAYS_2026:
        day -= timedelta(days=1)
    return day if day.year == 2026 else None
