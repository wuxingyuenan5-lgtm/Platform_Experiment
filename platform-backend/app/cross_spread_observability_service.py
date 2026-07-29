from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from app import cross_spread_live_read_client as runtime
from app.cross_spread import (
    BYBIT_ACCOUNT_ID,
    BYBIT_SYMBOL,
    MT5_ACCOUNT_ID,
    MT5_SYMBOL,
)
from app.cross_spread_live_read_client import CrossSpreadLiveReadError
from app.cross_spread_observability_schemas import (
    CrossSpreadObservabilityResponse,
    CrossSpreadVenueObservabilityResponse,
)

ObservabilityMode = Literal["fast", "audit"]


def get_cross_spread_observability(
    *,
    history_hours: int,
    limit: int,
    mode: ObservabilityMode = "audit",
) -> CrossSpreadObservabilityResponse:
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=history_hours)
    bybit = _venue_observability(
        venue="Bybit",
        account_id=BYBIT_ACCOUNT_ID,
        symbol=BYBIT_SYMBOL,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        mode=mode,
    )
    mt5 = _venue_observability(
        venue="MT5",
        account_id=MT5_ACCOUNT_ID,
        symbol=MT5_SYMBOL,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        mode=mode,
    )
    warnings = [*bybit.warnings, *mt5.warnings]
    if bybit.status == "complete" and mt5.status == "complete":
        status = "complete"
    elif bybit.status == "unavailable" and mt5.status == "unavailable":
        status = "unavailable"
    else:
        status = "partial"
    return CrossSpreadObservabilityResponse(
        status=status,
        historyHours=history_hours,
        bybit=bybit,
        mt5=mt5,
        warnings=warnings,
        asOf=end_time,
    )


def _venue_observability(
    *,
    venue: str,
    account_id: str,
    symbol: str,
    start_time: datetime,
    end_time: datetime,
    limit: int,
    mode: ObservabilityMode,
) -> CrossSpreadVenueObservabilityResponse:
    warnings: list[str] = []
    section_states: dict[str, str] = {}

    account_risk = _read_section(
        venue=venue,
        section="accountRisk",
        callback=lambda: runtime.get_account_risk(account_id),
        fallback=None,
        section_states=section_states,
        warnings=warnings,
    )
    positions = _read_section(
        venue=venue,
        section="positions",
        callback=lambda: runtime.list_position_rows(account_id),
        fallback=[],
        section_states=section_states,
        warnings=warnings,
    )

    active_page: dict[str, Any] = {"items": []}
    recent_page: dict[str, Any] = {"items": []}
    fill_page: dict[str, Any] = {"items": []}
    if mode == "audit":
        active_page = _read_section(
            venue=venue,
            section="activeOrders",
            callback=lambda: runtime.query_order_history(
                account_id=account_id,
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                scope="active",
            ),
            fallback={"items": []},
            section_states=section_states,
            warnings=warnings,
        )
        recent_page = _read_section(
            venue=venue,
            section="recentOrders",
            callback=lambda: runtime.query_order_history(
                account_id=account_id,
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                scope="closed",
            ),
            fallback={"items": []},
            section_states=section_states,
            warnings=warnings,
        )
        fill_page = _read_section(
            venue=venue,
            section="recentFills",
            callback=lambda: runtime.query_fill_history(
                account_id=account_id,
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            ),
            fallback={"items": []},
            section_states=section_states,
            warnings=warnings,
        )

    completed = sum(1 for state in section_states.values() if state == "complete")
    if completed == len(section_states):
        status = "complete"
    elif completed == 0:
        status = "unavailable"
    else:
        status = "partial"
    return CrossSpreadVenueObservabilityResponse(
        venue=venue,
        accountId=account_id,
        symbol=symbol,
        status=status,
        sectionStates=section_states,
        accountRisk=account_risk,
        positions=positions,
        activeOrders=_page_items(active_page),
        recentOrders=_page_items(recent_page),
        recentFills=_page_items(fill_page),
        warnings=warnings,
    )


def _read_section(
    *,
    venue: str,
    section: str,
    callback: Callable[[], Any],
    fallback: Any,
    section_states: dict[str, str],
    warnings: list[str],
) -> Any:
    try:
        value = callback()
    except CrossSpreadLiveReadError as exc:
        section_states[section] = "unavailable"
        warnings.append(f"{venue} {section}: {exc}")
        return fallback
    section_states[section] = "complete"
    return value


def _page_items(page: Any) -> list[dict[str, Any]]:
    if not isinstance(page, dict):
        return []
    items = page.get("items")
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]
