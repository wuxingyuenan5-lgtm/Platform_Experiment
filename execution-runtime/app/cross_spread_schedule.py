"""MT5 session calendar and the Cross automatic-exit boundary guard.

The MetaTrader5 Python package exposes the current symbol permissions but does
not expose the broker's weekly session-window API.  Runtime therefore receives
the broker calendar as explicit configuration and evaluates it against the
configured MT5 server timezone.  The calendar is read-only state: it never
changes an order or attempts to connect to a venue.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SessionStatus = Literal["open", "closed", "buffer", "unknown"]

_DAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
_DAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "周一": 0,
    "tue": 1,
    "tuesday": 1,
    "周二": 1,
    "wed": 2,
    "wednesday": 2,
    "周三": 2,
    "thu": 3,
    "thursday": 3,
    "周四": 3,
    "fri": 4,
    "friday": 4,
    "周五": 4,
    "sat": 5,
    "saturday": 5,
    "周六": 5,
    "sun": 6,
    "sunday": 6,
    "周日": 6,
}


class _BybitMt5Timezone(tzinfo):
    """Bybit MT5 server clock: UTC+2, with Bybit's published DST dates.

    Bybit's server calendar uses the second Sunday in March through the first
    Sunday in November, which differs from the Europe/Athens transition dates
    in some years.  Keeping this as a named tzinfo prevents a fixed offset from
    being accidentally applied across the transition weeks.
    """

    key = "Bybit/MT5"

    @staticmethod
    def _nth_sunday(year: int, month: int, nth: int) -> date:
        first_weekday, days_in_month = monthrange(year, month)
        # Python weekday: Monday=0, Sunday=6.
        first_sunday = 1 + ((6 - first_weekday) % 7)
        day = first_sunday + (nth - 1) * 7
        if day > days_in_month:
            raise ValueError("invalid Sunday rule")
        return date(year, month, day)

    @classmethod
    def _transitions_utc(cls, year: int) -> tuple[datetime, datetime]:
        start_day = cls._nth_sunday(year, 3, 2)
        end_day = cls._nth_sunday(year, 11, 1)
        # Bybit publishes both transitions at 02:00 UTC.
        return (
            datetime.combine(start_day, time(2), tzinfo=UTC),
            datetime.combine(end_day, time(2), tzinfo=UTC),
        )

    @classmethod
    def _is_dst_utc(cls, value: datetime) -> bool:
        start, end = cls._transitions_utc(value.year)
        return start <= value < end

    def fromutc(self, value: datetime) -> datetime:
        if value.tzinfo is not self:
            raise ValueError("fromutc: dt.tzinfo is not self")
        utc_value = value.replace(tzinfo=UTC)
        is_dst = self._is_dst_utc(utc_value)
        offset = timedelta(hours=3 if is_dst else 2)
        local_value = utc_value + offset
        _, end = self._transitions_utc(utc_value.year)
        # Mark the standard-time occurrence of the repeated 04:00-05:00 local
        # hour so utcoffset() can distinguish it from the daylight occurrence.
        fold = 1 if not is_dst and end <= utc_value < end + timedelta(hours=1) else 0
        return local_value.replace(tzinfo=self, fold=fold)

    def utcoffset(self, value: datetime | None) -> timedelta:
        if value is None:
            return timedelta(hours=2)
        local = value.replace(tzinfo=None)
        start_day = self._nth_sunday(local.year, 3, 2)
        end_day = self._nth_sunday(local.year, 11, 1)
        if start_day < local.date() < end_day:
            return timedelta(hours=3)
        if local.date() == start_day:
            # 04:00-05:00 local is the forward-jump gap. Treat its default
            # fold as standard time and fold=1 as daylight time.
            if local.time() >= time(5) or (
                local.time() >= time(4) and getattr(value, "fold", 0) == 1
            ):
                return timedelta(hours=3)
        elif local.date() == end_day:
            # 04:00-05:00 local is repeated when the clock moves back.
            if local.time() < time(4) or (
                local.time() < time(5) and getattr(value, "fold", 0) == 0
            ):
                return timedelta(hours=3)
        return timedelta(hours=2)

    def dst(self, value: datetime | None) -> timedelta:
        return self.utcoffset(value) - timedelta(hours=2)

    def tzname(self, value: datetime | None) -> str:
        return "Bybit MT5"


_BYBIT_MT5_TIMEZONE = _BybitMt5Timezone()


def _resolve_timezone(value: str) -> tzinfo:
    normalized = value.strip()
    if normalized.lower() in {"bybit/mt5", "bybit-mt5", "bybit_mt5"}:
        return _BYBIT_MT5_TIMEZONE
    return ZoneInfo(normalized)


@dataclass(frozen=True)
class Mt5SessionState:
    status: SessionStatus
    trading_hours: str | None
    timezone: str
    automatic_exit_allowed: bool
    automatic_exit_block_reason: str | None
    guard_minutes: int

    @property
    def manual_execution_allowed(self) -> bool:
        # Manual commands remain available during the pre/post boundary guard,
        # as requested.  A fully closed or unknown session remains fail-closed.
        return self.status in {"open", "buffer"}


def _parse_clock(value: str, *, allow_24: bool = False) -> int:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("clock must be HH:MM")
    hour, minute = (int(part) for part in parts)
    if minute < 0 or minute > 59:
        raise ValueError("minute is outside 00..59")
    if hour == 24 and allow_24 and minute == 0:
        return 1440
    if hour < 0 or hour > 23:
        raise ValueError("hour is outside 00..23")
    return hour * 60 + minute


def _parse_windows(windows_raw: str) -> tuple[tuple[int, int], ...]:
    if windows_raw.strip().lower() in {"closed", "none", "off"}:
        return ()
    windows: list[tuple[int, int]] = []
    for window_raw in windows_raw.split("|"):
        if "-" not in window_raw:
            raise ValueError("session window must contain '-'")
        start_raw, end_raw = window_raw.split("-", 1)
        start = _parse_clock(start_raw)
        end = _parse_clock(end_raw, allow_24=True)
        if start == end:
            raise ValueError("session window cannot have equal start/end")
        windows.append((start, end))
    return tuple(windows)


@lru_cache(maxsize=32)
def parse_trading_schedule(schedule: str) -> dict[int, tuple[tuple[int, int], ...]]:
    """Parse ``mon=00:00-23:00;...`` into weekday minute intervals."""

    parsed: dict[int, list[tuple[int, int]]] = {}
    for entry in schedule.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError("schedule entry must contain '='")
        day_raw, windows_raw = entry.split("=", 1)
        day = _DAY_ALIASES.get(day_raw.strip().lower())
        if day is None:
            raise ValueError(f"unknown weekday: {day_raw}")
        parsed[day] = list(_parse_windows(windows_raw))
    return {day: tuple(windows) for day, windows in parsed.items()}


@lru_cache(maxsize=32)
def parse_session_overrides(overrides: str) -> dict[date, tuple[tuple[int, int], ...]]:
    parsed: dict[date, tuple[tuple[int, int], ...]] = {}
    for entry in overrides.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError("session override must contain '='")
        date_raw, windows_raw = entry.split("=", 1)
        parsed[date.fromisoformat(date_raw.strip())] = _parse_windows(windows_raw)
    return parsed


def _format_clock(minutes: int) -> str:
    if minutes == 1440:
        return "24:00"
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _format_timezone_label(timezone: str) -> str:
    try:
        zone = _resolve_timezone(timezone)
    except ZoneInfoNotFoundError:
        return timezone
    offsets = {
        datetime(year, month, 1, tzinfo=UTC).astimezone(zone).utcoffset()
        for year in (2026, 2027)
        for month in (1, 7)
    }
    labels = []
    for offset in sorted(offsets, key=lambda value: value.total_seconds() if value else 0):
        if offset is None:
            continue
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        absolute = abs(total_minutes)
        labels.append(f"UTC{sign}{absolute // 60:02d}:{absolute % 60:02d}")
    if not labels:
        return timezone
    return f"{timezone}，{'/'.join(labels)}"


def _format_day_group(days: list[int]) -> str:
    if len(days) == 1:
        return _DAY_NAMES[days[0]]
    contiguous = all(
        right == left + 1 for left, right in zip(days, days[1:], strict=False)
    )
    if contiguous:
        return f"{_DAY_NAMES[days[0]]}至{_DAY_NAMES[days[-1]]}"
    return "、".join(_DAY_NAMES[day] for day in days)


def format_trading_schedule(schedule: str, timezone: str) -> str:
    """Return a compact user-facing schedule while retaining configured times."""

    parsed = parse_trading_schedule(schedule)
    groups: list[str] = []
    by_windows: dict[tuple[tuple[int, int], ...], list[int]] = {}
    for day in range(7):
        by_windows.setdefault(parsed.get(day, ()), []).append(day)
    for windows, days in by_windows.items():
        if not windows:
            continue
        window_text = "、".join(
            f"{_format_clock(start)}-{_format_clock(end)}" for start, end in windows
        )
        groups.append(f"{_format_day_group(days)} {window_text}")
    if not groups:
        return f"未配置（{_format_timezone_label(timezone)}）"
    return f"{'；'.join(groups)}（{_format_timezone_label(timezone)}）"


def _session_boundaries(
    parsed: dict[int, tuple[tuple[int, int], ...]],
    local_date: date,
    overrides: dict[date, tuple[tuple[int, int], ...]],
) -> list[tuple[datetime, datetime]]:
    boundaries: list[tuple[datetime, datetime]] = []
    for day_offset in range(-2, 3):
        current_date = local_date + timedelta(days=day_offset)
        windows = overrides.get(current_date, parsed.get(current_date.weekday(), ()))
        for start_minutes, end_minutes in windows:
            start = datetime.combine(
                current_date,
                time(start_minutes // 60, start_minutes % 60),
            )
            end_date = current_date
            if end_minutes <= start_minutes:
                end_date += timedelta(days=1)
            if end_minutes == 1440:
                end = datetime.combine(end_date + timedelta(days=1), time.min)
            else:
                end = datetime.combine(
                    end_date,
                    time(end_minutes // 60, end_minutes % 60),
                )
            # The timezone is attached by the caller after construction.  This
            # keeps the parser independent from zoneinfo implementation details.
            boundaries.append((start, end))
    return boundaries


def resolve_mt5_session_state(
    *,
    schedule: str,
    timezone: str,
    guard_minutes: int,
    overrides: str = "",
    now: datetime | None = None,
) -> Mt5SessionState:
    """Evaluate the configured MT5 session and automatic-exit guard."""

    normalized_guard = max(0, int(guard_minutes))
    try:
        parsed = parse_trading_schedule(schedule)
        date_overrides = parse_session_overrides(overrides)
        zone = _resolve_timezone(timezone)
    except (ValueError, ZoneInfoNotFoundError):
        return Mt5SessionState(
            status="unknown",
            trading_hours=None,
            timezone=timezone,
            automatic_exit_allowed=False,
            automatic_exit_block_reason="mt5_session_state_unknown",
            guard_minutes=normalized_guard,
        )

    now_utc = now or datetime.now(UTC)
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        now_utc = now_utc.replace(tzinfo=UTC)
    local_now = now_utc.astimezone(zone)
    # Build local datetimes with the server timezone so DST transitions are
    # evaluated by the timezone database rather than a fixed offset.
    intervals: list[tuple[datetime, datetime]] = []
    for start, end in _session_boundaries(parsed, local_now.date(), date_overrides):
        intervals.append((start.replace(tzinfo=zone), end.replace(tzinfo=zone)))

    guard = timedelta(minutes=normalized_guard)
    in_boundary_guard = any(
        abs((local_now - boundary).total_seconds()) <= guard.total_seconds()
        for start, end in intervals
        for boundary in (start, end)
    )
    in_session = any(start <= local_now < end for start, end in intervals)
    if in_boundary_guard:
        status: SessionStatus = "buffer"
        auto_allowed = False
        reason = "mt5_session_boundary_guard"
    elif in_session:
        status = "open"
        auto_allowed = True
        reason = None
    else:
        status = "closed"
        auto_allowed = False
        reason = "mt5_market_closed"
    return Mt5SessionState(
        status=status,
        trading_hours=format_trading_schedule(schedule, timezone),
        timezone=timezone,
        automatic_exit_allowed=auto_allowed,
        automatic_exit_block_reason=reason,
        guard_minutes=normalized_guard,
    )
