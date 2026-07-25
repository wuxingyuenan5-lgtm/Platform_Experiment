from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models import (
    CrossSpreadMetrics,
    CrossSpreadSnapshotResponse,
    CrossSpreadVenueSnapshot,
    MarketQuote,
    VenuePosition,
)
from app.mt5_file_bridge import read_mt5_bridge_snapshot
from app.secret_resolver import resolve_secret_reference

BYBIT_CREDENTIAL_REF = "secret://crypto-test-001"
MT5_CREDENTIAL_REF = "secret://mt5-demo-001"


def build_cross_spread_snapshot(
    *,
    bybit_symbol: str,
    mt5_symbol: str,
    bybit_demo: bool = False,
    bybit_recv_window: int = 20000,
    mt5_terminal_path: str | None = None,
    mt5_bridge_file_path: str | None = None,
    bybit_session_factory: Any | None = None,
    mt5_module: Any | None = None,
) -> CrossSpreadSnapshotResponse:
    bybit = _build_bybit_snapshot(
        symbol=bybit_symbol,
        demo=bybit_demo,
        recv_window=bybit_recv_window,
        session_factory=bybit_session_factory,
    )
    mt5 = _build_mt5_snapshot(
        symbol=mt5_symbol,
        terminal_path=mt5_terminal_path,
        bridge_file_path=mt5_bridge_file_path,
        mt5_module=mt5_module,
    )
    metrics = CrossSpreadMetrics(
        fundingRate=_extract_funding_rate(bybit),
        usdtUsd=_fetch_usdt_usd(
            demo=bybit_demo,
            recv_window=bybit_recv_window,
            session_factory=bybit_session_factory,
        ),
        buyerInventoryFee=_extract_swap_value(mt5.reason, "swapLong"),
        sellerInventoryFee=_extract_swap_value(mt5.reason, "swapShort"),
    )
    long_spread = None
    short_spread = None
    if bybit.quote is not None and mt5.quote is not None:
        long_spread = bybit.quote.ask - mt5.quote.bid
        short_spread = bybit.quote.bid - mt5.quote.ask

    if bybit.status == "available" and mt5.status == "available":
        status = "available"
    elif bybit.status == "available" or mt5.status == "available":
        status = "partial"
    else:
        status = "unavailable"

    return CrossSpreadSnapshotResponse(
        status=status,
        bybit=bybit,
        mt5=mt5,
        longSpread=long_spread,
        shortSpread=short_spread,
        metrics=metrics,
    )


def _build_bybit_snapshot(
    *,
    symbol: str,
    demo: bool,
    recv_window: int,
    session_factory: Any | None,
) -> CrossSpreadVenueSnapshot:
    try:
        credentials = resolve_secret_reference(BYBIT_CREDENTIAL_REF)
        using_injected_session = session_factory is not None
        if session_factory is None:
            from pybit.unified_trading import HTTP

            session_factory = HTTP
        session = session_factory(
            testnet=False,
            demo=demo,
            recv_window=recv_window,
            api_key=credentials["API_KEY"],
            api_secret=credentials["SECRET"],
        )
        ticker = session.get_tickers(category="linear", symbol=symbol)
        if ticker.get("retCode") != 0:
            return _unavailable("bybit", symbol, f"ticker error: {ticker.get('retMsg')}")
        ticker_row = ticker["result"]["list"][0]
        quote = MarketQuote(
            bid=Decimal(str(ticker_row["bid1Price"])),
            ask=Decimal(str(ticker_row["ask1Price"])),
            mid=(Decimal(str(ticker_row["bid1Price"])) + Decimal(str(ticker_row["ask1Price"])))
            / Decimal("2"),
            last=Decimal(str(ticker_row.get("lastPrice") or ticker_row["bid1Price"])),
            currency="USDT",
        )
        funding_rate = _optional_decimal(ticker_row.get("fundingRate"))
        positions = []
        position_reason = "Bybit position fetch is skipped in live quote snapshot"
        if not using_injected_session:
            return CrossSpreadVenueSnapshot(
                venue="bybit",
                symbol=symbol,
                status="available",
                quote=quote,
                positions=positions,
                reason=_join_reason(position_reason, funding_rate),
            )
        position_reason = None
        try:
            positions_response = session.get_positions(category="linear", symbol=symbol)
            if positions_response.get("retCode") == 0:
                for row in positions_response.get("result", {}).get("list", []):
                    size = Decimal(str(row.get("size") or "0"))
                    if size == 0:
                        continue
                    side = str(row.get("side") or "").lower()
                    signed_size = size if side == "buy" else -size
                    positions.append(
                        VenuePosition(
                            symbol=symbol,
                            side=side or "unknown",
                            quantity=signed_size,
                            averagePrice=_optional_decimal(row.get("avgPrice")),
                            unrealizedPnl=_optional_decimal(row.get("unrealisedPnl")),
                        )
                    )
            else:
                position_reason = f"position error: {positions_response.get('retMsg')}"
        except Exception as exc:
            position_reason = str(exc)
        return CrossSpreadVenueSnapshot(
            venue="bybit",
            symbol=symbol,
            status="available",
            quote=quote,
            positions=positions,
            reason=_join_reason(position_reason, funding_rate),
        )
    except Exception as exc:
        return _unavailable("bybit", symbol, str(exc))


def _build_mt5_snapshot(
    *,
    symbol: str,
    terminal_path: str | None,
    bridge_file_path: str | None,
    mt5_module: Any | None,
) -> CrossSpreadVenueSnapshot:
    try:
        credentials = resolve_secret_reference(MT5_CREDENTIAL_REF)
        if mt5_module is None:
            if bridge_file_path:
                return read_mt5_bridge_snapshot(bridge_file_path, symbol)
            return _unavailable(
                "mt5",
                symbol,
                (
                    "MT5 Python bridge is not responding in the web runtime; "
                    "keep terminal open and verify terminal bridge separately"
                ),
            )

        login = int(credentials["API_KEY"])
        initialize_kwargs = {
            "login": login,
            "password": credentials["SECRET"],
            "server": credentials["PASSPHRASE"],
        }
        if terminal_path:
            initialize_kwargs["path"] = terminal_path
        if not mt5_module.initialize(**initialize_kwargs):
            return _unavailable("mt5", symbol, "MT5 initialize failed")

        try:
            tick = mt5_module.symbol_info_tick(symbol)
            if tick is None:
                return _unavailable("mt5", symbol, "MT5 symbol tick unavailable")
            symbol_info = mt5_module.symbol_info(symbol)
            bid = Decimal(str(tick.bid))
            ask = Decimal(str(tick.ask))
            quote = MarketQuote(
                bid=bid,
                ask=ask,
                mid=(bid + ask) / Decimal("2"),
                last=_optional_decimal(getattr(tick, "last", None)),
                currency="USD",
            )
            positions = []
            for row in mt5_module.positions_get(symbol=symbol) or []:
                raw_volume = Decimal(str(getattr(row, "volume", "0")))
                side_code = getattr(row, "type", None)
                side = "buy" if side_code == mt5_module.ORDER_TYPE_BUY else "sell"
                signed_volume = raw_volume if side == "buy" else -raw_volume
                positions.append(
                    VenuePosition(
                        symbol=symbol,
                        side=side,
                        quantity=signed_volume,
                        averagePrice=_optional_decimal(getattr(row, "price_open", None)),
                        unrealizedPnl=_optional_decimal(getattr(row, "profit", None)),
                        externalId=str(getattr(row, "ticket", "")) or None,
                    )
                )
            return CrossSpreadVenueSnapshot(
                venue="mt5",
                symbol=symbol,
                status="available",
                quote=quote,
                positions=positions,
                reason=_mt5_symbol_reason(symbol_info),
            )
        finally:
            mt5_module.shutdown()
    except Exception as exc:
        return _unavailable("mt5", symbol, str(exc))


def _optional_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _join_reason(position_reason: str | None, funding_rate: Decimal | None) -> str | None:
    parts = []
    if position_reason:
        parts.append(position_reason)
    if funding_rate is not None:
        parts.append(f"fundingRate={funding_rate}")
    return ";".join(parts) if parts else None


def _mt5_symbol_reason(symbol_info: object | None) -> str | None:
    if symbol_info is None:
        return None
    fields = (
        ("swapLong", "swap_long"),
        ("swapShort", "swap_short"),
        ("swapMode", "swap_mode"),
        ("swapRollover3Days", "swap_rollover3days"),
        ("contractSize", "trade_contract_size"),
    )
    parts = []
    for key, attribute in fields:
        value = getattr(symbol_info, attribute, None)
        if value is not None:
            parts.append(f"{key}={value}")
    return ";".join(parts) if parts else None


def _extract_funding_rate(snapshot: CrossSpreadVenueSnapshot) -> Decimal | None:
    return _extract_reason_value(snapshot.reason, "fundingRate")


def _extract_swap_value(reason: str | None, key: str) -> Decimal | None:
    return _extract_reason_value(reason, key)


def _extract_reason_value(reason: str | None, key: str) -> Decimal | None:
    if not reason:
        return None
    prefix = f"{key}="
    for part in reason.split(";"):
        if part.startswith(prefix):
            return _optional_decimal(part.removeprefix(prefix))
    return None


def _fetch_usdt_usd(
    *,
    demo: bool,
    recv_window: int,
    session_factory: Any | None,
) -> Decimal | None:
    try:
        credentials = resolve_secret_reference(BYBIT_CREDENTIAL_REF)
        if session_factory is None:
            from pybit.unified_trading import HTTP

            session_factory = HTTP
        session = session_factory(
            testnet=False,
            demo=demo,
            recv_window=recv_window,
            api_key=credentials["API_KEY"],
            api_secret=credentials["SECRET"],
        )
        ticker = session.get_tickers(category="spot", symbol="USDCUSDT")
        if ticker.get("retCode") != 0:
            return None
        row = ticker["result"]["list"][0]
        usdc_usdt = _optional_decimal(row.get("lastPrice") or row.get("bid1Price"))
        if usdc_usdt is None or usdc_usdt == 0:
            return None
        return Decimal("1") / usdc_usdt
    except Exception:
        return None


def _unavailable(venue: str, symbol: str, reason: str) -> CrossSpreadVenueSnapshot:
    return CrossSpreadVenueSnapshot(
        venue=venue,
        symbol=symbol,
        status="unavailable",
        reason=reason,
    )
