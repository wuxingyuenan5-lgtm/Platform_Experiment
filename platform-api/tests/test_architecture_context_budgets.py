from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTEXT_TOOL = ROOT / "scripts/context-for.py"


def _budget_bytes() -> bytes:
    return subprocess.check_output(
        [sys.executable, str(CONTEXT_TOOL), "--check-budgets", "--json"],
        cwd=ROOT,
    )


def test_context_budget_report_is_deterministic_and_clean() -> None:
    first = _budget_bytes()
    second = _budget_bytes()
    assert second == first

    report = json.loads(first)
    assert report["ok"] is True
    assert report["failures"] == []
    assert report["default_startup"]["over_budget"] is False
    for pack in report["packs"].values():
        assert pack["missing_paths"] == []
        assert pack["required"]["over_budget"] is False
        assert pack["optional"]["over_budget"] is False
        assert pack["required"]["largest_file"] is not None


def test_context_pack_with_optional_reports_combined_largest_file() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CONTEXT_TOOL),
            "release-acceptance",
            "--with-optional",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")

    report = json.loads(completed.stdout)
    existing_files = [row for row in report["files"] if row["exists"]]
    expected_largest = max(
        existing_files,
        key=lambda row: (int(row["estimated_tokens"]), str(row["path"])),
        default=None,
    )
    assert report["include_optional"] is True
    assert report["largest_file"] == expected_largest
    assert report["missing_paths"] == [
        *report["required"]["missing_paths"],
        *report["optional"]["missing_paths"],
    ]


def test_trading_display_pack_uses_formal_cross_venue_owner() -> None:
    source = CONTEXT_TOOL.read_text(encoding="utf-8")
    assert "CrossVenueExecutionWorkspace.vue" in source
    assert "CrossVenueExecutionReplica.vue" not in source
