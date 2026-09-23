"""Start a local managed child with durable file handles for both log streams."""

import ctypes
import os
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path


def own_scheduled_worker(child: subprocess.Popen) -> int:
    """Kill the task's direct worker if pythonw is stopped or crashes.

    Descendant launches deliberately break away: the watchdog and business
    services have independent owners and must survive a supervisor restart.
    """

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimits),
            ("IoInfo", ctypes.c_ulonglong * 6),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = (
        0x2000 | 0x1000
    )  # KILL_ON_JOB_CLOSE | SILENT_BREAKAWAY_OK
    if not kernel.SetInformationJobObject(
        job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
    ) or not kernel.AssignProcessToJobObject(job, int(child._handle)):
        error = ctypes.get_last_error()
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(job)
        child.kill()
        child.wait()
        raise ctypes.WinError(error)
    return job


def main() -> int:
    arguments = sys.argv[1:]
    wait = bool(arguments and arguments[0] == "--wait")
    if wait:
        arguments = arguments[1:]
    if len(arguments) < 5:
        raise SystemExit(
            "usage: launch-platform-child.py [--wait] EXE CWD STDOUT STDERR ARG..."
        )
    executable, working_directory, stdout_path, stderr_path, *arguments = arguments
    if not Path(executable).is_file() or not Path(working_directory).is_dir():
        raise SystemExit("managed executable or working directory is missing")

    # Windows treats environment keys case-insensitively. Normalize keys before
    # creating the child; both PATH and Path previously broke PowerShell spawn.
    environment: dict[str, str] = {}
    for key, value in os.environ.items():
        existing = next(
            (name for name in environment if name.casefold() == key.casefold()), None
        )
        if existing is not None:
            del environment[existing]
        environment[key] = value

    # Scheduled tasks use pythonw + --wait: no console is ever allocated, and
    # Task Scheduler observes the actual worker lifetime and exit code.
    mode = "ab" if wait else "wb"
    with open(stdout_path, mode) as stdout, open(stderr_path, mode) as stderr:
        child = subprocess.Popen(
            [executable, *arguments],
            cwd=working_directory,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
    if wait:
        try:
            job = own_scheduled_worker(child)
        except OSError:
            if child.poll() is None:
                child.kill()
                child.wait()
            raise
        try:
            return child.wait()
        finally:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle(job)
    print(child.pid, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
