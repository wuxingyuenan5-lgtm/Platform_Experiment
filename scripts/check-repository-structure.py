"""Fail CI when repository structure or architectural safety boundaries regress."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "platform-backend" / "app"
TEST_ROOTS = (
    ROOT / "platform-backend" / "tests",
    ROOT / "execution-runtime" / "tests",
)
WORKFLOW_ROOT = ROOT / ".github" / "workflows"

FORBIDDEN_BACKEND_IMPORTS = {
    "MetaTrader5",
    "binance",
    "ccxt",
    "ib_insync",
    "pybit",
}
FORBIDDEN_TEST_NAME = re.compile(
    r"^test_.+_(?:backup|copy|final|new|old|temp|tmp)\.py$",
    re.IGNORECASE,
)
FORBIDDEN_WORKFLOW_NAME = re.compile(
    r"(?:^|[-_])(?:capture|debug|fix-once|one-time|once)(?:[-_]|\.)",
    re.IGNORECASE,
)
ALLOWED_COMPOSITION_CALLS = {"add_middleware", "include_router"}
EXECUTION_SCHEMA_NAMES = {
    "BatchLegRequest",
    "BatchLegResponse",
    "CreateExecutionBatchRequest",
    "CreateOrderRequest",
    "CreateStrategyRunRequest",
    "ExecutionBatchResponse",
    "OrderResponse",
    "PnlResponse",
    "PositionResponse",
    "StrategyRunResponse",
    "StrategyV1ReadinessResponse",
}
OPERATIONAL_PROJECTION_WRITE_ANCHORS = {
    "INSERT INTO positions",
    "INSERT INTO pnl_results",
}
FORMAL_PROJECTION_WRITES = {
    "INSERT INTO financial_facts",
    "INSERT INTO formal_positions",
    "UPDATE formal_positions",
    "INSERT INTO formal_pnl_results",
    "UPDATE formal_pnl_results",
}
OPERATIONAL_PROJECTION_READS = {
    "FROM positions",
    "FROM pnl_results",
}


def parsed_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_top_levels(path: Path) -> set[str]:
    tree = parsed_module(path)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return imports


def check_backend_venue_boundary(errors: list[str]) -> None:
    for path in sorted(BACKEND_APP.rglob("*.py")):
        forbidden = imported_top_levels(path) & FORBIDDEN_BACKEND_IMPORTS
        if forbidden:
            relative = path.relative_to(ROOT)
            errors.append(
                f"{relative}: backend imports venue SDK(s) {sorted(forbidden)}; "
                "external execution belongs in execution-runtime"
            )


def is_allowed_composition_call(node: ast.Expr) -> bool:
    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return True
    if not isinstance(node.value, ast.Call):
        return False
    function = node.value.func
    return (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "app"
        and function.attr in ALLOWED_COMPOSITION_CALLS
    )


def check_composition_root(errors: list[str]) -> None:
    path = BACKEND_APP / "main.py"
    tree = parsed_module(path)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and is_allowed_composition_call(node):
            continue
        if isinstance(node, ast.Assign) and all(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        errors.append(
            "platform-backend/app/main.py: composition root may only import, "
            "wire routers/middleware, and define __all__"
        )
        break


def check_execution_schema_boundary(errors: list[str]) -> None:
    compatibility_path = BACKEND_APP / "schemas.py"
    compatibility_tree = parsed_module(compatibility_path)
    duplicate_types = {
        node.name
        for node in compatibility_tree.body
        if isinstance(node, ast.ClassDef) and node.name in EXECUTION_SCHEMA_NAMES
    }
    if duplicate_types:
        errors.append(
            "platform-backend/app/schemas.py: execution API schemas must be re-exported "
            f"from execution_schemas.py, not redefined: {sorted(duplicate_types)}"
        )

    import_names: set[str] = set()
    for node in compatibility_tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "app.execution_schemas":
            import_names.update(alias.name for alias in node.names)
    missing_exports = EXECUTION_SCHEMA_NAMES - import_names
    if missing_exports:
        errors.append(
            "platform-backend/app/schemas.py: missing compatibility exports from "
            f"execution_schemas.py: {sorted(missing_exports)}"
        )


def check_projection_boundaries(errors: list[str]) -> None:
    trading_path = BACKEND_APP / "trading.py"
    trading_source = trading_path.read_text(encoding="utf-8")
    trading_functions = {
        node.name
        for node in parsed_module(trading_path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if "record_fill_and_update_operational_projections" not in trading_functions:
        errors.append(
            "platform-backend/app/trading.py: fill projection function must be named "
            "record_fill_and_update_operational_projections"
        )
    if "record_fill_and_update_projections" in trading_functions:
        errors.append(
            "platform-backend/app/trading.py: ambiguous projection function name is forbidden"
        )
    missing_operational_writes = OPERATIONAL_PROJECTION_WRITE_ANCHORS - {
        statement
        for statement in OPERATIONAL_PROJECTION_WRITE_ANCHORS
        if statement in trading_source
    }
    if missing_operational_writes:
        errors.append(
            "platform-backend/app/trading.py: expected operational projection writes are missing: "
            f"{sorted(missing_operational_writes)}"
        )
    forbidden_formal_writes = {
        statement for statement in FORMAL_PROJECTION_WRITES if statement in trading_source
    }
    if forbidden_formal_writes:
        errors.append(
            "platform-backend/app/trading.py: trading flow must not write formal accounting tables: "
            f"{sorted(forbidden_formal_writes)}"
        )

    financial_source = (BACKEND_APP / "financial_facts.py").read_text(encoding="utf-8")
    forbidden_operational_reads = {
        statement for statement in OPERATIONAL_PROJECTION_READS if statement in financial_source
    }
    if forbidden_operational_reads:
        errors.append(
            "platform-backend/app/financial_facts.py: formal accounting must not read "
            f"operational projection tables: {sorted(forbidden_operational_reads)}"
        )


def check_test_names(errors: list[str]) -> None:
    for root in TEST_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if FORBIDDEN_TEST_NAME.match(path.name):
                errors.append(
                    f"{path.relative_to(ROOT)}: temporary/versioned test suffix is forbidden; "
                    "merge the scenario into the canonical suite or use a domain-specific name"
                )


def check_workflow_names(errors: list[str]) -> None:
    for path in sorted(WORKFLOW_ROOT.glob("*.yml")):
        if FORBIDDEN_WORKFLOW_NAME.search(path.name):
            errors.append(
                f"{path.relative_to(ROOT)}: temporary diagnostic workflow must not be committed"
            )


def main() -> int:
    errors: list[str] = []
    check_backend_venue_boundary(errors)
    check_composition_root(errors)
    check_execution_schema_boundary(errors)
    check_projection_boundaries(errors)
    check_test_names(errors)
    check_workflow_names(errors)
    if errors:
        print("Repository structure check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Repository structure check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
