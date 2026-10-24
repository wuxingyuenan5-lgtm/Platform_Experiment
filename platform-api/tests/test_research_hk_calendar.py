from datetime import date

from app.research_hk_calendar import hk_last_session


def test_hkex_holiday_and_calendar_boundary():
    assert hk_last_session(date(2026, 10, 19)) == date(2026, 10, 16)
    assert hk_last_session(date(2026, 10, 20)) == date(2026, 10, 20)
    assert hk_last_session(date(2027, 1, 4)) is None
    assert hk_last_session(date(2026, 1, 1)) is None
