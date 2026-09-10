from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.gateway_errors import GatewayConfigurationError
from app.mt5_connection import _finish_background_startup, initialize_mt5

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows MT5 startup")


def terminal_process(executable: str | None):
    return SimpleNamespace(pid=4321, info={"name": "terminal64.exe", "exe": executable})


@pytest.mark.parametrize("portable", [False, True])
def test_absent_terminal_starts_hidden_before_sdk_attachment(tmp_path, monkeypatch, portable):
    terminal = tmp_path / "Main MT5" / "terminal64.exe"
    # Another logical account's executable must not be mistaken for this one.
    monkeypatch.setattr(
        "psutil.process_iter",
        lambda attrs: [terminal_process(str(tmp_path / "Other MT5" / "terminal64.exe"))],
    )
    events = []

    def spawn(arguments, **kwargs):
        events.append("spawn")
        assert arguments == [str(terminal)] + (["/portable"] if portable else [])
        assert kwargs["startupinfo"].wShowWindow == 0
        assert kwargs["startupinfo"].dwFlags & 1
        return SimpleNamespace(pid=1234)

    def wait_for_startup(pid, timeout_ms):
        assert (pid, timeout_ms) == (1234, 8000)
        events.append("ready")

    def connect(*args, **kwargs):
        events.append("connect")
        assert args == (str(terminal),)
        assert kwargs == {"portable": portable, "timeout": 8000}
        return True

    def finish_startup(pid):
        assert pid == 1234
        events.append("background")

    monkeypatch.setattr("app.mt5_connection.subprocess.Popen", spawn)
    monkeypatch.setattr("app.mt5_connection._wait_for_terminal_startup", wait_for_startup)
    monkeypatch.setattr("app.mt5_connection._finish_background_startup", finish_startup)
    assert initialize_mt5(
        SimpleNamespace(initialize=connect),
        terminal_path=str(terminal),
        background=True,
        portable=portable,
        timeout=8000,
    )
    assert events == ["spawn", "ready", "connect", "background"]


def test_existing_terminal_is_attached_and_hidden_without_relaunching(
    tmp_path, monkeypatch
):
    terminal = str(tmp_path / "terminal64.exe")
    monkeypatch.setattr("psutil.process_iter", lambda attrs: [terminal_process(terminal)])
    spawn = Mock(side_effect=AssertionError("Existing Terminal must not be relaunched"))
    monkeypatch.setattr("app.mt5_connection.subprocess.Popen", spawn)
    ready = Mock()
    monkeypatch.setattr("app.mt5_connection._wait_for_terminal_startup", ready)
    finish = Mock()
    monkeypatch.setattr("app.mt5_connection._finish_background_startup", finish)
    sdk = SimpleNamespace(initialize=Mock(return_value=True))

    assert initialize_mt5(sdk, terminal_path=terminal, background=True, timeout=8000)

    spawn.assert_not_called()
    ready.assert_called_once_with(4321, 8000)
    finish.assert_called_once_with(4321)
    sdk.initialize.assert_called_once_with(terminal, timeout=8000)


@pytest.mark.parametrize("failure", ["path_unavailable", "spawn_failed"])
def test_background_startup_failure_never_falls_back_to_sdk_foreground_launch(
    tmp_path, monkeypatch, failure
):
    monkeypatch.setattr(
        "psutil.process_iter",
        lambda attrs: [terminal_process(None)] if failure == "path_unavailable" else [],
    )
    monkeypatch.setattr(
        "app.mt5_connection.subprocess.Popen", Mock(side_effect=OSError("cannot start"))
    )
    sdk = SimpleNamespace(initialize=Mock())

    with pytest.raises(GatewayConfigurationError):
        initialize_mt5(sdk, terminal_path=str(tmp_path / "terminal64.exe"), background=True)

    sdk.initialize.assert_not_called()


def test_not_ready_terminal_never_allows_a_second_sdk_launch(tmp_path, monkeypatch):
    monkeypatch.setattr("psutil.process_iter", lambda attrs: [])
    monkeypatch.setattr(
        "app.mt5_connection.subprocess.Popen", Mock(return_value=SimpleNamespace(pid=1234))
    )
    monkeypatch.setattr(
        "app.mt5_connection._wait_for_terminal_startup",
        Mock(side_effect=GatewayConfigurationError("Terminal is still starting")),
    )
    sdk = SimpleNamespace(initialize=Mock())

    with pytest.raises(GatewayConfigurationError, match="still starting"):
        initialize_mt5(sdk, terminal_path=str(tmp_path / "terminal64.exe"), background=True)

    sdk.initialize.assert_not_called()


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

    assert [call.args for call in user.ShowWindowAsync.call_args_list] == [(101, 0)]


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
    monkeypatch.setattr("app.mt5_connection._ensure_background_terminal", Mock(return_value=4321))
    hide = Mock()
    monkeypatch.setattr("app.mt5_connection._finish_background_startup", hide)
    assert not initialize_mt5(
        SimpleNamespace(initialize=Mock(return_value=False)),
        terminal_path="C:/MT5/terminal64.exe", background=True,
    )
    hide.assert_called_once_with(4321)
