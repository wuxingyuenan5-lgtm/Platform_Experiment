from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.gateway_errors import GatewayConfigurationError


def _finish_background_startup(process_id: int, *, require_window: bool = True) -> None:
    """Hide every visible top-level window owned by this configured Terminal."""
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
        try:
            initialized = bool(mt5.initialize(terminal_path, **kwargs))
        finally:
            if background:
                maintain_background_terminal(terminal_path)
        return initialized
    return bool(mt5.initialize(**kwargs))




