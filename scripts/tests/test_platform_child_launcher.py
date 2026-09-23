"""The managed child must keep writing logs after its short-lived launcher exits."""

import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


def test_child_log_handles_survive_launcher_exit(tmp_path: Path) -> None:
    launcher = Path(__file__).resolve().parents[1] / "launch-platform-child.py"
    stdout = tmp_path / "stdout.log"
    stderr = tmp_path / "stderr.log"
    code = (
        "import sys,time;time.sleep(.2);"
        "print('late stdout',flush=True);"
        "print('late stderr',file=sys.stderr,flush=True)"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(launcher),
            sys.executable,
            str(tmp_path),
            str(stdout),
            str(stderr),
            "-c",
            code,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert int(result.stdout.strip()) > 0
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if (
            stdout.exists()
            and stderr.exists()
            and stdout.read_text().strip()
            and stderr.read_text().strip()
        ):
            break
        time.sleep(0.05)
    assert stdout.read_text().strip() == "late stdout"
    assert stderr.read_text().strip() == "late stderr"


def test_scheduled_launcher_waits_without_console_and_returns_failure(
    tmp_path: Path,
) -> None:
    launcher = Path(__file__).resolve().parents[1] / "launch-platform-child.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    stdout, stderr = tmp_path / "stdout.log", tmp_path / "stderr.log"
    stdout.write_text("prior run\n")
    code = (
        "import ctypes,json,sys,time;time.sleep(.2);"
        "print(json.dumps({'console':ctypes.windll.kernel32.GetConsoleWindow()}),flush=True);"
        "print('worker failed',file=sys.stderr,flush=True);sys.exit(7)"
    )
    result = subprocess.run(
        [
            str(pythonw),
            str(launcher),
            "--wait",
            sys.executable,
            str(tmp_path),
            str(stdout),
            str(stderr),
            "-c",
            code,
        ],
        timeout=10,
        check=False,
    )
    assert result.returncode == 7
    lines = stdout.read_text().splitlines()
    assert lines[0] == "prior run"
    assert json.loads(lines[1]) == {"console": 0}
    assert stderr.read_text().strip() == "worker failed"


def test_task_stop_ends_worker_but_preserves_independent_descendant(
    tmp_path: Path,
) -> None:
    launcher = Path(__file__).resolve().parents[1] / "launch-platform-child.py"
    stdout, stderr = tmp_path / "stdout.log", tmp_path / "stderr.log"
    # Give the job assignment time to finish before simulating a supervisor
    # launching its independently owned watchdog/service.
    code = (
        "import os,subprocess,sys,time;time.sleep(.3);"
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(15)'],creationflags=subprocess.CREATE_NO_WINDOW);"
        "print(str(os.getpid())+' '+str(p.pid),flush=True);time.sleep(15)"
    )
    wrapper = subprocess.Popen(
        [
            str(Path(sys.executable).with_name("pythonw.exe")),
            str(launcher),
            "--wait",
            sys.executable,
            str(tmp_path),
            str(stdout),
            str(stderr),
            "-c",
            code,
        ],
    )
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handles = []
    try:
        deadline = time.monotonic() + 5
        while not stdout.exists() or not stdout.read_text().strip():
            assert time.monotonic() < deadline
            time.sleep(0.03)
        handles = [
            kernel.OpenProcess(0x100001, False, int(pid))
            for pid in stdout.read_text().split()
        ]
        assert all(handles)
        wrapper.kill()
        wrapper.wait(timeout=5)
        assert kernel.WaitForSingleObject(handles[0], 3000) == 0
        assert kernel.WaitForSingleObject(handles[1], 0) == 258
    finally:
        if wrapper.poll() is None:
            wrapper.kill()
            wrapper.wait(timeout=5)
        for handle in handles:
            if handle:
                kernel.TerminateProcess(handle, 0)
                kernel.CloseHandle(handle)
