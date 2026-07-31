from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


def as_decimal(value: Any) -> Decimal | None:
    if value is None or value is False:
        return None
    text = str(value).replace(",", "").strip()
    if text in {"", "-", "--", "None", "nan", "NaN"}:
        return None
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not result.is_finite():
        return None
    return result


def as_non_negative_integer(value: Any) -> int:
    number = as_decimal(value)
    return max(0, int(number or 0))


def as_date(value: Any) -> date | None:
    if value in (None, "", "-"):
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def frame_records(frame: Any) -> list[dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return []
    return [dict(row) for row in frame.to_dict("records")]


def first_present(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def percentage_change(current: Decimal | None, previous: Decimal | None) -> Decimal | None:
    if current is None or previous is None or previous == 0:
        return None
    return ((current / previous) - Decimal("1")) * Decimal("100")


def trend_marker(current: Decimal | None, previous: Decimal | None) -> str | None:
    if current is None or previous is None:
        return None
    return "▲" if current >= previous else "▼"


def closest_prior_close(rows: list[dict[str, Any]], target: date) -> Decimal | None:
    candidates = [row for row in rows if row["date"] <= target]
    if not candidates:
        return None
    return candidates[-1]["close"]
