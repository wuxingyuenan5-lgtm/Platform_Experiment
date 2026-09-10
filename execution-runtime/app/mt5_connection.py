from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from app.gateway_errors import GatewayConfigurationError


def _wait_for_terminal_startup(process_id: int, timeout_ms: int) -> None:
    """Wait for the GUI process to initialize before the SDK searches for it."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    user.WaitForInputIdle.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    user.WaitForInputIdle.restype = wintypes.DWORD
    handle = kernel.OpenProcess(0x00101000, False, process_id)  # Synchronize + limited query.
    if not handle:
        raise GatewayConfigurationError("Cannot wait for MT5 Terminal startup")
    try:
        if user.WaitForInputIdle(handle, timeout_ms) != 0:
            raise GatewayConfigurationError("MT5 Terminal startup did not become ready")
    finally:
        kernel.CloseHandle(handle)


def _ensure_background_terminal(
    terminal_path: str, *, portable: bool, timeout_ms: int
) -> int | None:
    """Start an absent, explicitly configured Terminal without taking focus."""
    if sys.platform != "win32":
        return
    import psutil

    terminal = Path(terminal_path).resolve()
    for process in psutil.process_iter(["name", "exe"]):
        if str(process.info["name"] or "").casefold() != terminal.name.casefold():
            continue
        executable = process.info["exe"]
        if not executable:
            raise GatewayConfigurationError("Cannot establish the running MT5 Terminal path")
        if Path(executable).resolve() == terminal:
            _wait_for_terminal_startup(process.pid, timeout_ms)
            return process.pid

    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0  # SW_HIDE: background operation, matching the monitoring Terminal.
    arguments = [str(terminal)]
    if portable:
        arguments.append("/portable")
    try:
        process = subprocess.Popen(
            arguments,
            cwd=terminal.parent,
            startupinfo=startup,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise GatewayConfigurationError("MT5 background startup failed") from exc
    _wait_for_terminal_startup(process.pid, timeout_ms)
    return process.pid


def _finish_background_startup(process_id: int, *, require_window: bool = True) -> None:
    """Hide only this configured Terminal's visible, unowned top-level windows."""
    import ctypes
    from ctypes import wintypes

    user = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.EnumWindows.restype = wintypes.BOOL
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype = wintypes.DWORD
    user.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user.GetWindow.restype = wintypes.HWND
    user.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
    user.ShowWindowAsync.restype = wintypes.BOOL
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsWindowVisible.restype = wintypes.BOOL
    windows = []

    @callback_type
    def collect(window, _):
        owner = wintypes.DWORD()
        user.GetWindowThreadProcessId(window, ctypes.byref(owner))
        if (
            owner.value == process_id
            and not user.GetWindow(window, 4)  # GW_OWNER: exclude owned dialogs.
        ):
            windows.append(window)
        return True

    if not user.EnumWindows(collect, 0) or (require_window and not windows):
        raise GatewayConfigurationError("MT5 startup window is unavailable")
    for window in windows:
        if not user.IsWindowVisible(window):
            continue
        if not user.ShowWindowAsync(window, 0):  # SW_HIDE
            raise GatewayConfigurationError("MT5 startup could not finish in the background")


def maintain_background_terminal(terminal_path: str) -> None:
    """Enforce the owner's background policy without launching or reconnecting MT5."""
    if sys.platform != "win32":
        return
    import psutil

    terminal = Path(terminal_path).resolve()
    for process in psutil.process_iter(["name", "exe"]):
        if process.info["exe"] and Path(process.info["exe"]).resolve() == terminal:
            _finish_background_startup(process.pid, require_window=False)


def initialize_mt5(
    mt5: Any,
    *,
    terminal_path: str | None,
    background: bool = False,
    **kwargs: object,
) -> bool:
    """Initialize the explicit Terminal using MetaTrader5's positional path contract."""
    if terminal_path:
        started_pid = None
        if background:
            started_pid = _ensure_background_terminal(
                terminal_path,
                portable=bool(kwargs.get("portable", False)),
                timeout_ms=int(str(kwargs.get("timeout", 60000))),
            )
        try:
            return bool(mt5.initialize(terminal_path, **kwargs))
        finally:
            if started_pid is not None:
                _finish_background_startup(started_pid)
    return bool(mt5.initialize(**kwargs))
