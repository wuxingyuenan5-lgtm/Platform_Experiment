"""Beijing calendar boundaries for reporting, not venue clocks or trading sessions."""

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

REPORTING_ZONE = ZoneInfo("Asia/Shanghai")


def reporting_date(value: datetime) -> date:
    if value.tzinfo is None:
        raise ValueError("PnL reporting requires timezone-aware timestamps")
    return value.astimezone(REPORTING_ZONE).date()


def day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, REPORTING_ZONE).astimezone(UTC)
