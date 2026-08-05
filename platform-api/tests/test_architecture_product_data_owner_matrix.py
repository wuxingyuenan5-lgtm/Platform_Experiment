from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit-product-data-owner-matrix.py"
MATRIX = ROOT / "config" / "product-data-owner-matrix.json"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("product_data_owner_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_matrix(tmp_path: Path, mutate) -> Path:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    mutate(payload)
    target = tmp_path / "matrix.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def test_current_product_data_owner_matrix_is_closed_and_covers_formal_views() -> None:
    audit = _load_audit_module()
    result = audit.audit(MATRIX, require_closed=True)
    assert result["status"] == "ok"
    assert result["formal_routes"] == 30
    assert result["route_names"] == 30
    assert result["entries"] == 19
    assert result["unique_views"] == 19
    assert result["closure"].get("gap", 0) == 0
    assert "evidence_debt" not in result


def test_missing_formal_route_is_rejected(tmp_path: Path) -> None:
    audit = _load_audit_module()
    target = _write_matrix(tmp_path, lambda value: value["entries"][0]["routes"].clear())
    with pytest.raises(audit.AuditError, match="routes must be a non-empty list"):
        audit.audit(target, require_closed=True)


def test_registry_cannot_enable_live_write(tmp_path: Path) -> None:
    audit = _load_audit_module()
    target = _write_matrix(
        tmp_path,
        lambda value: value["entries"][0].__setitem__("live_write", True),
    )
    with pytest.raises(audit.AuditError, match="must not enable Live Write"):
        audit.audit(target, require_closed=True)


def test_require_closed_rejects_unresolved_product_gap(tmp_path: Path) -> None:
    audit = _load_audit_module()

    def add_unresolved_gap(value: dict) -> None:
        account = next(entry for entry in value["entries"] if entry["module"] == "account")
        account["closure_status"] = "gap"
        account["gap_reason"] = "test unresolved account owner"

    target = _write_matrix(tmp_path, add_unresolved_gap)
    with pytest.raises(audit.AuditError, match="unresolved product/data gap"):
        audit.audit(target, require_closed=True)


def test_historical_evidence_fields_are_rejected(tmp_path: Path) -> None:
    audit = _load_audit_module()
    target = _write_matrix(
        tmp_path,
        lambda value: value.__setitem__("generated_from_head", "deadbeef"),
    )
    with pytest.raises(audit.AuditError, match="contains historical fields"):
        audit.audit(target, require_closed=True)


def test_nonexistent_repository_owner_path_is_rejected(tmp_path: Path) -> None:
    audit = _load_audit_module()

    def break_owner(value: dict) -> None:
        account = next(entry for entry in value["entries"] if entry["module"] == "account")
        account["frontend_services"] = ["platform-web/src/api/does-not-exist.ts"]

    target = _write_matrix(tmp_path, break_owner)
    with pytest.raises(audit.AuditError, match="path does not exist"):
        audit.audit(target, require_closed=True)
