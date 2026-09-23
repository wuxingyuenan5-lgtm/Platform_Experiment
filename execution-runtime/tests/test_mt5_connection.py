from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.mt5_connection import _finish_background_startup, initialize_mt5

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows MT5 startup")


def terminal_process(executable: str | None, ppid: int | None = None):
    info = {"name": "terminal64.exe", "exe": executable}
    if ppid is not None:
        info["ppid"] = ppid
    return SimpleNamespace(pid=4321, info=info, terminate=Mock(), wait=Mock(), kill=Mock())


@pytest.mark.parametrize("portable", [False, True])
def test_sdk_owns_single_terminal_start_and_runtime_only_hides_after_attach(
    tmp_path, monkeypatch, portable
):
    terminal = str(tmp_path / "terminal64.exe")
    events = []

    def connect(*args, **kwargs):
        events.append("connect")
        assert args == (terminal,)
        assert kwargs == {"portable": portable, "timeout": 8000}
        return True

    monkeypatch.setattr(
        "app.mt5_connection.maintain_background_terminal",
        lambda path: events.append(("background", path)),
    )
    sdk = SimpleNamespace(initialize=connect)
    assert initialize_mt5(
        sdk, terminal_path=terminal, background=True, portable=portable, timeout=8000
    )
    assert events == ["connect", ("background", terminal)]


def test_startup_finalization_only_hides_the_new_process_main_window(monkeypatch):
    owners = {101: 1234, 102: 9999, 103: 1234, 104: 1234}

    def window_pid(window, pointer):
        pointer._obj.value = owners[window]
        return 1

    def enumerate_windows(callback, value):
        for window in owners:
            callback(window, value)
        return 1

    user = SimpleNamespace(
        EnumWindows=Mock(side_effect=enumerate_windows),
        GetWindowThreadProcessId=Mock(side_effect=window_pid),
        GetWindow=Mock(side_effect=lambda window, _: 101 if window == 103 else 0),
        IsWindowVisible=Mock(side_effect=lambda window: window != 104),
        ShowWindowAsync=Mock(return_value=1),
    )
    monkeypatch.setattr("ctypes.WinDLL", lambda *args, **kwargs: user)

    _finish_background_startup(1234)

    assert [call.args for call in user.ShowWindowAsync.call_args_list] == [(101, 0), (103, 0)]


def test_background_maintenance_rechecks_only_the_configured_terminal(tmp_path, monkeypatch):
    from app.mt5_connection import maintain_background_terminal

    terminal = str(tmp_path / "Account A" / "terminal64.exe")
    other = str(tmp_path / "Account B" / "terminal64.exe")
    monkeypatch.setattr("psutil.process_iter", lambda attrs: [
        terminal_process(terminal), terminal_process(other), terminal_process(None)
    ])
    hide = Mock()
    monkeypatch.setattr("app.mt5_connection._finish_background_startup", hide)
    # A later show event is covered by the next worker maintenance pass.
    maintain_background_terminal(terminal)
    maintain_background_terminal(terminal)
    assert hide.call_count == 2
    hide.assert_called_with(4321, require_window=False)


def test_failed_sdk_attachment_still_hides_terminal(monkeypatch):
    hide = Mock()
    monkeypatch.setattr("app.mt5_connection.maintain_background_terminal", hide)
    assert not initialize_mt5(
        SimpleNamespace(initialize=Mock(return_value=False)),
        terminal_path="C:/MT5/terminal64.exe", background=True,
    )
    hide.assert_called_once_with("C:/MT5/terminal64.exe")
