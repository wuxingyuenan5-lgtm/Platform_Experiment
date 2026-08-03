from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit-production-data-boundaries.py"
POLICY = ROOT / "config" / "production-data-boundary-policy.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("production_data_boundary_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_policy(tmp_path: Path, mutate) -> Path:
    payload = json.loads(POLICY.read_text(encoding="utf-8"))
    mutate(payload)
    target = tmp_path / "policy.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def test_current_production_data_boundaries_are_clean() -> None:
    audit = _load_module()
    result = audit.audit(POLICY)
    assert result["status"] == "ok"
    assert result["scanned_files"] > 0
    assert result["findings"] == []
    assert {item["status"] for item in result["quarantines"]} == {"isolated"}
    assert {
        item["path"] for item in result["explicit_unavailable_views"]
    } == {
        "platform-web/src/views/dashboard/index.vue",
        "platform-web/src/views/financialAi/index.vue",
        "platform-web/src/views/strategy/management/index.vue",
        "platform-web/src/views/strategy/funding-carry/index.vue",
        "platform-web/src/views/strategy/spread-carry/index.vue",
        "platform-web/src/views/newsCalendar/index.vue",
        "platform-web/src/views/settings/index.vue",
    }


def test_random_value_generation_is_rejected(tmp_path: Path) -> None:
    audit = _load_module()
    source = ROOT / "platform-web" / "src" / "views" / "__phase5_boundary_probe__.ts"
    source.write_text("export const price = Math.random();\n", encoding="utf-8")
    try:
        with pytest.raises(audit.AuditError, match="production data boundary violations"):
            audit.audit(POLICY)
    finally:
        source.unlink(missing_ok=True)


def test_quarantine_requires_consumer_guard(tmp_path: Path) -> None:
    audit = _load_module()
    target = _write_policy(
        tmp_path,
        lambda value: value["quarantines"][1].__setitem__(
            "consumer_required_markers",
            ["missing-static-isolation-guard"],
        ),
    )
    with pytest.raises(audit.AuditError, match="missing markers"):
        audit.audit(target)


def test_explicit_unavailable_view_requires_source_marker(tmp_path: Path) -> None:
    audit = _load_module()
    target = _write_policy(
        tmp_path,
        lambda value: value["explicit_unavailable_views"][0].__setitem__(
            "required_markers",
            ["missing-not-configured-source-marker"],
        ),
    )
    with pytest.raises(audit.AuditError, match="missing markers"):
        audit.audit(target)
