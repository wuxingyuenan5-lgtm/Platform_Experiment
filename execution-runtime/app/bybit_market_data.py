"""CCXT market normalization over the existing account-owned Bybit connection.

Only public market reads are admitted here. CCXT owns the market identity,
precision/limit parsing and pagination; the account adapter owns transport,
credentials, time synchronization and read recovery. This avoids a second SDK
connection/rate budget while the private execution extension remains in pybit.
"""

from collections.abc import Callable
from threading import RLock
from time import monotonic
from typing import Any

from app.gateway_errors import GatewayConfigurationError


class BybitMarketData:
    def __init__(self, read: Callable[..., dict[str, Any]]) -> None:
        self._read = read
        self._lock = RLock()
        self._markets: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
        self._exchange: Any = None
        self._page_requests: set[tuple] = set()

    def _ccxt(self):
        if self._exchange is None:
            try:
                import ccxt
            except ImportError as exc:
                raise GatewayConfigurationError(
                    "ccxt market-data dependency is not installed"
                ) from exc
            self._exchange = ccxt.bybit({"enableRateLimit": False})
            self._exchange.number = str
            # CCXT is used through its public read interface. All I/O is delegated
            # to the same account connection; its unused Session never connects.
            self._exchange.request = self._request
        return self._exchange

    def _request(self, path, api="public", method="GET", params=None, **_kwargs):
        if api != "public" or method != "GET" or path != "v5/market/instruments-info":
            raise GatewayConfigurationError("CCXT market reader cannot issue this request")
        params = params or {}
        identity = tuple(sorted(params.items()))
        if identity in self._page_requests or len(self._page_requests) >= 100:
            raise GatewayConfigurationError("Bybit market pagination did not converge")
        self._page_requests.add(identity)
        response = self._read("get_instruments_info", **params)
        if response.get("result", {}).get("category") != params.get("category"):
            raise GatewayConfigurationError("Bybit market response category mismatch")
        return response

    def market(self, category: str, symbol: str) -> dict[str, Any]:
        key = category, symbol.upper()
        with self._lock:
            cached = self._markets.get(key)
            if cached is not None and monotonic() - cached[0] < 60:
                return cached[1]
            exchange = self._ccxt()
            self._page_requests.clear()
            params = {"category": category, "symbol": key[1]}
            if category == "spot":
                markets = exchange.fetch_spot_markets(params)
            elif category in {"linear", "inverse"}:
                markets = exchange.fetch_future_markets(params)
            else:
                raise GatewayConfigurationError("Unsupported Bybit market category")
            candidates = [market for market in markets if market["id"] == key[1]]
            if not candidates:
                raise GatewayConfigurationError(
                    "Bybit instrument query returned no matching market"
                )
            market = candidates[0]
            if not market.get("base") or not market.get("quote") or not market.get("symbol"):
                raise GatewayConfigurationError("Bybit market currency identity is incomplete")
            if category != "spot" and not market.get("swap"):
                raise GatewayConfigurationError("Bybit strategy requires a perpetual instrument")
            self._markets[key] = monotonic(), market
            return market

    def ticker(self, category: str, symbol: str) -> tuple[dict, dict, dict, dict]:
        with self._lock:
            market = self.market(category, symbol)
            response = self._read("get_tickers", category=category, symbol=symbol)
            if response.get("result", {}).get("category") != category:
                raise GatewayConfigurationError("Bybit ticker response category mismatch")
            rows = response.get("result", {}).get("list", [])
            row = next((row for row in rows if row.get("symbol") == symbol), None)
            if row is None:
                raise GatewayConfigurationError("Bybit ticker query returned no matching symbol")
            exchange = self._ccxt()
            ticker = exchange.parse_ticker(row, market)
            funding = exchange.parse_funding_rate(row, market) if category != "spot" else {}
            return market, ticker, funding, response

    def close(self) -> None:
        with self._lock:
            if self._exchange is not None:
                self._exchange.session.close()
                self._exchange = None
            self._markets.clear()
