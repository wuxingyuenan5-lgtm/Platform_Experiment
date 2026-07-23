from __future__ import annotations

import os
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable

from app.models import VenueReadinessResult, VenueReadinessResponse
from app.secret_resolver import env_prefix_for_secret_ref


def check_bybit_contract(
    *,
    credential_ref: str,
    symbol: str,
    demo: bool = False,
    recv_window: int = 20000,
    timeout_seconds: float = 8.0,
    session_factory: Callable[..., Any] | None = None,
) -> VenueReadinessResult:
    env_prefix = env_prefix_for_secret_ref(credential_ref)
    api_key = os.getenv(f"{env_prefix}_API_KEY")
    api_secret = os.getenv(f"{env_prefix}_SECRET")
    if not api_key or not api_secret:
        return _venue_result(
            venue="bybit",
            status="missing_credentials",
            credential_ref=credential_ref,
            symbol=symbol,
            market_type="linear",
            reason="Bybit API_KEY and SECRET are required",
        )

    if session_factory is None:
        try:
            from pybit.unified_trading import HTTP
        except ImportError:
            return _venue_result(
                venue="bybit",
                status="sdk_missing",
                credential_ref=credential_ref,
                symbol=symbol,
                market_type="linear",
                reason="pybit is not installed",
            )
        session_factory = HTTP

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        _check_bybit_contract_blocking,
        session_factory,
        api_key,
        api_secret,
        demo,
        recv_window,
        credential_ref,
        symbol,
    )
    try:
        return future.result(timeout=timeout_seconds)
    except TimeoutError:
        executor.shutdown(wait=False, cancel_futures=True)
        return _venue_result(
            venue="bybit",
            status="timeout",
            credential_ref=credential_ref,
            symbol=symbol,
            market_type="linear",
            reason=f"Bybit check timed out after {timeout_seconds:g}s",
        )
    except Exception as exc:
        executor.shutdown(wait=False, cancel_futures=True)
        return _venue_result(
            venue="bybit",
            status="unavailable",
            credential_ref=credential_ref,
            symbol=symbol,
            market_type="linear",
            reason=str(exc),
        )
    finally:
        if future.done():
            executor.shutdown(wait=False)


def _check_bybit_contract_blocking(
    session_factory: Callable[..., Any],
    api_key: str,
    api_secret: str,
    demo: bool,
    recv_window: int,
    credential_ref: str,
    symbol: str,
) -> VenueReadinessResult:
    session = session_factory(
        testnet=False,
        demo=demo,
        recv_window=recv_window,
        api_key=api_key,
        api_secret=api_secret,
    )
    wallet = session.get_wallet_balance(accountType="UNIFIED")
    if wallet.get("retCode") != 0:
        return _venue_result(
            venue="bybit",
            status="unavailable",
            credential_ref=credential_ref,
            symbol=symbol,
            market_type="linear",
            checks=["ticker"],
            reason=str(wallet.get("retMsg") or "wallet check failed"),
        )
    ticker = session.get_tickers(category="linear", symbol=symbol)
    if ticker.get("retCode") != 0:
        return _venue_result(
            venue="bybit",
            status="unavailable",
            credential_ref=credential_ref,
            symbol=symbol,
            market_type="linear",
            checks=["wallet"],
            reason=str(ticker.get("retMsg") or "ticker check failed"),
        )

    return _venue_result(
        venue="bybit",
        status="available",
        credential_ref=credential_ref,
        symbol=symbol,
        market_type="linear",
        checks=["ticker", "wallet"],
    )


def check_mt5_symbol(
    *,
    credential_ref: str,
    symbol: str,
    terminal_path: str | None = None,
    mt5_module: Any | None = None,
    timeout_seconds: float = 5.0,
) -> VenueReadinessResult:
    env_prefix = env_prefix_for_secret_ref(credential_ref)
    login = os.getenv(f"{env_prefix}_API_KEY")
    password = os.getenv(f"{env_prefix}_SECRET")
    server = os.getenv(f"{env_prefix}_PASSPHRASE")
    if not login or not password or not server:
        return _venue_result(
            venue="mt5",
            status="missing_credentials",
            credential_ref=credential_ref,
            symbol=symbol,
            reason="MT5 login, password and server are required",
        )

    if mt5_module is None:
        try:
            import MetaTrader5  # noqa: F401
        except ImportError:
            return _venue_result(
                venue="mt5",
                status="sdk_missing",
                credential_ref=credential_ref,
                symbol=symbol,
                reason="MetaTrader5 Python package is not installed",
            )
        return _check_mt5_symbol_subprocess(
            credential_ref=credential_ref,
            symbol=symbol,
            terminal_path=terminal_path,
            timeout_seconds=timeout_seconds,
        )

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        _check_mt5_symbol_blocking,
        mt5_module,
        int(login),
        password,
        server,
        terminal_path,
        credential_ref,
        symbol,
    )
    try:
        return future.result(timeout=timeout_seconds)
    except TimeoutError:
        executor.shutdown(wait=False, cancel_futures=True)
        return _venue_result(
            venue="mt5",
            status="timeout",
            credential_ref=credential_ref,
            symbol=symbol,
            reason=f"MT5 check timed out after {timeout_seconds:g}s",
        )
    except Exception as exc:
        executor.shutdown(wait=False, cancel_futures=True)
        return _venue_result(
            venue="mt5",
            status="unavailable",
            credential_ref=credential_ref,
            symbol=symbol,
            reason=str(exc),
        )
    finally:
        if future.done():
            executor.shutdown(wait=False)


def _check_mt5_symbol_blocking(
    mt5_module: Any,
    login: int,
    password: str,
    server: str,
    terminal_path: str | None,
    credential_ref: str,
    symbol: str,
) -> VenueReadinessResult:
    try:
        init_kwargs = {"login": login, "password": password, "server": server}
        if terminal_path:
            init_kwargs["path"] = terminal_path
        if not mt5_module.initialize(**init_kwargs):
            return _venue_result(
                venue="mt5",
                status="unavailable",
                credential_ref=credential_ref,
                symbol=symbol,
                reason="MT5 initialize failed",
            )
        symbol_info = mt5_module.symbol_info(symbol)
        if symbol_info is None:
            return _venue_result(
                venue="mt5",
                status="unavailable",
                credential_ref=credential_ref,
                symbol=symbol,
                checks=["login"],
                reason=f"MT5 symbol not found: {symbol}",
            )
    except Exception as exc:
        return _venue_result(
            venue="mt5",
            status="unavailable",
            credential_ref=credential_ref,
            symbol=symbol,
            reason=str(exc),
        )
    finally:
        shutdown = getattr(mt5_module, "shutdown", None)
        if callable(shutdown):
            shutdown()

    return _venue_result(
        venue="mt5",
        status="available",
        credential_ref=credential_ref,
        symbol=symbol,
        checks=["login", "symbol"],
    )


def _check_mt5_symbol_subprocess(
    *,
    credential_ref: str,
    symbol: str,
    terminal_path: str | None,
    timeout_seconds: float,
) -> VenueReadinessResult:
    script = r"""
import json
import os
import sys

import MetaTrader5 as mt5

prefix = sys.argv[1]
symbol = sys.argv[2]
terminal_path = sys.argv[3] or None
login = os.getenv(f"{prefix}_API_KEY")
password = os.getenv(f"{prefix}_SECRET")
server = os.getenv(f"{prefix}_PASSPHRASE")

try:
    kwargs = {"login": int(login), "password": password, "server": server}
    if terminal_path:
        kwargs["path"] = terminal_path
    ok = mt5.initialize(**kwargs)
    if not ok:
        print(json.dumps({"status": "unavailable", "checks": [], "reason": "MT5 initialize failed"}))
        raise SystemExit(0)
    info = mt5.symbol_info(symbol)
    if info is None:
        print(json.dumps({"status": "unavailable", "checks": ["login"], "reason": f"MT5 symbol not found: {symbol}"}))
    else:
        print(json.dumps({"status": "available", "checks": ["login", "symbol"], "reason": None}))
finally:
    mt5.shutdown()
"""
    env_prefix = env_prefix_for_secret_ref(credential_ref)
    try:
        completed = subprocess.run(
            [sys.executable, "-c", script, env_prefix, symbol, terminal_path or ""],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _venue_result(
            venue="mt5",
            status="timeout",
            credential_ref=credential_ref,
            symbol=symbol,
            reason=f"MT5 check timed out after {timeout_seconds:g}s",
        )

    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        reason = completed.stderr.strip() or "MT5 subprocess returned no status"
        return _venue_result(
            venue="mt5",
            status="unavailable",
            credential_ref=credential_ref,
            symbol=symbol,
            reason=reason,
        )

    return _venue_result(
        venue="mt5",
        status=payload.get("status", "unavailable"),
        credential_ref=credential_ref,
        symbol=symbol,
        checks=payload.get("checks") or [],
        reason=payload.get("reason"),
    )


def get_venue_readiness(
    *,
    bybit_symbol: str,
    bybit_demo: bool,
    bybit_recv_window: int = 20000,
    bybit_timeout_seconds: float = 8.0,
    mt5_symbol: str,
    mt5_terminal_path: str | None = None,
    mt5_timeout_seconds: float = 5.0,
) -> VenueReadinessResponse:
    venues = [
        check_bybit_contract(
            credential_ref="secret://crypto-test-001",
            symbol=bybit_symbol,
            demo=bybit_demo,
            recv_window=bybit_recv_window,
            timeout_seconds=bybit_timeout_seconds,
        ),
        check_mt5_symbol(
            credential_ref="secret://mt5-demo-001",
            symbol=mt5_symbol,
            terminal_path=mt5_terminal_path,
            timeout_seconds=mt5_timeout_seconds,
        ),
    ]
    status = "available" if all(item.status == "available" for item in venues) else "partial"
    return VenueReadinessResponse(status=status, venues=venues)


def _venue_result(
    *,
    venue: str,
    status: str,
    credential_ref: str,
    symbol: str,
    market_type: str | None = None,
    checks: list[str] | None = None,
    reason: str | None = None,
) -> VenueReadinessResult:
    return VenueReadinessResult(
        venue=venue,
        status=status,
        credentialRef=credential_ref,
        symbol=symbol,
        marketType=market_type,
        checks=checks or [],
        reason=reason,
    )
