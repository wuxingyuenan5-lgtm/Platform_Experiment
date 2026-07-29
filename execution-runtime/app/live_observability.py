from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from app.gateway_errors import GatewayConfigurationError, GatewayResultUnknownError
from app.models import (
    VenueAccountRiskSnapshot,
    VenueFillHistoryPage,
    VenueOrderHistoryPage,
    VenuePositionSnapshot,
)


def bybit_positions(adapter, account_id: str | None = None) -> list[VenuePositionSnapshot]:
    account = account_id or adapter._single_account()
    adapter._assert_account(account)
    try:
        response = adapter._with_fresh_client_retry(
            lambda client: client.get_positions(
                category=adapter.settings.bybit_category,
                settleCoin=adapter.settings.bybit_settle_coin,
                limit=200,
            )
        )
        adapter._require_success(response, "Bybit position-risk query failed")
    except Exception as exc:
        raise GatewayResultUnknownError("Bybit position-risk result is unknown") from exc
    snapshots: list[VenuePositionSnapshot] = []
    for row in adapter._result_list(response):
        size = Decimal(str(row.get("size") or "0"))
        if size == 0:
            continue
        symbol = str(row.get("symbol") or "").upper()
        instrument_id = adapter.settings.bybit_instruments.get(symbol)
        if instrument_id is None:
            continue
        side = str(row.get("side") or "")
        quantity = size if side == "Buy" else -size
        liquidation = adapter._optional_decimal(row.get("liqPrice"))
        if liquidation is not None and liquidation <= 0:
            liquidation = None
        snapshots.append(
            VenuePositionSnapshot(
                source=adapter.name,
                externalPositionId=f"{account}:{symbol}:{row.get('positionIdx', 0)}",
                accountId=account,
                instrumentId=instrument_id,
                symbol=symbol,
                netQuantity=quantity,
                averagePrice=adapter._optional_decimal(row.get("avgPrice")),
                currentPrice=adapter._optional_decimal(row.get("markPrice")),
                markPrice=adapter._optional_decimal(row.get("markPrice")),
                breakEvenPrice=adapter._optional_decimal(row.get("breakEvenPrice")),
                liquidationPrice=liquidation,
                liquidationPriceSource=(
                    "venue_reported" if liquidation is not None else "venue_not_finite"
                ),
                positionValue=adapter._optional_decimal(row.get("positionValue")),
                leverage=adapter._optional_decimal(row.get("leverage")),
                initialMargin=adapter._optional_decimal(
                    row.get("positionIM") or row.get("positionIMByMp")
                ),
                maintenanceMargin=adapter._optional_decimal(
                    row.get("positionMM") or row.get("positionMMByMp")
                ),
                unrealizedPnl=adapter._optional_decimal(row.get("unrealisedPnl")),
                realizedPnl=adapter._optional_decimal(
                    row.get("curRealisedPnl") or row.get("cumRealisedPnl")
                ),
                stopLossPrice=adapter._optional_decimal(row.get("stopLoss")),
                takeProfitPrice=adapter._optional_decimal(row.get("takeProfit")),
                positionStatus=str(row.get("positionStatus") or "unknown"),
                riskLimitValue=adapter._optional_decimal(row.get("riskLimitValue")),
                reduceOnlyRestricted=(
                    bool(row.get("isReduceOnly")) if "isReduceOnly" in row else None
                ),
                autoAddMargin=(
                    int(row.get("autoAddMargin") or 0) == 1
                    if "autoAddMargin" in row
                    else None
                ),
                currency=adapter.settings.bybit_settle_coin,
                asOf=adapter._millis(row.get("updatedTime")),
                fieldAvailability={
                    "liquidationPrice": (
                        "venue_reported" if liquidation is not None else "not_finite_for_mode"
                    ),
                    "marginCallLevel": "account_level_only",
                    "stopOutLevel": "account_level_only",
                },
            )
        )
    return snapshots


def mt5_positions(adapter, account_id: str | None = None) -> list[VenuePositionSnapshot]:
    account = account_id or adapter._single_account()
    adapter._assert_account(account)
    mt5 = adapter._connect()
    try:
        rows = mt5.positions_get() or ()
    except Exception as exc:
        raise GatewayResultUnknownError("MT5 position-risk result is unknown") from exc
    currency = adapter._account_currency(mt5)
    snapshots: list[VenuePositionSnapshot] = []
    for row in rows:
        symbol = str(getattr(row, "symbol", "")).upper()
        instrument_id = adapter.settings.mt5_instruments.get(symbol)
        if instrument_id is None:
            continue
        volume = Decimal(str(getattr(row, "volume", 0) or 0))
        if int(getattr(row, "type", -1)) == int(getattr(mt5, "POSITION_TYPE_SELL", 1)):
            volume = -volume
        snapshots.append(
            VenuePositionSnapshot(
                source=adapter.name,
                externalPositionId=str(getattr(row, "ticket", 0)),
                accountId=account,
                instrumentId=instrument_id,
                symbol=symbol,
                netQuantity=volume,
                averagePrice=Decimal(str(getattr(row, "price_open", 0) or 0)),
                currentPrice=Decimal(str(getattr(row, "price_current", 0) or 0)),
                liquidationPrice=None,
                liquidationPriceSource="not_available_mt5_api",
                unrealizedPnl=Decimal(str(getattr(row, "profit", 0) or 0)),
                stopLossPrice=_positive_decimal(getattr(row, "sl", 0)),
                takeProfitPrice=_positive_decimal(getattr(row, "tp", 0)),
                swap=Decimal(str(getattr(row, "swap", 0) or 0)),
                positionStatus="open",
                currency=currency,
                asOf=adapter._position_time(row),
                fieldAvailability={
                    "liquidationPrice": "not_available_mt5_api",
                    "initialMargin": "account_level_only",
                    "maintenanceMargin": "account_level_only",
                    "leverage": "account_level_only",
                },
            )
        )
    return snapshots


def mt5_account_risk(adapter, account_id: str) -> VenueAccountRiskSnapshot:
    adapter._assert_account(account_id)
    mt5 = adapter._connect()
    info = mt5.account_info()
    terminal = mt5.terminal_info()
    if info is None or terminal is None:
        raise GatewayResultUnknownError(f"MT5 account-risk query failed: {mt5.last_error()}")
    actual_login = str(getattr(info, "login", ""))
    secret = adapter._secret()
    if actual_login != str(secret["LOGIN"]):
        raise GatewayConfigurationError("Connected MT5 account does not match configured login")
    threshold_mode = str(int(getattr(info, "margin_so_mode", -1)))
    return VenueAccountRiskSnapshot(
        source=adapter.name,
        accountId=account_id,
        currency=str(getattr(info, "currency", "USD")),
        equity=Decimal(str(getattr(info, "equity", 0) or 0)),
        walletBalance=Decimal(str(getattr(info, "balance", 0) or 0)),
        marginBalance=Decimal(str(getattr(info, "equity", 0) or 0)),
        availableBalance=Decimal(str(getattr(info, "margin_free", 0) or 0)),
        initialMargin=Decimal(str(getattr(info, "margin", 0) or 0)),
        maintenanceMargin=_optional_decimal(getattr(info, "margin_maintenance", None)),
        unrealizedPnl=Decimal(str(getattr(info, "profit", 0) or 0)),
        marginLevel=_optional_decimal(getattr(info, "margin_level", None)),
        marginCallLevel=_optional_decimal(getattr(info, "margin_so_call", None)),
        stopOutLevel=_optional_decimal(getattr(info, "margin_so_so", None)),
        marginThresholdMode=threshold_mode,
        leverage=_optional_decimal(getattr(info, "leverage", None)),
        marginMode=str(int(getattr(info, "margin_mode", -1))),
        tradeAllowed=bool(getattr(info, "trade_allowed", False)),
        expertTradingAllowed=(
            bool(getattr(info, "trade_expert", False))
            and bool(getattr(terminal, "trade_allowed", False))
        ),
        fieldAvailability={
            "liquidationPrice": "not_available_mt5_api",
            "marginCallLevel": "venue_reported",
            "stopOutLevel": "venue_reported",
            "marginThresholdMode": "0_percent_or_1_money_per_mt5_enum",
        },
        asOf=datetime.now(UTC),
    )


def mt5_order_history(
    adapter,
    *,
    account_id: str,
    symbol: str | None,
    start_time: datetime,
    end_time: datetime,
    cursor: str | None,
    limit: int,
    scope: Literal["active", "closed"],
) -> VenueOrderHistoryPage:
    adapter._assert_account(account_id)
    mt5 = adapter._connect()
    try:
        if scope == "active":
            rows = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
        else:
            rows = mt5.history_orders_get(start_time, end_time) or ()
    except Exception as exc:
        raise GatewayResultUnknownError("MT5 paged order result is unknown") from exc
    items = []
    for row in rows or ():
        row_symbol = str(getattr(row, "symbol", "")).upper()
        if symbol and row_symbol != symbol.upper():
            continue
        snapshot = adapter._snapshot(mt5, row, account_id)
        if snapshot is not None:
            items.append(snapshot)
    items.sort(key=lambda item: (item.as_of, item.external_order_id), reverse=True)
    offset = _cursor_offset(cursor)
    page_size = max(1, min(limit, 100))
    page_items = items[offset : offset + page_size]
    next_offset = offset + len(page_items)
    return VenueOrderHistoryPage(
        source=adapter.name,
        accountId=account_id,
        items=page_items,
        nextCursor=str(next_offset) if next_offset < len(items) else None,
        startTime=start_time,
        endTime=end_time,
        dataQualityState="venue_windowed",
    )


def mt5_fill_history(
    adapter,
    *,
    account_id: str,
    symbol: str | None,
    start_time: datetime,
    end_time: datetime,
    cursor: str | None,
    limit: int,
) -> VenueFillHistoryPage:
    adapter._assert_account(account_id)
    mt5 = adapter._connect()
    try:
        deals = mt5.history_deals_get(start_time, end_time) or ()
    except Exception as exc:
        raise GatewayResultUnknownError("MT5 paged deal result is unknown") from exc
    items = []
    for deal in deals:
        if not adapter._is_trade_deal(mt5, deal):
            continue
        if symbol and str(getattr(deal, "symbol", "")).upper() != symbol.upper():
            continue
        snapshot = adapter._fill_snapshot(
            mt5,
            deal,
            account_id,
            target=None,
            fallback_route=None,
        )
        if snapshot is not None:
            items.append(snapshot)
    items.sort(key=lambda item: (item.occurred_at, item.external_fill_id), reverse=True)
    offset = _cursor_offset(cursor)
    page_size = max(1, min(limit, 100))
    page_items = items[offset : offset + page_size]
    next_offset = offset + len(page_items)
    return VenueFillHistoryPage(
        source=adapter.name,
        accountId=account_id,
        items=page_items,
        nextCursor=str(next_offset) if next_offset < len(items) else None,
        startTime=start_time,
        endTime=end_time,
        dataQualityState="venue_windowed",
    )


def _cursor_offset(cursor: str | None) -> int:
    if cursor is None or cursor == "":
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise GatewayConfigurationError("MT5 history cursor is invalid") from exc
    if offset < 0:
        raise GatewayConfigurationError("MT5 history cursor is invalid")
    return offset


def _optional_decimal(value) -> Decimal | None:
    if value in {None, ""}:
        return None
    return Decimal(str(value))


def _positive_decimal(value) -> Decimal | None:
    result = _optional_decimal(value)
    if result is None or result <= 0:
        return None
    return result
