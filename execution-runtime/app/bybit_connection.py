"""Account-owned pybit connections with a shared CCXT request budget."""

from threading import Lock, RLock
from time import monotonic, perf_counter
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings
from app.gateway_errors import GatewayConfigurationError
from app.operational_metrics import VENUE_REQUEST_SECONDS
from app.secret_resolver import resolve_secret_reference

_ip_lock = Lock()
_ip_budget: Any = None
_clock_lock = RLock()
_clock_offset_ms = 0
_clock_calibrated_at = 0.0
_clock_refreshing = False
_CLOCK_REFRESH_SECONDS = 60.0


def _new_budget() -> Any:
    import ccxt

    # Use CCXT's maintained Bybit endpoint costs and throttle implementation.
    budget: Any = ccxt.bybit()
    budget.number = str
    if budget.session is not None:
        budget.session.close()  # This instance owns timing/metadata, never network I/O.
    return budget


def _reserve_ip_request() -> None:
    global _ip_budget
    with _ip_lock:
        if _ip_budget is None:
            _ip_budget = _new_budget()
        _ip_budget.throttle(1)
        _ip_budget.lastRestRequestTimestamp = _ip_budget.milliseconds()


def _managed_session():
    import requests

    class BybitSession(requests.Session):
        def __init__(self):
            super().__init__()
            self._budget_lock = Lock()
            self._budget = _new_budget()

        def send(self, request: requests.PreparedRequest, **kwargs):
            if request.url is None or request.method is None:
                raise ValueError("Bybit request is not prepared")
            path = urlsplit(request.url).path.lstrip("/")
            api = "public" if path.startswith("v5/market/") else "private"
            method = request.method.lower()
            config = self._budget.api.get(api, {}).get(method, {}).get(path, {"cost": 5})
            cost = config.get("cost", 5) if isinstance(config, dict) else config
            with self._budget_lock:
                self._budget.throttle(cost)
                _reserve_ip_request()
                self._budget.lastRestRequestTimestamp = self._budget.milliseconds()
            # requests defaults to no adapter retry. Reject redirect replay too;
            # private signatures and business writes are for this exact URL.
            kwargs["allow_redirects"] = False
            known_paths = {
                "v5/market/time", "v5/market/tickers", "v5/market/instruments-info",
                "v5/order/create", "v5/order/cancel", "v5/order/realtime", "v5/order/history",
                "v5/execution/list", "v5/position/list", "v5/position/set-leverage",
                "v5/account/wallet-balance", "v5/account/transaction-log", "v5/account/info",
            }
            operation = path if path in known_paths else "other"
            started = perf_counter()
            outcome = "error"
            try:
                response = super().send(request, **kwargs)
                outcome = f"http_{response.status_code // 100}xx"
                if response.status_code == 429:
                    outcome = "rate_limited"
                elif response.status_code == 200:
                    try:
                        code = response.json().get("retCode")
                    except (ValueError, AttributeError):
                        outcome = "invalid_response"
                    else:
                        if code in (10006, 10018):
                            outcome = "rate_limited"
                        elif code not in (0, None):
                            outcome = "venue_rejected"
                return response
            except requests.Timeout:
                outcome = "timeout"
                raise
            except requests.ConnectionError:
                outcome = "transport_error"
                raise
            finally:
                VENUE_REQUEST_SECONDS.labels("bybit", operation, outcome).observe(
                    perf_counter() - started
                )

    return BybitSession()


class BybitConnections:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = RLock()
        self._clients: dict[str, Any] = {}
        self._research_sockets: list[Any] = []
        self._research_lock = Lock()

    def client(self, account_id: str) -> Any:
        with self._lock:
            if account_id in self._clients:
                return self._clients[account_id]
            if account_id not in self.settings.bybit_accounts:
                raise GatewayConfigurationError("Account is not mapped to Bybit")
            try:
                from pybit import _helpers
                from pybit.unified_trading import HTTP
            except ImportError as exc:
                raise GatewayConfigurationError("pybit dependency is not installed") from exc
            try:
                secret = resolve_secret_reference(
                    self.settings.bybit_credential_for_account(account_id),
                    required_fields=("API_KEY", "SECRET"),
                )
            except ValueError as exc:
                raise GatewayConfigurationError(str(exc)) from exc
            client = HTTP(
                testnet=False,
                demo=False,
                api_key=secret["API_KEY"],
                api_secret=secret["SECRET"],
                recv_window=self.settings.bybit_recv_window,
                force_retry=False,
                max_retries=1,
            )
            session = _managed_session()
            session.headers.update(client.client.headers)
            client.client.close()
            client.client = session
            try:
                self._sync_clock(_helpers, client)
            except Exception:
                session.close()
                raise
            self._clients[account_id] = client
            return client

    def _sync_clock(self, helpers, client) -> None:
        original = getattr(helpers, "_vg_original_generate_timestamp", None)
        if original is None:
            original = helpers.generate_timestamp
            helpers._vg_original_generate_timestamp = original
        configured_offset_ms = int(self.settings.bybit_timestamp_offset_ms or 0)
        auto_sync = configured_offset_ms == 0
        offset_ms = configured_offset_ms
        if auto_sync:
            offset_ms = self._measure_clock_offset(original, client)
        if abs(offset_ms) > 60_000:
            raise GatewayConfigurationError("Bybit server-time offset exceeds safety limit")
        with _clock_lock:
            global _clock_offset_ms, _clock_calibrated_at
            _clock_offset_ms = offset_ms
            _clock_calibrated_at = monotonic()

        # pybit keeps the timestamp helper at module scope. Install one wrapper
        # that shares a calibrated offset across account clients and refreshes it
        # periodically. A one-time startup sample is unsafe on hosts whose clock
        # drifts during a long-running monitor process.
        helpers.generate_timestamp = lambda: self._timestamp(
            original, client, auto_sync=auto_sync
        )

    @staticmethod
    def _measure_clock_offset(original, client) -> int:
        try:
            response = client.get_server_time()
            after = int(original())
            server_ms = int(response.get("time") or 0)
            if response.get("retCode") != 0 or server_ms <= 0:
                raise ValueError("Bybit server time is unavailable")
            # The venue timestamp is produced before the response reaches us.
            # Using the latest local sample is deliberately conservative: it
            # can leave a request a little behind the venue, but it cannot push
            # an authenticated request over Bybit's strict +1000 ms bound when
            # the proxy/network path is asymmetric.
            return server_ms - after
        except Exception as exc:
            raise GatewayConfigurationError(
                f"Bybit server-time synchronization failed: {type(exc).__name__}"
            ) from exc

    @classmethod
    def _timestamp(cls, original, client, *, auto_sync: bool = True) -> int:
        global _clock_offset_ms, _clock_calibrated_at, _clock_refreshing
        should_refresh = False
        with _clock_lock:
            stale = auto_sync and monotonic() - _clock_calibrated_at >= _CLOCK_REFRESH_SECONDS
            if stale and not _clock_refreshing:
                _clock_refreshing = True
                should_refresh = True
        if should_refresh:
            try:
                offset = cls._measure_clock_offset(original, client)
                if abs(offset) <= 60_000:
                    with _clock_lock:
                        _clock_offset_ms = offset
                        _clock_calibrated_at = monotonic()
            except GatewayConfigurationError:
                # Keep the last verified offset when the public clock is
                # temporarily unreachable. The signed request still fails
                # closed if the venue rejects it, and the next timestamp retries.
                pass
            finally:
                with _clock_lock:
                    _clock_refreshing = False
        with _clock_lock:
            offset = _clock_offset_ms
        return int(original()) + offset

    def start_research_streams(self, capture) -> None:
        from pybit.unified_trading import WebSocket

        class RawPublicSocket(WebSocket):
            # pybit's normal callback rewrites delta into a synthetic snapshot.
            # This dedicated PUBLIC socket forwards the native message before that merge.
            def _process_normal_message(ws, message):
                topic = message["topic"]
                capture("bybit_message", f"bybit:{ws.research_category}:{topic}", "public",
                        message, source_ms=message.get("cts", message.get("ts")),
                        source_layer="native_websocket")

            def _on_open(ws):
                capture("quality", f"bybit:{ws.research_category}", "public",
                        {"reason": "connected_wait_snapshot"}, quality=["book_unsynced"])
                super()._on_open()

            def _on_close(ws):
                capture("quality", f"bybit:{ws.research_category}", "public",
                        {"reason": "disconnected"}, quality=["source_gap"])
                super()._on_close()

        with self._research_lock:
            if self._research_sockets:
                return
            for category, symbols in (("linear", ["XAUTUSDT", "BTCUSDT"]), ("spot", ["BTCUSDT"])):
                # _on_open may run during construction, so category belongs to a per-socket class.
                Socket = type(
                    "ResearchPublicSocket", (RawPublicSocket,), {"research_category": category}
                )
                ws = None
                try:
                    ws = Socket(channel_type=category, testnet=False, retries=3)
                    ws.orderbook_stream(depth=50, symbol=symbols, callback=lambda _: None)
                    if category == "linear":
                        ws.ticker_stream(symbol=symbols, callback=lambda _: None)
                    self._research_sockets.append(ws)
                except Exception:
                    if ws is not None:
                        ws.exit()
                    for existing in self._research_sockets:
                        existing.exit()
                    self._research_sockets.clear()
                    raise

    def close(self) -> None:
        for socket in self._research_sockets:
            socket.exit()
        self._research_sockets.clear()
        with self._lock:
            for client in self._clients.values():
                client.client.close()
            self._clients.clear()

    def reset(self, account_id: str) -> None:
        """Discard a transport session after a connection reset.

        Requests can leave a pooled TLS connection unusable after a remote
        reset (Windows reports this as ConnectionResetError/10054). Reusing
        that session makes every background read fail even though credentials
        and the venue are still valid.
        """
        with self._lock:
            client = self._clients.pop(account_id, None)
            if client is not None:
                client.client.close()
