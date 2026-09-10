"""Account-owned pybit connections with a shared CCXT request budget."""

from threading import Lock, RLock
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings
from app.gateway_errors import GatewayConfigurationError
from app.operational_metrics import VENUE_REQUEST_SECONDS
from app.secret_resolver import resolve_secret_reference

_ip_lock = Lock()
_ip_budget: Any = None


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
        offset_ms = int(self.settings.bybit_timestamp_offset_ms or 0)
        if offset_ms == 0:
            try:
                response = client.get_server_time()
                server_ms = int(response.get("time") or 0)
                if response.get("retCode") != 0 or server_ms <= 0:
                    raise ValueError("Bybit server time is unavailable")
                offset_ms = server_ms - int(original())
            except Exception as exc:
                raise GatewayConfigurationError(
                    f"Bybit server-time synchronization failed: {type(exc).__name__}"
                ) from exc
        if abs(offset_ms) > 60_000:
            raise GatewayConfigurationError("Bybit server-time offset exceeds safety limit")
        helpers.generate_timestamp = lambda: original() + offset_ms

    def close(self) -> None:
        with self._lock:
            for client in self._clients.values():
                client.client.close()
            self._clients.clear()
