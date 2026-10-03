"""Small, fail-closed wrapper for Bybit's native strategy endpoints.

The strategy API is not exposed by all pybit releases.  Calling pybit's
authenticated request primitive keeps the account session, signing, throttling
and timeout policy owned by ``BybitConnections``.
"""

from __future__ import annotations

from typing import Any

from app.gateway_errors import GatewayRequestRejectedError, GatewayResultUnknownError


class _StrategyRejected(GatewayRequestRejectedError):
    def __init__(self, code: int):
        self.code = code
        super().__init__(f"Bybit native strategy rejected: {code}")


def _request(
    client: Any, *, method: str, path: str, params: dict[str, object]
) -> dict[str, object]:
    try:
        endpoint = str(getattr(client, "endpoint", "")).rstrip("/")
        if not endpoint.startswith("https://"):
            raise GatewayResultUnknownError("Bybit native strategy client endpoint is not absolute")
        response = client._submit_request(
            method=method, path=f"{endpoint}{path}", query=params, auth=True
        )
    except Exception as exc:
        from pybit.exceptions import InvalidRequestError

        if isinstance(exc, InvalidRequestError):
            raise _StrategyRejected(int(exc.status_code)) from exc
        # A strategy create timeout is deliberately not retryable: the venue
        # may have accepted it and strategyId is the only safe recovery key.
        raise GatewayResultUnknownError(
            f"Bybit native strategy {path} result is unknown: {exc.__class__.__name__}"
        ) from exc
    if not isinstance(response, dict):
        raise GatewayResultUnknownError(f"Bybit native strategy {path} returned invalid data")
    if "retCode" not in response:
        raise GatewayResultUnknownError(f"Bybit native strategy {path} omitted retCode")
    try:
        code = int(response["retCode"])
    except (ValueError, TypeError) as exc:
        raise GatewayResultUnknownError("Native strategy retCode malformed") from exc
    if not isinstance(response.get("result"), dict) and code == 0:
        raise GatewayResultUnknownError("Native strategy result malformed")
    if code != 0:
        raise _StrategyRejected(code)
    return response


def create_chase_order(
    client: Any,
    *,
    category: str,
    symbol: str,
    side: str,
    size: str,
    reduce_only: bool,
    position_idx: int | None = None,
    max_chase_price: str | None = None,
    chase_distance: str | None = None,
    chase_percent_e4: int | None = None,
) -> str:
    if chase_distance is not None and chase_percent_e4 is not None:
        raise GatewayRequestRejectedError(
            "Native chase distance and percent are mutually exclusive"
        )
    payload: dict[str, object] = {
        "category": category,
        "symbol": symbol.upper(),
        "side": side,
        "size": size,
        "strategyType": "chaseOrder",
        "reduceOnly": reduce_only,
    }
    if position_idx is not None:
        payload["positionIdx"] = position_idx
    if max_chase_price is not None:
        payload["maxChasePrice"] = max_chase_price
    if chase_distance is not None:
        payload["chaseDistance"] = chase_distance
    elif chase_percent_e4 is not None:
        payload["chasePercentE4"] = chase_percent_e4
    response = _request(client, method="POST", path="/v5/strategy/create", params=payload)
    strategy_id = str((response.get("result") or {}).get("strategyId") or "")
    if not strategy_id:
        raise GatewayResultUnknownError("Bybit native chase accepted without strategyId")
    return strategy_id


def stop_strategy(client: Any, strategy_id: str) -> str:
    try:
        response = _request(
            client,
            method="POST",
            path="/v5/strategy/stop",
            params={"strategyId": strategy_id},
        )
    except _StrategyRejected as exc:
        if exc.code not in (60062, 60074):
            raise
        # Stop can race with a venue fill. This is not terminal evidence:
        # every caller must still reconcile the strategy, children and fills.
        return strategy_id
    result = response.get("result")
    if not isinstance(result, dict):
        raise GatewayResultUnknownError("Bybit native strategy stop returned invalid result")
    returned = str(result.get("strategyId") or "")
    if returned != strategy_id:
        raise GatewayResultUnknownError(
            "Bybit native strategy stop returned a different strategyId"
        )
    return returned


def get_strategy(
    client: Any, strategy_id: str, *, page_size: int = 50, max_pages: int = 100
) -> dict[str, object]:
    """Find one strategy by exact ID, following bounded cursor pagination."""
    cursor: str | None = None
    seen_cursors: set[str] = set()
    for _ in range(max_pages):
        params: dict[str, object] = {
            "strategyId": strategy_id,
            "pageSize": page_size,
            "strategyType": "chaseOrder",
        }
        if cursor:
            params["cursor"] = cursor
        response = _request(client, method="GET", path="/v5/strategy/list", params=params)
        result = response.get("result")
        if not isinstance(result, dict):
            raise GatewayResultUnknownError("Bybit native strategy list returned invalid result")
        rows = result.get("list")
        if not isinstance(rows, list):
            raise GatewayResultUnknownError("Bybit native strategy list returned invalid list")
        for row in rows:
            if isinstance(row, dict) and str(row.get("strategyId") or "") == strategy_id:
                return row
        next_cursor = result.get("nextCursor")
        if next_cursor in (None, ""):
            break
        if not isinstance(next_cursor, str) or next_cursor in seen_cursors:
            raise GatewayResultUnknownError("Bybit native strategy list returned a repeated cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    else:
        raise GatewayResultUnknownError("Bybit native strategy list pagination exceeded bound")
    raise GatewayRequestRejectedError("Bybit native strategy was not found")


def list_strategy_orders(
    client: Any,
    *,
    strategy_id: str,
    symbol: str | None = None,
    page_size: int = 50,
    max_pages: int = 100,
) -> list[dict[str, object]]:
    params: dict[str, object] = {
        "strategyId": strategy_id,
        "strategyType": "chaseOrder",
        "pageSize": page_size,
    }
    if symbol:
        params["symbol"] = symbol.upper()
    rows: list[dict[str, object]] = []
    cursor: str | None = None
    seen: dict[str, dict[str, object]] = {}
    seen_cursors: set[str] = set()
    for _ in range(max_pages):
        query = dict(params)
        if cursor:
            query["cursor"] = cursor
        response = _request(client, method="GET", path="/v5/strategy/order-list", params=query)
        result = response.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("list"), list):
            raise GatewayResultUnknownError(
                "Bybit native strategy order-list returned invalid result"
            )
        page = result["list"]
        for row in page or []:
            if not isinstance(row, dict) or not row.get("orderId"):
                raise GatewayResultUnknownError("Native child identity malformed")
            order_id = str(row["orderId"])
            if order_id in seen and seen[order_id] != row:
                raise GatewayResultUnknownError("Native child pagination conflicts")
            if order_id not in seen:
                seen[order_id] = row
                rows.append(row)
        next_cursor = result.get("nextCursor")
        if next_cursor not in (None, "") and not isinstance(next_cursor, str):
            raise GatewayResultUnknownError(
                "Bybit native strategy order-list returned invalid cursor"
            )
        if next_cursor and next_cursor in seen_cursors:
            raise GatewayResultUnknownError(
                "Bybit native strategy order-list returned a repeated cursor"
            )
        cursor = next_cursor or ""
        if cursor:
            seen_cursors.add(cursor)
        if not cursor:
            return rows
    raise GatewayResultUnknownError("Bybit native strategy order-list pagination exceeded bound")
