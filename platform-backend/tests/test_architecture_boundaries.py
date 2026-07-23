from __future__ import annotations

import ast
from pathlib import Path

from app.auth import permission_for_request

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def function_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]


def test_composition_root_only_wires_application_components() -> None:
    source = (BACKEND_ROOT / "app/main.py").read_text(encoding="utf-8")
    forbidden_assignments = (
        "execution_risk.calculate_residual_exposure =",
        "eod_reconciliation.list_strategy_orders =",
        "eod_reconciliation.create_eod_report =",
        "auth.permission_for_request =",
    )
    assert all(marker not in source for marker in forbidden_assignments)


def test_residual_exposure_has_one_authoritative_implementation() -> None:
    risk_functions = function_names(BACKEND_ROOT / "app/execution_risk.py")
    exposure_functions = function_names(BACKEND_ROOT / "app/execution_exposure.py")
    assert "calculate_residual_exposure" not in risk_functions
    assert exposure_functions.count("calculate_residual_exposure") == 1


def test_eod_policy_is_an_explicit_dependency() -> None:
    source = (BACKEND_ROOT / "app/eod_reconciliation.py").read_text(encoding="utf-8")
    assert "from app.eod_policy import" in source
    assert "list_strategy_orders_for_eod(" in source
    assert "def list_strategy_orders(" not in source


def test_production_operations_permissions_live_in_auth_policy() -> None:
    assert permission_for_request("GET", "/api/v1/ops/production-status") == "audit:read"
    assert permission_for_request("GET", "/api/v1/security/credential-rotations") == "audit:read"
    assert permission_for_request("POST", "/api/v1/ops/alerts/scan") == "operations:run"
    assert (
        permission_for_request("POST", "/api/v1/ops/alerts/alert-1/acknowledge")
        == "reconciliation:review"
    )
