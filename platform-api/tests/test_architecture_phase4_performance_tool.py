from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_phase4_critical_path_tool_emits_repeatable_schema() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            str(repository_root / "scripts" / "measure-phase4-critical-paths.py"),
            str(repository_root),
            "--iterations",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)

    assert payload["runtime"]["iterations"] == 2
    assert payload["platform_api"]["iterations"] == 10
    for metric in (
        "command_claim_seconds",
        "journal_write_read_seconds",
        "result_unknown_recovery_seconds",
    ):
        assert payload["runtime"][metric] >= 0
    assert payload["platform_api"]["platform_trading_route_seconds"] >= 0
