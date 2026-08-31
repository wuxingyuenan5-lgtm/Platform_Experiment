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

    def assert_healthy(self) -> None:
        if not self._restore_failed:
            return
        raise GatewayConfigurationError(
            self._restore_failure_reason or "MT5 primary account restore failed"
        )

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
        current = mt5.account_info()
        current_login = str(getattr(current, "login", "") or "")
        current_server = str(getattr(current, "server", "") or "")
        if current_login == session.login and current_server == session.server:
            if account_id == settings.mt5_primary_account_id.strip():
                self.clear_restore_failure()
            return session
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
        if account_id == settings.mt5_primary_account_id.strip():
            self.clear_restore_failure()
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

    def probe_primary_health(self, *, mt5: Any, settings: Settings) -> None:
        with self.acquire():
            primary_account_id = settings.mt5_primary_account_id.strip()
            if not primary_account_id:
                self.clear_restore_failure()
                return
            try:
                self.login(mt5=mt5, settings=settings, account_id=primary_account_id)
            except Exception as exc:
                self._restore_failed = True
                self._restore_failure_reason = str(exc)
                raise GatewayConfigurationError("MT5 primary account restore failed") from exc
            self.clear_restore_failure()


COORDINATOR = Mt5ReadOnlyCoordinator()


@contextmanager
def mt5_account_session(
    *,
    mt5: Any,
    settings: Settings,
    account_id: str,
):
    """Serialize one explicit MT5 account session across every read and write.

    MetaTrader5 controls one process-global Terminal session. A prior restore
    failure is recoverable only by proving the primary identity again; it must
    not permanently poison the Runtime after a transient IPC timeout.
    """
    with COORDINATOR.acquire():
        primary_account_id = settings.mt5_primary_account_id.strip()
        if settings.live_write_enabled and account_id != primary_account_id:
            raise GatewayConfigurationError(
                "MT5_NON_PRIMARY_SESSION_PAUSED_DURING_LIVE_WRITE"
            )
        if COORDINATOR.restore_failed:
            COORDINATOR.login(
                mt5=mt5,
                settings=settings,
                account_id=primary_account_id,
            )
        switched_away_from_primary = account_id != primary_account_id
        try:
            session = COORDINATOR.login(
                mt5=mt5,
                settings=settings,
                account_id=account_id,
            )
            yield session
        finally:
            if switched_away_from_primary:
                COORDINATOR.restore_primary(mt5=mt5, settings=settings)


def with_mt5_read_session[T](
    *,
    mt5: Any,
    settings: Settings,
    account_id: str,
    callback: Callable[[Mt5ReadSession], T],
) -> T:
    with mt5_account_session(
        mt5=mt5,
        settings=settings,
        account_id=account_id,
    ) as session:
        try:
            return callback(session)
        except GatewayConfigurationError:
            raise
        except Exception as exc:
            raise GatewayResultUnknownError("MT5 read-only snapshot failed") from exc
