from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import httpx

from app.config import get_settings


class CrossSpreadLiveReadError(RuntimeError):
    """Raised when authoritative live venue evidence is unavailable or invalid."""


_RUNTIME_CLIENT = httpx.Client(trust_env=False)


@dataclass(frozen=True)
class LiveInstrumentSpecification:
    source: str
    account_id: str
    instrument_id: str
    symbol: str
    status: str
    min_quantity: Decimal
    quantity_step: Decimal
    max_market_quantity: Decimal | None
    contract_size: Decimal
    trade_mode: str
    filling_mode: str
    access_checks: dict[str, object]


@dataclass(frozen=True)
class LivePosition:
    source: str
    external_position_id: str
    account_id: str
    instrument_id: str
    symbol: str
    net_quantity: Decimal


def runtime_get(path: str, params: dict[str, str] | None = None) -> object:
    settings = get_settings()
    try:
        response = _RUNTIME_CLIENT.get(
            f"{settings.runtime_base_url}{path}",
            params=params,
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = _response_detail(exc.response)
        raise CrossSpreadLiveReadError(
            f"Execution Runtime rejected live read {path}: {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise CrossSpreadLiveReadError(
            f"Execution Runtime live read is unavailable: {path}"
        ) from exc
    return response.json()


def get_instrument_specification(
    *,
    account_id: str,
    symbol: str,
) -> LiveInstrumentSpecification:
    payload = runtime_get(
        f"/venue/instruments/{symbol}",
        params={"accountId": account_id},
    )
    if not isinstance(payload, dict):
        raise CrossSpreadLiveReadError("Runtime instrument specification is malformed")
    try:
        maximum = payload.get("maxMarketQuantity")
        access_checks = payload.get("accessChecks") or {}
        if not isinstance(access_checks, dict):
            raise TypeError("accessChecks must be an object")
        specification = LiveInstrumentSpecification(
            source=str(payload["source"]),
            account_id=str(payload["accountId"]),
            instrument_id=str(payload["instrumentId"]),
            symbol=str(payload["symbol"]).upper(),
            status=str(payload["status"]),
            min_quantity=Decimal(str(payload["minQuantity"])),
            quantity_step=Decimal(str(payload["quantityStep"])),
            max_market_quantity=Decimal(str(maximum)) if maximum is not None else None,
            contract_size=Decimal(str(payload["contractSize"])),
            trade_mode=str(payload["trade_mode"]),
            filling_mode=str(payload["filling_mode"]),
            access_checks=dict(access_checks),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CrossSpreadLiveReadError("Runtime instrument specification is incomplete") from exc
    if specification.min_quantity <= 0 or specification.quantity_step <= 0:
        raise CrossSpreadLiveReadError("Runtime instrument quantity specification is invalid")
    if specification.contract_size <= 0:
        raise CrossSpreadLiveReadError("Runtime instrument contract size is invalid")
    return specification


def list_positions(account_id: str) -> list[LivePosition]:
    rows = list_position_rows(account_id)
    positions: list[LivePosition] = []
    for row in rows:
        try:
            positions.append(
                LivePosition(
                    source=str(row["source"]),
                    external_position_id=str(row["externalPositionId"]),
                    account_id=str(row["accountId"]),
                    instrument_id=str(row["instrumentId"]),
                    symbol=str(row["symbol"]).upper(),
                    net_quantity=Decimal(str(row["netQuantity"])),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CrossSpreadLiveReadError("Runtime position row is incomplete") from exc
    return positions


def list_position_rows(account_id: str) -> list[dict[str, object]]:
    payload = runtime_get("/venue/positions", params={"accountId": account_id})
    return _object_list(payload, "Runtime position response")


def get_account_risk(account_id: str) -> dict[str, object]:
    payload = runtime_get("/venue/account-risk", params={"accountId": account_id})
    if not isinstance(payload, dict):
        raise CrossSpreadLiveReadError("Runtime account-risk response is malformed")
    return dict(payload)


def list_orders(
    *,
    account_id: str,
    symbol: str | None = None,
    limit: int = 50,
) -> list[dict[str, object]]:
    params = {"accountId": account_id, "limit": str(limit)}
    if symbol is not None:
        params["symbol"] = symbol
    payload = runtime_get("/venue/orders", params=params)
    return _object_list(payload, "Runtime order-list response")


def query_order_history(
    *,
    account_id: str,
    symbol: str | None,
    start_time: datetime,
    end_time: datetime,
    limit: int,
    scope: str,
    cursor: str | None = None,
) -> dict[str, object]:
    params = {
        "accountId": account_id,
        "startTime": start_time.isoformat(),
        "endTime": end_time.isoformat(),
        "limit": str(limit),
        "scope": scope,
    }
    if symbol is not None:
        params["symbol"] = symbol
    if cursor is not None:
        params["cursor"] = cursor
    payload = runtime_get("/venue/order-history", params=params)
    return _history_page(payload, "Runtime order-history response")


def query_fill_history(
    *,
    account_id: str,
    symbol: str | None,
    start_time: datetime,
    end_time: datetime,
    limit: int,
    cursor: str | None = None,
) -> dict[str, object]:
    params = {
        "accountId": account_id,
        "startTime": start_time.isoformat(),
        "endTime": end_time.isoformat(),
        "limit": str(limit),
    }
    if symbol is not None:
        params["symbol"] = symbol
    if cursor is not None:
        params["cursor"] = cursor
    payload = runtime_get("/venue/fill-history", params=params)
    return _history_page(payload, "Runtime fill-history response")


def _object_list(payload: object, label: str) -> list[dict[str, object]]:
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise CrossSpreadLiveReadError(f"{label} is malformed")
    return [dict(row) for row in payload]


def _history_page(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise CrossSpreadLiveReadError(f"{label} is malformed")
    items = payload.get("items")
    if not isinstance(items, list) or any(not isinstance(row, dict) for row in items):
        raise CrossSpreadLiveReadError(f"{label} items are malformed")
    return dict(payload)


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])
    return f"HTTP {response.status_code}"


