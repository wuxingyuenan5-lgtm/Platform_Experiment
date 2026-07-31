import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "venue_reconciliation_policy.py"
SERVICE_PATH = APP_ROOT / "venue_reconciliation_service.py"
FACADE_PATH = APP_ROOT / "venue_reconciliation.py"
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
    service_functions = function_names(SERVICE_PATH)
    facade_functions = function_names(FACADE_PATH)

    assert POLICY_FUNCTIONS <= owner_functions
    assert not (POLICY_FUNCTIONS & service_functions)
    assert not (POLICY_FUNCTIONS & facade_functions)


def test_service_imports_policy_and_facade_delegates_use_cases() -> None:
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    facade_source = FACADE_PATH.read_text(encoding="utf-8")

    assert "from app.venue_reconciliation_policy import (" in service_source
    assert "persist_difference_draft" in service_source
    assert "from app import venue_reconciliation_repository as repository" in service_source
    assert "from app import venue_reconciliation_runtime_client as runtime_client" in service_source
    assert "runtime_client.get(" in service_source
    assert "from app import venue_reconciliation_service as service" in facade_source
    assert "record_financial_fact(" not in facade_source
    assert "connection()" not in service_source
    assert "connection()" not in facade_source
    assert "INSERT OR IGNORE INTO reconciliation_differences" not in service_source
    assert "INSERT OR IGNORE INTO reconciliation_differences" not in facade_source


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
