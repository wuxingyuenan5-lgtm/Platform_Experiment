from decimal import Decimal, InvalidOperation

import httpx
from fastapi import HTTPException

from app import runtime_transport
from app.config import get_settings
from app.cross_spread import BYBIT_SYMBOL, STRATEGY_INSTANCE_ID, get_bybit_account_id
from app.cross_spread_live_read_client import CrossSpreadLiveReadError, runtime_get
from app.execution_risk import assert_execution_allowed


def read_bybit_leverage() -> dict:
    account_id = get_bybit_account_id()
    try:
        result = runtime_get(
            "/venue/bybit/leverage", {"accountId": account_id, "symbol": BYBIT_SYMBOL}
        )
    except CrossSpreadLiveReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _validated(result, account_id)


def update_bybit_leverage(leverage: Decimal) -> dict:
    settings = get_settings()
    if not settings.live_trading_enabled:
        raise HTTPException(status_code=403, detail="平台实盘写入未开启，杠杆未修改")
    account_id = get_bybit_account_id()
    assert_execution_allowed(STRATEGY_INSTANCE_ID, [account_id])
    try:
        response = runtime_transport.post(
            f"{settings.runtime_base_url}/venue/bybit/leverage",
            json={"accountId": account_id, "symbol": BYBIT_SYMBOL, "leverage": str(leverage)},
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", "交易所未接受杠杆设置")
        except ValueError:
            detail = "杠杆设置结果未确认，请刷新查询"
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="杠杆设置结果未知，请刷新查询；不会自动重试"
        ) from exc
    try:
        result = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="杠杆回执无法解析，请刷新查询") from exc
    return _validated(result, account_id, expected=leverage)


def _validated(result: object, account_id: str, *, expected: Decimal | None = None) -> dict:
    if (
        not isinstance(result, dict)
        or result.get("accountId") != account_id
        or result.get("symbol") != BYBIT_SYMBOL
    ):
        raise HTTPException(status_code=502, detail="杠杆回执身份不匹配，请刷新查询")
    value = result.get("leverage")
    if value is None and expected is None:
        return result
    try:
        actual = Decimal(str(value))
        if not actual.is_finite() or actual < 1 or (expected is not None and actual != expected):
            raise InvalidOperation
    except InvalidOperation as exc:
        raise HTTPException(status_code=502, detail="杠杆设置值未获确认，请刷新查询") from exc
    return result
