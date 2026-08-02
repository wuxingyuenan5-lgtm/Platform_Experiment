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


def test_trading_display_pack_uses_formal_cross_venue_owner() -> None:
    source = CONTEXT_TOOL.read_text(encoding="utf-8")
    assert "CrossVenueExecutionWorkspace.vue" in source
    assert "CrossVenueExecutionReplica.vue" not in source
