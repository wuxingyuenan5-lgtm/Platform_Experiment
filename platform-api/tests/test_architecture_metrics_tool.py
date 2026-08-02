from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analyze-architecture.py"
SPEC = importlib.util.spec_from_file_location("analyze_architecture", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
analyze_architecture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = analyze_architecture
SPEC.loader.exec_module(analyze_architecture)


def test_architecture_reports_are_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    analyze_architecture.write_reports(first, analyze_architecture.collect())
    analyze_architecture.write_reports(second, analyze_architecture.collect())

    first_files = sorted(path.name for path in first.iterdir())
    second_files = sorted(path.name for path in second.iterdir())
    assert first_files == second_files
    assert first_files == [
        "platform-0-9-3-phase-4-before-metrics.json",
        "platform-0-9-3-phase-4-compatibility-inventory.json",
        "platform-0-9-3-phase-4-contract-inventory.json",
        "platform-0-9-3-phase-4-hotspots.json",
        "platform-0-9-3-phase-4-import-graph.json",
        "platform-0-9-3-phase-4-type-debt.json",
    ]
    for name in first_files:
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_architecture_reports_separate_production_totals(tmp_path: Path) -> None:
    analyze_architecture.write_reports(tmp_path, analyze_architecture.collect())

    payload = json.loads(
        (tmp_path / "platform-0-9-3-phase-4-before-metrics.json").read_text(encoding="utf-8")
    )
    totals = payload["totals"]
    assert totals["production_files"] > 0
    assert totals["production_lines"] > totals["production_files"]
    assert totals["production_bytes"] > totals["production_lines"]
