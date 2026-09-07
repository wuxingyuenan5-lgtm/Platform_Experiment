from datetime import UTC, datetime

from app.research_a_share_refresh import _scheduled_refresh_due


def test_scheduled_a_share_refresh_requires_completed_china_session() -> None:
    # 2026-09-06 is Sunday in Asia/Shanghai.
    assert _scheduled_refresh_due(datetime(2026, 9, 6, 8, tzinfo=UTC)) is False
    # Monday 15:04 Shanghai is not a completed daily close.
    assert _scheduled_refresh_due(datetime(2026, 9, 7, 7, 4, tzinfo=UTC)) is False
    # Monday 15:05 Shanghai is eligible.
    assert _scheduled_refresh_due(datetime(2026, 9, 7, 7, 5, tzinfo=UTC)) is True
