from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Lock

from app.config import get_settings
from app.cross_spread_schedule import resolve_mt5_session_state
from app.gateway import VenueGateway
from app.models import (
    CrossSpreadMetrics,
    CrossSpreadSnapshotResponse,
    CrossSpreadVenueSnapshot,
    MarketQuote,
    VenuePosition,
)
from app.redaction import redact_text

# Cache belongs to the injected gateway and explicit accounts, not credentials or
# a default terminal. It never connects an SDK or switches an MT5 account.
_SNAPSHOT_CACHE: dict[object, tuple[float, CrossSpreadSnapshotResponse]] = {}
_SNAPSHOT_CACHE_TTL_SECONDS = 1.0
_SNAPSHOT_LOCK = Lock()
_MAX_SOURCE_AGE_SECONDS = 30.0


def build_cross_spread_snapshot(
    *,
    gateway: VenueGateway,
    bybit_account_id: str,
    mt5_account_id: str,
    bybit_symbol: str,
    mt5_symbol: str,
) -> CrossSpreadSnapshotResponse:
    with _SNAPSHOT_LOCK:
        cache_key = (id(gateway), bybit_account_id, mt5_account_id, bybit_symbol, mt5_symbol)
        cached = _SNAPSHOT_CACHE.get(cache_key)
        if cached is not None and time.monotonic() - cached[0] < _SNAPSHOT_CACHE_TTL_SECONDS:
            return cached[1]
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="cross-market-read") as pool:
            bybit_future = pool.submit(
                _build_venue_snapshot,
                gateway=gateway,
                account_id=bybit_account_id,
                symbol=bybit_symbol,
                venue="bybit",
                category="linear",
            )
            mt5_future = pool.submit(
                _build_venue_snapshot,
                gateway=gateway,
                account_id=mt5_account_id,
                symbol=mt5_symbol,
                venue="mt5",
                category="mt5",
            )
            fx_future = pool.submit(_fetch_usdt_usd, gateway, bybit_account_id)
            bybit, mt5, usdt_usd = bybit_future.result(), mt5_future.result(), fx_future.result()
        long_spread = None
        short_spread = None
        if bybit.quote is not None and mt5.quote is not None:
            long_spread = bybit.quote.ask - mt5.quote.bid
            short_spread = bybit.quote.bid - mt5.quote.ask
        available_count = sum(venue.status == "available" for venue in (bybit, mt5))
        result = CrossSpreadSnapshotResponse(
            status=(
                "available"
                if available_count == 2
                else "partial"
                if available_count
                else "unavailable"
            ),
            bybit=bybit,
            mt5=mt5,
            longSpread=long_spread,
            shortSpread=short_spread,
            metrics=CrossSpreadMetrics(
                fundingRate=_extract_reason_value(bybit.reason, "fundingRate"),
                usdtUsd=usdt_usd,
                buyerInventoryFee=_extract_reason_value(mt5.reason, "swapLong"),
                sellerInventoryFee=_extract_reason_value(mt5.reason, "swapShort"),
            ),
            executionState=(
                "executable"
                if (
                    bybit.open_allowed
                    and bybit.close_allowed
                    and mt5.open_allowed
                    and mt5.close_allowed
                )
                else "monitor_only"
                if bybit.quote is not None or mt5.quote is not None
                else "unavailable"
            ),
        )
        _SNAPSHOT_CACHE[cache_key] = (time.monotonic(), result)
        return result


def _build_venue_snapshot(
    *,
    gateway: VenueGateway,
    account_id: str,
    symbol: str,
    venue: str,
    category: str,
) -> CrossSpreadVenueSnapshot:
    started = time.perf_counter()
    try:
        quote = gateway.get_market_quote(account_id=account_id, symbol=symbol, category=category)
        if quote.account_id != account_id or quote.category not in {category, "simulation"}:
            raise ValueError("Market quote account/category identity mismatch")
        reasons = []
        if quote.funding_rate is not None:
            reasons.append(f"fundingRate={quote.funding_rate}")
        for label, key in (
            ("swapLong", "swap_long"),
            ("swapShort", "swap_short"),
            ("swapMode", "swap_mode"),
            ("swapRollover3Days", "swap_rollover3days"),
            ("contractSize", "trade_contract_size"),
        ):
            value = quote.raw_payload.get(key)
            if value is not None:
                reasons.append(f"{label}={value}")
        positions = []
        try:
            rows = gateway.get_positions(account_id)
            for row in rows:
                if row.account_id != account_id:
                    raise ValueError("Position account identity mismatch")
                if row.symbol.upper() != quote.symbol.upper() or row.net_quantity == 0:
                    continue
                if row.category not in {category, "simulation"}:
                    continue
                positions.append(
                    VenuePosition(
                        symbol=row.symbol,
                        side="buy" if row.net_quantity > 0 else "sell",
                        quantity=row.net_quantity,
                        averagePrice=row.average_price,
                        unrealizedPnl=row.unrealized_pnl,
                        externalId=row.external_position_id,
                        accountId=row.account_id,
                        currency=row.currency,
                        asOf=row.as_of,
                    )
                )
        except Exception as exc:
            positions = []
            reasons.append(f"positions unavailable: {redact_text(str(exc))}")
        open_allowed, close_allowed, block_reason = _execution_capability(venue, quote)
        if venue == "bybit":
            market_status = "open"
            trading_hours = "24H"
            trading_timezone = "UTC"
            automatic_exit_allowed = True
            automatic_exit_block_reason = None
            automatic_exit_guard_minutes = None
        elif quote.raw_payload.get("mt5ScheduleTracked") is True:
            settings = get_settings()
            session_state = resolve_mt5_session_state(
                schedule=settings.cross_spread_mt5_trading_schedule,
                timezone=settings.cross_spread_mt5_schedule_timezone,
                guard_minutes=settings.cross_spread_auto_exit_guard_minutes,
                overrides=settings.cross_spread_mt5_session_overrides,
            )
            market_status = session_state.status
            trading_hours = session_state.trading_hours
            trading_timezone = session_state.timezone
            automatic_exit_allowed = session_state.automatic_exit_allowed
            automatic_exit_block_reason = session_state.automatic_exit_block_reason
            automatic_exit_guard_minutes = session_state.guard_minutes
            if not session_state.manual_execution_allowed:
                open_allowed = False
                close_allowed = False
                block_reason = session_state.automatic_exit_block_reason
        else:
            # Simulation adapters do not carry a broker session calendar. Keep
            # their legacy capability semantics while making the missing
            # production evidence visible to callers.
            market_status = "unknown"
            trading_hours = None
            trading_timezone = None
            automatic_exit_allowed = True
            automatic_exit_block_reason = None
            automatic_exit_guard_minutes = None
        result = CrossSpreadVenueSnapshot(
            venue=venue,
            symbol=quote.symbol,
            status="available",
            quote=MarketQuote(
                bid=quote.bid,
                ask=quote.ask,
                mid=quote.mid,
                last=quote.last,
                currency=quote.currency,
            ),
            positions=positions,
            reason=";".join(reasons) or None,
            asOf=quote.as_of,
            openAllowed=open_allowed,
            closeAllowed=close_allowed,
            executionBlockReason=block_reason,
            marketStatus=market_status,
            tradingHours=trading_hours,
            tradingTimezone=trading_timezone,
            automaticExitAllowed=automatic_exit_allowed,
            automaticExitBlockReason=automatic_exit_block_reason,
            automaticExitGuardMinutes=automatic_exit_guard_minutes,
            quoteSourceAsOf=quote.source_as_of,
        )
    except Exception as exc:
        market_status = "unknown"
        trading_hours = None
        trading_timezone = None
        automatic_exit_allowed = False
        automatic_exit_block_reason = "mt5_session_state_unknown" if venue == "mt5" else None
        automatic_exit_guard_minutes = None
        if venue == "mt5":
            settings = get_settings()
            session_state = resolve_mt5_session_state(
                schedule=settings.cross_spread_mt5_trading_schedule,
                timezone=settings.cross_spread_mt5_schedule_timezone,
                guard_minutes=settings.cross_spread_auto_exit_guard_minutes,
                overrides=settings.cross_spread_mt5_session_overrides,
            )
            market_status = session_state.status
            trading_hours = session_state.trading_hours
            trading_timezone = session_state.timezone
            automatic_exit_guard_minutes = session_state.guard_minutes
            automatic_exit_block_reason = session_state.automatic_exit_block_reason
        result = CrossSpreadVenueSnapshot(
            venue=venue,
            symbol=symbol,
            status="unavailable",
            reason=redact_text(str(exc)),
            marketStatus=market_status,
            tradingHours=trading_hours,
            tradingTimezone=trading_timezone,
            automaticExitAllowed=automatic_exit_allowed,
            automaticExitBlockReason=automatic_exit_block_reason,
            automaticExitGuardMinutes=automatic_exit_guard_minutes,
            asOf=datetime.now(UTC),
        )
    return result.model_copy(
        update={"fetch_latency_ms": round((time.perf_counter() - started) * 1000, 1)}
    )


def _fetch_usdt_usd(gateway: VenueGateway, account_id: str) -> Decimal | None:
    try:
        for balance in gateway.list_balances(account_id):
            if balance.account_id != account_id:
                raise ValueError("Balance account identity mismatch")
            if balance.currency == "USDT" and balance.equity > 0:
                if balance.usd_value is not None and balance.usd_value > 0:
                    return balance.usd_value / balance.equity
    except Exception:
        return None
    return None


def _extract_reason_value(reason: str | None, key: str) -> Decimal | None:
    prefix = f"{key}="
    for part in (reason or "").split(";"):
        if part.startswith(prefix):
            return Decimal(part.removeprefix(prefix))
    return None


def _execution_capability(venue: str, quote) -> tuple[bool, bool, str | None]:
    """Derive write readiness from native source evidence while retaining quotes."""
    now = datetime.now(UTC)
    source_time = quote.source_as_of
    if source_time is None:
        return False, False, "quote_source_time_missing"
    if source_time.tzinfo is None or source_time.utcoffset() is None:
        return False, False, "quote_source_time_missing"
    quote_observed_at = quote.as_of
    if quote_observed_at.tzinfo is None or quote_observed_at.utcoffset() is None:
        return False, False, "quote_source_time_missing"
    payload = quote.raw_payload
    if venue == "mt5" and payload.get("tickFreshnessTracked") is True:
        quote_age = (now - quote_observed_at).total_seconds()
        if quote_age < 0 or quote_age > _MAX_SOURCE_AGE_SECONDS:
            return False, False, "quote_stale"
        observed_raw = payload.get("lastTickAdvanceObservedAt")
        if not isinstance(observed_raw, str):
            return False, False, "quote_stale"
        try:
            observed_at = datetime.fromisoformat(observed_raw)
        except ValueError:
            return False, False, "quote_stale"
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            return False, False, "quote_stale"
        advance_age = (now - observed_at).total_seconds()
        if advance_age < 0 or advance_age > _MAX_SOURCE_AGE_SECONDS:
            return False, False, "quote_stale"
    else:
        age = (now - source_time).total_seconds()
        if age < 0 or age > _MAX_SOURCE_AGE_SECONDS:
            return False, False, "quote_stale"
    if venue == "bybit":
        return True, True, None
    account_allowed = payload.get("accountTradeAllowed")
    terminal_allowed = payload.get("terminalTradeAllowed")
    trade_mode = payload.get("tradeMode")
    if account_allowed is not True:
        return False, False, "mt5_trade_not_allowed"
    if payload.get("accountExpertTradeAllowed") is not True:
        return False, False, "mt5_expert_trade_not_allowed"
    if payload.get("pythonTradeAllowed") is not True:
        return False, False, "mt5_python_trade_not_allowed"
    if payload.get("symbolVisible") is not True:
        return False, False, "mt5_symbol_not_visible"
    if terminal_allowed is not True:
        return False, False, "mt5_terminal_trade_not_allowed"
    try:
        mode = int(trade_mode)
    except (TypeError, ValueError):
        return False, False, "mt5_trade_mode_unknown"
    if mode == 0:
        return False, False, "mt5_symbol_disabled"
    if mode != 4:
        return False, mode == 3, "mt5_symbol_not_full_trade"
    return True, True, None


def estimate_cached_fill_price(*, symbol: str, side: str) -> Decimal | None:
    # Simulation-only price estimation. Live order/fill evidence never uses this cache.
    for _, snapshot in sorted(
        list(_SNAPSHOT_CACHE.values()), key=lambda item: item[0], reverse=True
    ):
        for venue in (snapshot.bybit, snapshot.mt5):
            if venue.symbol.upper() != symbol.upper() or venue.quote is None:
                continue
            if side.lower() == "buy":
                return venue.quote.ask
            if side.lower() == "sell":
                return venue.quote.bid
    return None
