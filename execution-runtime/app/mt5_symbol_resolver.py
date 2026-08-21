"""Resolve the actual MT5 symbol name for a logical gold symbol.

MT5 broker servers name the same product differently (``XAUUSD``, ``XAUUSD.s``,
``XAUUSD+``, ``XAUUSD.a`` ...).  Hard-coding one name breaks when the server or
account changes, so this module resolves the concrete symbol at runtime:

1. An explicit preferred symbol (from ``MT5_INSTRUMENT_MAP`` / ``mt5_symbol``)
   is used first when it is selectable and has a live tick.
2. Otherwise all symbols containing the base name (e.g. ``XAUUSD``) are
   enumerated and ranked: exact match, then ``.s``, then ``+``, then any other
   variant.
3. Only candidates that ``symbol_select`` and expose a non-zero bid/ask tick
   are accepted.

The resolution is cached per (login, server) so repeated snapshots do not
re-enumerate the terminal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Process-local cache: (login, server) -> resolution. Keyed by account identity
# because the same terminal process can switch servers/accounts.
_symbol_cache: dict[tuple[str, str], "Mt5SymbolResolution"] = {}


@dataclass(frozen=True)
class Mt5SymbolResolution:
    symbol: str
    matched_by: str  # "explicit" | "exact" | "dot_s" | "plus" | "variant"
    reason: str | None = None


def clear_mt5_symbol_cache() -> None:
    """Clear the process-local resolution cache (tests / server switch)."""
    _symbol_cache.clear()


def _candidate_rank(symbol: str, base: str) -> int:
    """Lower rank wins. Exact base match is best, then '.s', then '+', then others."""
    upper = symbol.upper()
    base_upper = base.upper()
    if upper == base_upper:
        return 0
    if upper == f"{base_upper}.S":
        return 1
    if upper == f"{base_upper}+":
        return 2
    return 3


def _has_live_tick(mt5_module: Any, symbol: str) -> bool:
    select = getattr(mt5_module, "symbol_select", None)
    if callable(select):
        try:
            select(symbol, True)
        except Exception:
            return False
    try:
        tick = mt5_module.symbol_info_tick(symbol)
    except Exception:
        return False
    if tick is None:
        return False
    bid = getattr(tick, "bid", 0)
    ask = getattr(tick, "ask", 0)
    try:
        return float(bid) > 0 and float(ask) > 0
    except (TypeError, ValueError):
        return False


def resolve_mt5_symbol(
    *,
    mt5_module: Any,
    base_symbol: str,
    preferred: str | None = None,
    require_tick: bool = True,
    cache_key: tuple[str, str] | None = None,
) -> Mt5SymbolResolution | None:
    """Resolve the concrete MT5 symbol for ``base_symbol``.

    ``preferred`` wins when it is selectable and (optionally) has a live tick.
    Otherwise symbols are enumerated and ranked.  ``cache_key`` should be
    ``(login, server)`` to reuse the result across snapshot polls.
    """
    if cache_key is not None and cache_key in _symbol_cache:
        cached = _symbol_cache[cache_key]
        if require_tick:
            if not _has_live_tick(mt5_module, cached.symbol):
                # Stale or dead symbol: drop cache and re-resolve.
                del _symbol_cache[cache_key]
            else:
                return cached
        else:
            return cached

    resolution = _resolve_uncached(
        mt5_module=mt5_module,
        base_symbol=base_symbol,
        preferred=preferred,
        require_tick=require_tick,
    )
    if resolution is not None and cache_key is not None:
        _symbol_cache[cache_key] = resolution
    return resolution


def _resolve_uncached(
    *,
    mt5_module: Any,
    base_symbol: str,
    preferred: str | None,
    require_tick: bool,
) -> Mt5SymbolResolution | None:
    if preferred:
        try:
            if _has_live_tick(mt5_module, preferred):
                return Mt5SymbolResolution(
                    symbol=preferred,
                    matched_by="explicit",
                    reason=f"explicit preferred symbol {preferred} has a live tick",
                )
        except Exception:
            pass

    try:
        symbols = mt5_module.symbols_get()
    except Exception:
        return None
    if not symbols:
        return None

    candidates = [
        getattr(item, "name", None)
        for item in symbols
        if getattr(item, "name", None)
    ]
    base_upper = base_symbol.upper()
    matching = [
        name
        for name in candidates
        if base_upper in str(name).upper()
    ]
    matching.sort(key=lambda name: (_candidate_rank(name, base_upper), str(name)))
    for candidate in matching:
        if require_tick and not _has_live_tick(mt5_module, candidate):
            continue
        rank = _candidate_rank(candidate, base_upper)
        matched_by = ("exact", "dot_s", "plus", "variant")[rank]
        return Mt5SymbolResolution(
            symbol=candidate,
            matched_by=matched_by,
            reason=f"auto-resolved {candidate} (rank={matched_by})",
        )
    return None
