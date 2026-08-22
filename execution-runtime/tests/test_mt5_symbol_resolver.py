"""Tests for MT5 symbol resolution (auto-discovery of the concrete broker name)."""

from __future__ import annotations

from dataclasses import dataclass

from app.mt5_symbol_resolver import (
    clear_mt5_symbol_cache,
    resolve_mt5_symbol,
)


@dataclass
class _Tick:
    bid: float
    ask: float


@dataclass
class _Symbol:
    name: str


class _FakeMt5:
    def __init__(self, symbols: list[str], tick_map: dict[str, _Tick] | None = None) -> None:
        self._symbols = symbols
        self._tick_map = tick_map or {}
        self.selected: list[str] = []

    def symbols_get(self) -> list[_Symbol]:
        return [_Symbol(name=name) for name in self._symbols]

    def symbol_select(self, symbol: str, enabled: bool) -> bool:
        self.selected.append(symbol)
        return symbol in self._symbols

    def symbol_info_tick(self, symbol: str) -> _Tick | None:
        return self._tick_map.get(symbol)


def _live(*names: str) -> dict[str, _Tick]:
    return {name: _Tick(bid=4000.0, ask=4001.0) for name in names}


def test_explicit_preferred_wins() -> None:
    clear_mt5_symbol_cache()
    mt5 = _FakeMt5(
        ["XAUUSD.s", "XAUUSD+"],
        _live("XAUUSD.s", "XAUUSD+"),
    )
    result = resolve_mt5_symbol(
        mt5_module=mt5,
        base_symbol="XAUUSD",
        preferred="XAUUSD.s",
    )
    assert result is not None
    assert result.symbol == "XAUUSD.s"
    assert result.matched_by == "explicit"


def test_auto_resolve_dot_s_preferred_over_plus() -> None:
    clear_mt5_symbol_cache()
    mt5 = _FakeMt5(
        ["XAUUSD+", "XAUUSD.s", "XAUAUD.s"],
        _live("XAUUSD+", "XAUUSD.s"),
    )
    result = resolve_mt5_symbol(mt5_module=mt5, base_symbol="XAUUSD")
    assert result is not None
    assert result.symbol == "XAUUSD.s"
    assert result.matched_by == "dot_s"


def test_auto_resolve_plus_when_only_plus_has_tick() -> None:
    clear_mt5_symbol_cache()
    mt5 = _FakeMt5(
        ["XAUUSD.s", "XAUUSD+"],
        _live("XAUUSD+"),
    )
    result = resolve_mt5_symbol(mt5_module=mt5, base_symbol="XAUUSD")
    assert result is not None
    assert result.symbol == "XAUUSD+"
    assert result.matched_by == "plus"


def test_auto_resolve_exact_base_wins() -> None:
    clear_mt5_symbol_cache()
    mt5 = _FakeMt5(
        ["XAUUSD", "XAUUSD.s"],
        _live("XAUUSD", "XAUUSD.s"),
    )
    result = resolve_mt5_symbol(mt5_module=mt5, base_symbol="XAUUSD")
    assert result is not None
    assert result.symbol == "XAUUSD"
    assert result.matched_by == "exact"


def test_no_tick_returns_none() -> None:
    clear_mt5_symbol_cache()
    mt5 = _FakeMt5(["XAUUSD.s"])  # no live tick
    result = resolve_mt5_symbol(mt5_module=mt5, base_symbol="XAUUSD")
    assert result is None


def test_missing_base_returns_none() -> None:
    clear_mt5_symbol_cache()
    mt5 = _FakeMt5(["EURUSD"], _live("EURUSD"))
    result = resolve_mt5_symbol(mt5_module=mt5, base_symbol="XAUUSD")
    assert result is None


def test_cache_key_avoids_re_enumeration() -> None:
    clear_mt5_symbol_cache()
    mt5 = _FakeMt5(["XAUUSD.s"], _live("XAUUSD.s"))
    first = resolve_mt5_symbol(
        mt5_module=mt5,
        base_symbol="XAUUSD",
        cache_key=("100", "Bybit-Live-2"),
    )
    assert first is not None
    assert first.symbol == "XAUUSD.s"
    # Second call with same key should hit cache without touching the terminal.
    second = resolve_mt5_symbol(
        mt5_module=mt5,
        base_symbol="XAUUSD",
        cache_key=("100", "Bybit-Live-2"),
    )
    assert second is not None
    assert second.symbol == "XAUUSD.s"


def test_logical_suffix_strip() -> None:
    from app.mt5_live_adapter import _logical_mt5_symbol

    assert _logical_mt5_symbol("XAUUSD.s") == "XAUUSD"
    assert _logical_mt5_symbol("XAUUSD+") == "XAUUSD"
    assert _logical_mt5_symbol("XAUUSD") == "XAUUSD"
    assert _logical_mt5_symbol("XAUAUD.s") == "XAUAUD"
    assert _logical_mt5_symbol("GOLD.custom") == "GOLD.custom"
