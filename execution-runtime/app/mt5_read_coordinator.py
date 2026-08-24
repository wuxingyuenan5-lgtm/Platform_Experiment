from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.config import Settings
from app.gateway_errors import GatewayConfigurationError, GatewayResultUnknownError
from app.secret_resolver import resolve_secret_reference


@dataclass(frozen=True)
class Mt5ReadSession:
    account_id: str
    secret_ref: str
    login: str
    server: str


class Mt5ReadOnlyCoordinator:
    def __init__(self) -> None:
        self._lock = Lock()
        self._restore_failed = False
        self._restore_failure_reason: str | None = None

    @property
    def restore_failed(self) -> bool:
        return self._restore_failed

    @property
    def restore_failure_reason(self) -> str | None:
        return self._restore_failure_reason

    def readiness_suffix(self) -> list[str]:
        if not self._restore_failed:
            return []
        return ["MT5_PRIMARY_RESTORE_FAILED"]

    def clear_restore_failure(self) -> None:
        self._restore_failed = False
        self._restore_failure_reason = None

    @contextmanager
    def acquire(self):
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()

    def resolve_session(self, settings: Settings, account_id: str) -> Mt5ReadSession:
        try:
            secret_ref = settings.mt5_credential_for_account(account_id)
            secret = resolve_secret_reference(
                secret_ref,
                required_fields=("LOGIN", "PASSWORD", "SERVER"),
            )
        except ValueError as exc:
            raise GatewayConfigurationError(str(exc)) from exc
        return Mt5ReadSession(
            account_id=account_id,
            secret_ref=secret_ref,
            login=str(secret["LOGIN"]),
            server=str(secret["SERVER"]),
        )

    def login(
        self,
        *,
        mt5: Any,
        settings: Settings,
        account_id: str,
    ) -> Mt5ReadSession:
        session = self.resolve_session(settings, account_id)
        timeout_ms = int(settings.mt5_check_timeout_seconds * 1000)
        secret = resolve_secret_reference(
            session.secret_ref,
            required_fields=("LOGIN", "PASSWORD", "SERVER"),
        )
        authorized = mt5.login(
            int(secret["LOGIN"]),
            password=secret["PASSWORD"],
            server=secret["SERVER"],
            timeout=timeout_ms,
        )
        if not authorized:
            raise GatewayConfigurationError(f"MT5 login failed: {mt5.last_error()}")
        info = mt5.account_info()
        actual_login = str(getattr(info, "login", "") or "")
        actual_server = str(getattr(info, "server", "") or "")
        if actual_login != session.login or actual_server != session.server:
            raise GatewayConfigurationError("MT5 account identity mismatch after login")
        return session

    def restore_primary(self, *, mt5: Any, settings: Settings) -> None:
        primary_account_id = settings.mt5_primary_account_id.strip()
        if not primary_account_id:
            return
        try:
            self.login(mt5=mt5, settings=settings, account_id=primary_account_id)
        except Exception as exc:
            self._restore_failed = True
            self._restore_failure_reason = str(exc)
            raise GatewayConfigurationError("MT5 primary account restore failed") from exc
        self.clear_restore_failure()


COORDINATOR = Mt5ReadOnlyCoordinator()


def with_mt5_read_session[T](
    *,
    mt5: Any,
    settings: Settings,
    account_id: str,
    callback: Callable[[Mt5ReadSession], T],
) -> T:
    if COORDINATOR.restore_failed:
        raise GatewayConfigurationError(
            COORDINATOR.restore_failure_reason or "MT5 primary account restore failed"
        )
    with COORDINATOR.acquire():
        try:
            session = COORDINATOR.login(mt5=mt5, settings=settings, account_id=account_id)
            return callback(session)
        except GatewayConfigurationError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 read-only snapshot failed") from exc
        finally:
            try:
                COORDINATOR.restore_primary(mt5=mt5, settings=settings)
            except GatewayConfigurationError:
                raise
