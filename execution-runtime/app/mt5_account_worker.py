from __future__ import annotations

import atexit
import logging
import multiprocessing
import time
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

from app.config import Settings
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.journal import has_unresolved_command_for_account
from app.mt5_connection import maintain_background_terminal
from app.operational_metrics import VENUE_REQUEST_SECONDS, WORKER_READY, WORKER_STARTS

_ERROR_TYPES = {
    "GatewayConfigurationError": GatewayConfigurationError,
    "GatewayRequestRejectedError": GatewayRequestRejectedError,
    "GatewayResultUnknownError": GatewayResultUnknownError,
}

_READ_METHODS = frozenset(
    {
        "capability",
        "get_account_risk",
        "get_account_snapshot",
        "get_instrument_specification",
        "get_market_quote",
        "get_research_ticks",
        "estimate_order_margin",
        "get_order",
        "list_balances",
        "list_economic_events",
        "get_capital_flows",
        "list_fills",
        "list_orders",
        "list_positions",
        "query_fill_history",
        "query_order_history",
    }
)
_WRITE_METHODS = frozenset({"cancel_order", "submit_order"})
_ALLOWED_METHODS = _READ_METHODS | _WRITE_METHODS


class Mt5AccountWorkerClient:
    """High-level RPC client for one immutable MT5 account process."""

    name = "mt5_live"

    def __init__(self, *, settings: Settings, account_id: str, terminal_path: str | None) -> None:
        self.settings = settings
        self.account_id = account_id
        self.terminal_path = terminal_path
        self._lock = Lock()
        self._process: multiprocessing.Process | None = None
        self._connection: Any | None = None
        self._write_frozen_command_id: str | None = None
        self._write_frozen_without_command = False
        self._startup_failures = 0
        self._startup_failed_at: float | None = None
        self._startup_failure: GatewayConfigurationError | None = None
        WORKER_READY.labels(self.account_id).set(0)

    def __getattr__(self, method: str):
        if method not in _ALLOWED_METHODS:
            raise AttributeError(method)

        def call(*args, **kwargs):
            started = perf_counter()
            outcome = "error"
            try:
                result = self._call(method, *args, **kwargs)
                outcome = "success"
                return result
            except GatewayResultUnknownError:
                outcome = "result_unknown"
                raise
            except GatewayConfigurationError:
                outcome = "configuration_error"
                raise
            except GatewayRequestRejectedError:
                outcome = "rejected"
                raise
            finally:
                VENUE_REQUEST_SECONDS.labels("mt5", method, outcome).observe(
                    perf_counter() - started
                )

        return call

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()

    def _call(self, method: str, *args, **kwargs):
        if method == "get_research_ticks" and (
            self._lock.locked() or self.settings.live_write_enabled
        ):
            raise GatewayConfigurationError("Research yielded to account operations")
        with self._lock:
            command_id = self._command_id(method, args)
            if method in _WRITE_METHODS:
                self._assert_write_reconciled(command_id)
            self._ensure_started()
            assert self._connection is not None
            try:
                self._connection.send(("call", method, args, kwargs))
                if not self._connection.poll(60):
                    self._freeze_write(method, command_id)
                    self._close_unlocked()
                    raise GatewayResultUnknownError(
                        f"MT5 worker timed out for account {self.account_id}"
                    )
                status, error_type, payload = self._connection.recv()
            except (BrokenPipeError, EOFError, OSError) as exc:
                self._freeze_write(method, command_id)
                self._close_unlocked()
                raise GatewayResultUnknownError(
                    f"MT5 worker unavailable for account {self.account_id}"
                ) from exc
            if status == "ok":
                return payload
            error_class = _ERROR_TYPES.get(error_type, GatewayConfigurationError)
            raise error_class(str(payload))

    @staticmethod
    def _command_id(method: str, args: tuple[Any, ...]) -> str | None:
        if method != "submit_order" or not args:
            return None
        return str(getattr(args[0], "command_id", "") or "") or None

    def _freeze_write(self, method: str, command_id: str | None) -> None:
        if method not in _WRITE_METHODS:
            return
        if command_id is None:
            self._write_frozen_without_command = True
        else:
            self._write_frozen_command_id = command_id

    def _assert_write_reconciled(self, command_id: str | None) -> None:
        if self._write_frozen_without_command:
            raise GatewayResultUnknownError(
                f"MT5 writes are frozen for account {self.account_id} after an uncertain write"
            )
        frozen_command_id = self._write_frozen_command_id
        if frozen_command_id is not None:
            if has_unresolved_command_for_account(
                self.account_id,
                exclude_command_id=command_id,
            ):
                raise GatewayResultUnknownError(
                    f"MT5 writes are frozen for account {self.account_id} pending reconciliation"
                )
            self._write_frozen_command_id = None
        if has_unresolved_command_for_account(
            self.account_id,
            exclude_command_id=command_id,
        ):
            raise GatewayResultUnknownError(
                f"MT5 account {self.account_id} has an unresolved Runtime command"
            )

    def _ensure_started(self) -> None:
        if self._process is not None and self._process.is_alive() and self._connection is not None:
            return
        if self._startup_failure is not None and self._startup_failed_at is not None:
            cooldown = min(30.0, 2.0 ** min(self._startup_failures - 1, 4))
            elapsed = time.monotonic() - self._startup_failed_at
            if elapsed < cooldown:
                raise GatewayConfigurationError(
                    f"MT5 worker startup cooling down for account {self.account_id}: "
                    f"{self._startup_failure}"
                ) from self._startup_failure
        self._close_unlocked()
        parent, child = multiprocessing.Pipe()
        process = multiprocessing.Process(
            target=_run_account_worker,
            args=(
                child,
                self.settings.model_dump(),
                self.account_id,
                self.terminal_path,
            ),
            name=f"vg-mt5-{self.account_id}",
            daemon=True,
        )
        process.start()
        WORKER_STARTS.labels(self.account_id).inc()
        child.close()
        self._process = process
        self._connection = parent
        # A portable terminal may perform a first-run MQL5 rebuild before it
        # can answer the worker handshake.  The fixed 15s window caused a
        # false runtime_unavailable on the isolated WW terminal.
        startup_timeout = max(
            15.0,
            float(self.settings.mt5_check_timeout_seconds) + 30.0,
        )
        if not parent.poll(startup_timeout):
            self._close_unlocked()
            error = GatewayConfigurationError(
                f"MT5 worker startup timed out for account {self.account_id}"
            )
            self._record_startup_failure(error)
            raise error
        status, _, payload = parent.recv()
        if status != "ready":
            self._close_unlocked()
            error = GatewayConfigurationError(str(payload))
            self._record_startup_failure(error)
            raise error
        self._startup_failures = 0
        self._startup_failed_at = None
        self._startup_failure = None
        WORKER_READY.labels(self.account_id).set_function(lambda: int(process.is_alive()))

    def _record_startup_failure(self, error: GatewayConfigurationError) -> None:
        self._startup_failures += 1
        self._startup_failed_at = time.monotonic()
        self._startup_failure = error

    def _close_unlocked(self) -> None:
        WORKER_READY.labels(self.account_id).set_function(lambda: 0)
        connection = self._connection
        process = self._process
        self._connection = None
        self._process = None
        if connection is not None:
            try:
                connection.send(("close",))
            except (BrokenPipeError, EOFError, OSError):
                pass
            connection.close()
        if process is not None and process.is_alive():
            process.join(timeout=3)
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)


class Mt5AccountWorkerSupervisor:
    """Owns one process and one distinct Terminal executable per MT5 account."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._clients: dict[str, Mt5AccountWorkerClient] = {}
        atexit.register(self.close)

    def adapter(self, account_id: str) -> Mt5AccountWorkerClient:
        if account_id not in self.settings.mt5_accounts:
            raise GatewayConfigurationError("Account is not mapped to MT5")
        client = self._clients.get(account_id)
        if client is None:
            terminal_path = self.settings.mt5_terminal_for_account(account_id)
            if not terminal_path:
                raise GatewayConfigurationError(f"MT5_TERMINAL_PATH_REQUIRED:{account_id}")
            client = Mt5AccountWorkerClient(
                settings=self.settings,
                account_id=account_id,
                terminal_path=terminal_path,
            )
            self._clients[account_id] = client
        return client

    def missing_requirements(self, selected_account_id: str | None = None) -> list[str]:
        missing: list[str] = []
        owners: dict[str, str] = {}
        for account_id in sorted(self.settings.mt5_accounts):
            terminal_path = self.settings.mt5_terminal_for_account(account_id)
            if not terminal_path:
                missing.append(f"{account_id}:MT5_TERMINAL_PATH")
                continue
            resolved = str(Path(terminal_path).resolve()).casefold()
            if not Path(terminal_path).is_file():
                missing.append(f"{account_id}:MT5_TERMINAL_NOT_FOUND")
            if resolved in owners:
                missing.append(f"{account_id}:MT5_TERMINAL_SHARED_WITH:{owners[resolved]}")
            owners[resolved] = account_id
        if selected_account_id is None:
            return missing
        prefix = f"{selected_account_id}:"
        return [item for item in missing if item.startswith(prefix)]

    def close(self) -> None:
        for client in list(self._clients.values()):
            client.close()


def _run_account_worker(
    connection,
    settings_values: dict[str, Any],
    account_id: str,
    terminal_path: str,
) -> None:
    gateway = None
    try:
        from app.bybit_mt5_gateway import BybitMt5Gateway
        from app.strict_live_acceptance_adapters import StrictMt5AcceptanceAdapter

        original = Settings(**settings_values)
        is_primary = account_id == original.mt5_primary_account_id
        settings_values.update(
            {
                "mt5_account_ids": account_id,
                "mt5_primary_account_id": account_id,
                "mt5_credential_ref": original.mt5_credential_for_account(account_id),
                "mt5_terminal_path": terminal_path,
                # Each account uses its configured Terminal and the data directory
                # selected by its portable setting.
                "mt5_terminal_portable": original.mt5_terminal_portable_for_account(account_id),
                "mt5_check_timeout_seconds": max(
                    original.mt5_check_timeout_seconds,
                    30.0 if not is_primary else original.mt5_check_timeout_seconds,
                ),
            }
        )
        settings = Settings(**settings_values)
        adapter = StrictMt5AcceptanceAdapter(settings)
        gateway = BybitMt5Gateway(settings=settings, mt5=adapter)
        # Ready means the explicit Terminal has initialized and the configured
        # Login/Server identity has been proven by an authoritative snapshot.
        _prove_worker_ready(gateway, account_id)
        connection.send(("ready", None, {"accountId": account_id}))
        visibility_failed = False
        parent = multiprocessing.parent_process()
        while True:
            # Windows does not automatically terminate a spawned child when
            # its Runtime parent is force-stopped.  Leaving this worker alive
            # keeps an MT5 IPC session attached and lets the next Runtime
            # create a competing session against the same Terminal.
            if parent is not None and not parent.is_alive():
                break
            try:
                maintain_background_terminal(terminal_path)
                visibility_failed = False
            except Exception:
                # Window presentation must not interrupt execution or SDK identity.
                if not visibility_failed:
                    logging.getLogger(__name__).exception(
                        "MT5 background window maintenance failed"
                    )
                visibility_failed = True
            if not connection.poll(0.1):
                continue
            message = connection.recv()
            if message[0] == "close":
                break
            _, method, args, kwargs = message
            try:
                result = _execute_worker_call(gateway, account_id, method, args, kwargs)
                connection.send(("ok", None, result))
            except Exception as exc:
                connection.send(("error", type(exc).__name__, str(exc)))
    except (EOFError, BrokenPipeError):
        pass
    except Exception as exc:
        try:
            connection.send(("error", type(exc).__name__, str(exc)))
        except Exception:
            pass
    finally:
        try:
            import MetaTrader5 as mt5

            sdk: Any = mt5
            sdk.shutdown()
        except Exception:
            pass
        connection.close()


def _prove_worker_ready(gateway: Any, account_id: str) -> None:
    # Startup needs an authoritative account identity, not a history backfill.
    snapshot = gateway.get_account_risk(account_id)
    if str(getattr(snapshot, "account_id", "") or "") != account_id:
        raise GatewayConfigurationError("MT5 worker account identity mismatch")


def _execute_worker_call(gateway: Any, account_id: str, method: str, args, kwargs):
    def invoke():
        if method == "capability":
            return gateway.mt5.capability()
        return getattr(gateway, method)(*args, **kwargs)

    try:
        return invoke()
    except (GatewayConfigurationError, GatewayResultUnknownError):
        if method not in _READ_METHODS or not gateway.mt5.recover_read_transport():
            raise
        # Read-only recovery does not replay writes or alter unresolved journal state.
        _prove_worker_ready(gateway, account_id)
        return invoke()
