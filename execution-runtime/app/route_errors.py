from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from fastapi import HTTPException

from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayQueryUnsupportedError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)

T = TypeVar("T")


def query_gateway(callback: Callable[[], T]) -> T:
    try:
        return callback()
    except GatewayConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GatewayQueryUnsupportedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except GatewayRequestRejectedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GatewayResultUnknownError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def history_window(
    start_time: datetime | None,
    end_time: datetime | None,
) -> tuple[datetime, datetime]:
    end = as_utc(end_time or datetime.now(UTC))
    start = as_utc(start_time or end - timedelta(days=7))
    if end <= start:
        raise HTTPException(status_code=422, detail="History endTime must be after startTime")
    if end - start > timedelta(days=7):
        raise HTTPException(
            status_code=422,
            detail="History query window cannot exceed 7 days",
        )
    return start, end


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
