from datetime import UTC, datetime

from app.cross_spread_schedule import (
    _resolve_timezone,
    format_trading_schedule,
    resolve_mt5_session_state,
)

SCHEDULE = (
    "mon=00:00-23:00;tue=00:00-23:00;wed=00:00-23:00;"
    "thu=00:00-23:00;fri=00:00-23:00"
)


def test_mt5_session_is_open_outside_boundary_guard():
    state = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Europe/Athens",
        guard_minutes=15,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )

    assert state.status == "open"
    assert state.automatic_exit_allowed is True
    assert state.manual_execution_allowed is True


def test_mt5_session_boundary_blocks_automatic_exit_but_keeps_manual_execution():
    # 20:50 UTC is 23:50 server time during September DST: 10 minutes before
    # the configured 00:00 session boundary.
    state = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Europe/Athens",
        guard_minutes=15,
        now=datetime(2026, 9, 15, 20, 50, tzinfo=UTC),
    )

    assert state.status == "buffer"
    assert state.automatic_exit_allowed is False
    assert state.automatic_exit_block_reason == "mt5_session_boundary_guard"
    assert state.manual_execution_allowed is True


def test_mt5_weekend_is_closed_and_fail_closed():
    state = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Europe/Athens",
        guard_minutes=15,
        now=datetime(2026, 9, 19, 10, 0, tzinfo=UTC),
    )

    assert state.status == "closed"
    assert state.automatic_exit_allowed is False
    assert state.automatic_exit_block_reason == "mt5_market_closed"
    assert state.manual_execution_allowed is False


def test_guard_minutes_are_configurable_and_schedule_is_rendered():
    state = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Europe/Athens",
        guard_minutes=3,
        now=datetime(2026, 9, 15, 20, 56, tzinfo=UTC),
    )

    assert state.status == "closed"
    assert state.guard_minutes == 3
    assert "周一至周五" in format_trading_schedule(SCHEDULE, "Europe/Athens")


def test_invalid_schedule_is_unknown_and_fail_closed():
    state = resolve_mt5_session_state(
        schedule="bad=hours",
        timezone="Europe/Athens",
        guard_minutes=15,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )

    assert state.status == "unknown"
    assert state.automatic_exit_allowed is False
    assert state.manual_execution_allowed is False


def test_date_override_can_close_a_weekday_for_holiday_or_maintenance():
    state = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Europe/Athens",
        guard_minutes=15,
        overrides="2026-09-15=closed",
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )

    assert state.status == "closed"
    assert state.automatic_exit_block_reason == "mt5_market_closed"


def test_bybit_mt5_timezone_uses_published_dst_transition_dates():
    # Bybit switches at the second Sunday in March and first Sunday in
    # November. Europe/Athens would switch on different dates in 2026.
    zone = _resolve_timezone("Bybit/MT5")

    def offset_hours(value: datetime) -> int:
        offset = value.astimezone(zone).utcoffset()
        assert offset is not None
        return int(offset.total_seconds() // 3600)

    before_spring = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Bybit/MT5",
        guard_minutes=15,
        now=datetime(2026, 3, 8, 1, 59, tzinfo=UTC),
    )
    after_spring = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Bybit/MT5",
        guard_minutes=15,
        now=datetime(2026, 3, 8, 2, 1, tzinfo=UTC),
    )
    before_autumn = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Bybit/MT5",
        guard_minutes=15,
        now=datetime(2026, 11, 1, 1, 59, tzinfo=UTC),
    )
    after_autumn = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Bybit/MT5",
        guard_minutes=15,
        now=datetime(2026, 11, 1, 2, 1, tzinfo=UTC),
    )

    assert "UTC+02:00/UTC+03:00" in before_spring.trading_hours
    assert before_spring.timezone == "Bybit/MT5"
    assert offset_hours(datetime(2026, 3, 8, 1, 59, tzinfo=UTC)) == 2
    assert offset_hours(datetime(2026, 3, 8, 2, 1, tzinfo=UTC)) == 3
    assert offset_hours(datetime(2026, 11, 1, 1, 59, tzinfo=UTC)) == 3
    assert offset_hours(datetime(2026, 11, 1, 2, 1, tzinfo=UTC)) == 2
    # Both transition dates are Sundays, so the weekly calendar is closed;
    # the assertions above validate the offset itself independently.
    assert after_spring.status == "closed"
    assert before_autumn.status == "closed"
    assert after_autumn.status == "closed"


def test_bybit_mt5_daily_break_maps_to_beijing_summer_and_winter_time():
    summer = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Bybit/MT5",
        guard_minutes=15,
        now=datetime(2026, 9, 15, 20, 50, tzinfo=UTC),
    )
    winter = resolve_mt5_session_state(
        schedule=SCHEDULE,
        timezone="Bybit/MT5",
        guard_minutes=15,
        now=datetime(2026, 1, 13, 21, 50, tzinfo=UTC),
    )

    assert summer.status == "buffer"  # 04:50 Beijing / 23:50 server UTC+3
    assert winter.status == "buffer"  # 05:50 Beijing / 23:50 server UTC+2
