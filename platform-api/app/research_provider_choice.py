"""Isolated, read-only Choice daily close fallback for research observations.

The native SDK is executed in a short-lived child process so a DLL fault or a
blocking login cannot take down the API worker. Child output is parsed locally
and never forwarded; credentials are supplied only through the SDK's existing
user-level activation store.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_SDK_ROOT = Path.home() / ".choice" / "EMQuantAPI_Python" / "python3"
_CHILD = r"""
import json, sys
from decimal import Decimal
import pandas as pd
from EmQuantAPI import c
code, day = sys.argv[1], sys.argv[2]
try:
    login = c.start()
    if getattr(login, "ErrorCode", -1) != 0:
        print(json.dumps({"ok": False, "error": "login_failed"}))
    else:
        result = c.css(
            code, "CLOSE",
            "TradeDate=" + day + ",Ispandas=1,RECVtimeout=60",
        )
        value = None
        if isinstance(result, pd.DataFrame) and "CLOSE" in result.columns:
            if "DATES" in result.columns and code in result.index:
                row = result.loc[code]
                if str(row["DATES"])[:10].replace("/", "-") == day:
                    candidate = pd.to_numeric(row["CLOSE"], errors="coerce")
                    value = candidate if pd.notna(candidate) else None
        print(json.dumps({
            "ok": value is not None,
            "value": str(value) if value is not None else None,
        }))
finally:
    try:
        c.stop()
    except Exception:
        pass
"""


def choice_daily_close(
    trade_date: date | str,
    *,
    instrument_code: str = "801102.SWI",
    timeout_seconds: float = 8.0,
    sdk_root: Path | str | None = None,
) -> Decimal | None:
    """Return one Choice close, or None for every unavailable/invalid outcome."""
    root = Path(sdk_root or os.environ.get("VG_CHOICE_SDK_ROOT", DEFAULT_SDK_ROOT))
    if not (root / "EmQuantAPI.py").is_file():
        return None
    day = trade_date.isoformat() if isinstance(trade_date, date) else str(trade_date)[:10]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    # Some Windows virtual-environment launchers cannot load the SDK's native
    # DLL even though their base interpreter can. Keep the SDK in its own
    # process and use that base interpreter rather than the API venv shim.
    python_executable = str(getattr(sys, "_base_executable", None) or sys.executable)
    try:
        completed = subprocess.run(
            [python_executable, "-c", _CHILD, instrument_code, day],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=max(0.5, timeout_seconds),
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    result = None
    for line in reversed(completed.stdout.splitlines()):
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "ok" in candidate:
            result = candidate
            break
    if not result or not result.get("ok"):
        return None
    try:
        value = Decimal(str(result.get("value")))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return value if value > 0 else None
