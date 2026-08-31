from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from app.config import get_settings
from app.gateway_factory import create_gateway
from app.models import (
    CrossSpreadMetrics,
    CrossSpreadSnapshotResponse,
    CrossSpreadVenueSnapshot,
    MarketQuote,
    VenuePosition,
)
from app.mt5_connection import initialize_mt5
from app.mt5_file_bridge import read_mt5_bridge_snapshot
from app.secret_resolver import resolve_secret_reference

BYBIT_CREDENTIAL_REF = "secret://crypto-test-001"
MT5_CREDENTIAL_REF = "secret://mt5-demo-001"

# Snapshot cache to absorb the 1Hz exit-monitor polling without hammering the
# live venues on every tick. TTL is short enough to keep quotes fresh while
# cutting venue round-trips by an order of magnitude.
_SNAPSHOT_CACHE: dict[str, tuple[float, CrossSpreadSnapshotResponse]] = {}
_SNAPSHOT_CACHE_TTL_SECONDS = 5.0


def build_cross_spread_snapshot(
    *,
    bybit_symbol: str,
    mt5_symbol: str,
    bybit_demo: bool = False,
    bybit_recv_window: int = 20000,
    bybit_credential_ref: str = BYBIT_CREDENTIAL_REF,
    mt5_credential_ref: str = MT5_CREDENTIAL_REF,
    mt5_terminal_path: str | None = None,
    mt5_bridge_file_path: str | None = None,
    mt5_timeout_seconds: float = 5.0,
    bybit_session_factory: Any | None = None,
    mt5_module: Any | None = None,
    mt5_preferred_symbol: str | None = None,
    bybit_timestamp_offset_ms: int = 0,
) -> CrossSpreadSnapshotResponse:
    settings = get_settings()
    cache_key = (
        f"{bybit_symbol}|{mt5_symbol}|{bybit_demo}|"
        f"{bybit_credential_ref}|{mt5_credential_ref}"
    )
    cached = _SNAPSHOT_CACHE.get(cache_key)
    if cached is not None and time.time() - cached[0] < _SNAPSHOT_CACHE_TTL_SECONDS:
        return cached[1]

    bybit = _build_bybit_snapshot(
        symbol=bybit_symbol,
        demo=bybit_demo,
        recv_window=bybit_recv_window,
        credential_ref=bybit_credential_ref,
        session_factory=bybit_session_factory,
        bybit_timestamp_offset_ms=bybit_timestamp_offset_ms,
    )
    mt5 = _build_mt5_snapshot(
        symbol=mt5_symbol,
        credential_ref=mt5_credential_ref,
        terminal_path=mt5_terminal_path,
        bridge_file_path=mt5_bridge_file_path,
        timeout_seconds=mt5_timeout_seconds,
        mt5_module=mt5_module,
        preferred_symbol=mt5_preferred_symbol,
    )
    if (
        settings.gateway_name.strip().lower() in {"fake", "simulation"}
        and bybit_session_factory is None
        and mt5_module is None
    ):
        bybit = bybit.model_copy(
            update={"positions": _gateway_positions_for_symbol(bybit_symbol)}
        )
        mt5 = mt5.model_copy(
            update={"positions": _gateway_positions_for_symbol(mt5.symbol)}
        )
    metrics = CrossSpreadMetrics(
        fundingRate=_extract_funding_rate(bybit),
        usdtUsd=_fetch_usdt_usd(
            demo=bybit_demo,
            recv_window=bybit_recv_window,
            session_factory=bybit_session_factory,
            bybit_timestamp_offset_ms=bybit_timestamp_offset_ms,
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

    result = CrossSpreadSnapshotResponse(
        status=status,
        bybit=bybit,
        mt5=mt5,
        longSpread=long_spread,
        shortSpread=short_spread,
        metrics=metrics,
    )
    _SNAPSHOT_CACHE[cache_key] = (time.time(), result)
    return result


def estimate_cached_fill_price(
    *,
    symbol: str,
    side: str,
) -> Decimal | None:
    normalized_symbol = symbol.upper()
    normalized_side = side.lower()
    snapshots = sorted(_SNAPSHOT_CACHE.values(), key=lambda item: item[0], reverse=True)
    for _, snapshot in snapshots:
        venue = None
        if snapshot.bybit.symbol.upper() == normalized_symbol:
            venue = snapshot.bybit
        elif snapshot.mt5.symbol.upper() == normalized_symbol:
            venue = snapshot.mt5
        if venue is None or venue.quote is None:
            continue
        if normalized_side == "buy":
            return venue.quote.ask
        if normalized_side == "sell":
            return venue.quote.bid
    return None


def _gateway_positions_for_symbol(symbol: str) -> list[VenuePosition]:
    gateway = create_gateway(get_settings().gateway_name, live_write_enabled=False)
    normalized_symbol = symbol.upper()
    positions = []
    for row in gateway.list_positions():
        if row.symbol.upper() != normalized_symbol or row.net_quantity == 0:
            continue
        positions.append(
            VenuePosition(
                symbol=row.symbol,
                side="buy" if row.net_quantity > 0 else "sell",
                quantity=row.net_quantity,
                averagePrice=row.average_price,
                unrealizedPnl=row.unrealized_pnl,
                externalId=row.external_position_id,
            )
        )
    return positions


def _build_bybit_snapshot(
    *,
    symbol: str,
    demo: bool,
    recv_window: int,
    credential_ref: str,
    session_factory: Any | None,
    bybit_timestamp_offset_ms: int = 0,
) -> CrossSpreadVenueSnapshot:
    try:
        credentials = resolve_secret_reference(
            credential_ref,
            required_fields=("API_KEY", "SECRET"),
        )
        if session_factory is None:
            from pybit import _helpers
            from pybit.unified_trading import HTTP

            _apply_bybit_timestamp_offset(_helpers, bybit_timestamp_offset_ms)
            session_factory = HTTP
        session = session_factory(
            testnet=False,
            demo=demo,
            recv_window=recv_window,
            api_key=credentials["API_KEY"],
            api_secret=credentials["SECRET"],
        )
        ticker = _fetch_bybit_tickers_with_retry(
            session,
            symbol=symbol,
            attempts=2,
        )
        if ticker is None:
            return _unavailable(
                "bybit",
                symbol,
                "Bybit ticker fetch failed after retry (proxy/link flaky)",
            )
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
    credential_ref: str,
    terminal_path: str | None,
    bridge_file_path: str | None,
    timeout_seconds: float,
    mt5_module: Any | None,
    preferred_symbol: str | None = None,
) -> CrossSpreadVenueSnapshot:
    try:
        credentials = resolve_secret_reference(
            credential_ref,
            required_fields=("LOGIN", "PASSWORD", "SERVER"),
        )
        if mt5_module is None:
            try:
                import MetaTrader5 as mt5_module  # type: ignore[import-not-found]
            except Exception:
                if bridge_file_path and not terminal_path:
                    return read_mt5_bridge_snapshot(bridge_file_path, symbol)
                return _unavailable(
                    "mt5",
                    symbol,
                    (
                        "MT5 Python bridge is not responding in the web runtime; "
                        "keep terminal open and verify terminal bridge separately"
                    ),
                )

        login = int(credentials["LOGIN"])
        timeout_ms = int(timeout_seconds * 1000)
        if not initialize_mt5(
            mt5_module,
            terminal_path=terminal_path,
            timeout=timeout_ms,
        ):
            return _unavailable("mt5", symbol, "MT5 initialize failed")
        if not mt5_module.login(
            login,
            password=credentials["PASSWORD"],
            server=credentials["SERVER"],
            timeout=timeout_ms,
        ):
            return _unavailable("mt5", symbol, "MT5 login failed")

        try:
            try:
                from app.mt5_symbol_resolver import resolve_mt5_symbol

                resolved = resolve_mt5_symbol(
                    mt5_module=mt5_module,
                    base_symbol=symbol,
                    preferred=preferred_symbol,
                    cache_key=(str(login), str(credentials.get("SERVER") or "")),
                )
                if resolved is not None:
                    symbol = resolved.symbol
            except Exception:
                # Resolution is best-effort; fall back to the configured symbol.
                pass
            symbol_selector = getattr(mt5_module, "symbol_select", None)
            if callable(symbol_selector):
                symbol_selector(symbol, True)
            tick = mt5_module.symbol_info_tick(symbol)
            if tick is None:
                return _unavailable("mt5", symbol, "MT5 symbol tick unavailable")
            symbol_info_getter = getattr(mt5_module, "symbol_info", None)
            symbol_info = symbol_info_getter(symbol) if callable(symbol_info_getter) else None
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



def _read_mt5_terminal_swap_reason(symbol: str, terminal_path: str | None) -> str | None:
    try:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]

        initialize_attempts = [terminal_path, None] if terminal_path else [None]
        for attempted_path in initialize_attempts:
            if not initialize_mt5(mt5, terminal_path=attempted_path):
                continue
            try:
                symbol_info = mt5.symbol_info(symbol)
                return _mt5_symbol_reason(symbol_info)
            finally:
                mt5.shutdown()
        return None
    except Exception:
        return None

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


def _join_reason_text(*parts: str | None) -> str | None:
    present_parts = [part for part in parts if part]
    return ";".join(present_parts) if present_parts else None


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
    bybit_timestamp_offset_ms: int = 0,
) -> Decimal | None:
    try:
        credentials = resolve_secret_reference(BYBIT_CREDENTIAL_REF)
        if session_factory is None:
            from pybit import _helpers
            from pybit.unified_trading import HTTP

            _apply_bybit_timestamp_offset(_helpers, bybit_timestamp_offset_ms)
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


def _apply_bybit_timestamp_offset(helpers: Any, offset_ms: int) -> None:
    """Compensate local clock skew against the Bybit server.

    Bybit rejects authenticated requests whose timestamp is in the future by
    more than the recv_window.  When the local clock runs ahead (measured via
    ``/v5/market/time``), injecting a negative offset keeps signatures valid.
    """
    offset_ms = int(offset_ms or 0)
    if offset_ms == 0:
        return
    original = getattr(helpers, "_vg_original_generate_timestamp", None)
    if original is None:
        original = helpers.generate_timestamp
        helpers._vg_original_generate_timestamp = original
    helpers.generate_timestamp = lambda: original() + offset_ms


def _fetch_bybit_tickers_with_retry(session: Any, *, symbol: str, attempts: int) -> Any | None:
    """Fetch Bybit tickers with a single retry for flaky proxy connections.

    Returns the raw ticker response (or ``None`` when all attempts fail), so
    callers can keep a stale-but-readable snapshot instead of an empty page.
    """
    import time

    last_error: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            return session.get_tickers(category="linear", symbol=symbol)
        except Exception as exc:  # noqa: BLE001 - network flakiness is expected
            last_error = exc
            if attempt < max(1, attempts) - 1:
                time.sleep(0.5)
    if last_error is not None:
        return None
    return None

