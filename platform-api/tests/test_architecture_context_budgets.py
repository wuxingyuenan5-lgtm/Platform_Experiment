from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/context-for.py"
BUDGET_MANIFEST = ROOT / "docs/codex/context-budgets.json"


def load_context_tool():
    spec = importlib.util.spec_from_file_location("context_for", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_budget_manifest_matches_executable_budget_registry() -> None:
    tool = load_context_tool()
    payload = json.loads(BUDGET_MANIFEST.read_text(encoding="utf-8"))
    expected = {
        name: {
            "required_tokens": budget[0],
            "optional_tokens": budget[1],
        }
        for name, budget in sorted(tool.PACK_BUDGETS.items())
    }

    assert payload["schema_version"] == 1
    assert payload["packs"] == expected
    assert all(
        set(values) == {"required_tokens", "optional_tokens"}
        for values in payload["packs"].values()
    )


def test_all_context_packs_have_bounded_existing_paths() -> None:
    tool = load_context_tool()
    report = tool.budget_report()

    assert report["ok"] is True
    assert report["failures"] == []
    assert report["unbudgeted_packs"] == []
    assert report["orphan_budgets"] == []
    assert set(report["packs"]) == set(tool.PACKS)
    for pack in report["packs"].values():
        assert pack["missing_paths"] == []
        assert pack["required"]["over_budget"] is False
        assert pack["optional"]["over_budget"] is False


def test_default_startup_is_below_four_thousand_tokens() -> None:
    tool = load_context_tool()
    startup = tool.default_startup_report()

    assert startup["missing_paths"] == []
    assert startup["budget_tokens"] == 4_000
    assert startup["maximum_estimated_tokens"] <= 4_000
    assert startup["over_budget"] is False


def test_machine_readable_budget_output_is_stable() -> None:
    command = [sys.executable, str(SCRIPT), "--check-budgets", "--json"]
    first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)

    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert payload["schema_version"] == 1
    assert payload["ok"] is True
    assert sorted(payload["packs"]) == sorted(load_context_tool().PACKS)


def test_new_pack_without_budget_is_rejected() -> None:
    tool = load_context_tool()
    original = dict(tool.PACKS)
    tool.PACKS["unbudgeted-fixture"] = replace(
        next(iter(original.values())),
        description="test-only unbudgeted pack",
    )
    try:
        report = tool.budget_report()
    finally:
        tool.PACKS.clear()
        tool.PACKS.update(original)

    assert report["ok"] is False
    assert report["unbudgeted_packs"] == ["unbudgeted-fixture"]
    assert any("packs without budgets" in failure for failure in report["failures"])
