import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "venue_reconciliation_policy.py"
ORCHESTRATION_PATH = APP_ROOT / "venue_reconciliation.py"
POLICY_FUNCTIONS = {
    "balance_difference_drafts",
    "expected_order_status",
    "external_order_update_status",
    "order_difference_draft",
    "order_difference_drafts",
    "position_difference_drafts",
}


def function_names(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_difference_policy_is_the_only_decision_function_owner() -> None:
    owner_functions = function_names(OWNER_PATH)
    orchestration_functions = function_names(ORCHESTRATION_PATH)

    assert POLICY_FUNCTIONS <= owner_functions
    assert not (POLICY_FUNCTIONS & orchestration_functions)


def test_orchestration_imports_policy_and_delegates_persistence_effects() -> None:
    source = ORCHESTRATION_PATH.read_text(encoding="utf-8")

    assert "from app.venue_reconciliation_policy import (" in source
    assert "persist_difference_draft" in source
    assert "from app import venue_reconciliation_repository as repository" in source
    assert "httpx.get(" in source
    assert "connection()" not in source
    assert "INSERT OR IGNORE INTO reconciliation_differences" not in source


def test_policy_has_no_framework_database_or_network_dependency() -> None:
    imports = imported_modules(OWNER_PATH)
    source = OWNER_PATH.read_text(encoding="utf-8")

    assert imports <= {
        "__future__",
        "dataclasses",
        "decimal",
        "app.venue_reconciliation_schemas",
    }
    assert "fastapi" not in source
    assert "httpx" not in source
    assert "connection" not in source
    assert "SELECT " not in source
    assert "INSERT " not in source
    assert "UPDATE " not in source
