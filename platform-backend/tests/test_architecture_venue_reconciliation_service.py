import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SERVICE_PATH = APP_ROOT / "venue_reconciliation_service.py"
FACADE_PATH = APP_ROOT / "venue_reconciliation.py"

SERVICE_FUNCTIONS = {
    "compare_balance",
    "compare_order",
    "compare_position",
    "get_run",
    "list_differences",
    "persist_difference_draft",
    "persist_standalone_order_difference",
    "reconcile_order_with_venue",
    "resolve_difference",
    "run_account_reconciliation",
    "standalone_order_difference",
    "strategy_for_order",
    "update_order_from_external",
    "validate_strategy_account",
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


def test_service_is_the_use_case_implementation_owner() -> None:
    service_functions = function_names(SERVICE_PATH)
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    facade_source = FACADE_PATH.read_text(encoding="utf-8")

    assert SERVICE_FUNCTIONS <= service_functions
    assert "record_financial_fact(" in service_source
    assert "apply_execution_events(" in service_source
    assert "repository.create_account_snapshot_run(" in service_source
    assert "service.reconcile_order_with_venue" in facade_source
    assert "service.run_account_reconciliation" in facade_source
    assert "record_financial_fact(" not in facade_source
    assert "apply_execution_events(" not in facade_source
    assert "repository.create_account_snapshot_run(" not in facade_source


def test_service_has_no_fastapi_configured_http_or_direct_sql_dependency() -> None:
    imports = imported_modules(SERVICE_PATH)
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "fastapi" not in imports
    assert "app.config" not in imports
    assert "httpx" not in imports
    assert "APIRouter" not in source
    assert "HTTPException" not in source
    assert "httpx.get(" not in source
    assert "connection()" not in source
    assert "db.execute(" not in source
    assert "SELECT " not in source
    assert "INSERT " not in source
    assert "UPDATE " not in source


def test_facade_owns_http_mapping_compatibility_and_routes() -> None:
    imports = imported_modules(FACADE_PATH)
    source = FACADE_PATH.read_text(encoding="utf-8")

    assert "fastapi" in imports
    assert "app.venue_reconciliation_service" in imports
    assert "def _call_service(" in source
    assert "HTTPException(status_code=503" in source
    assert "status_code=422" in source
    assert "status_code=409" in source
    assert "status_code=403" in source
    assert "status_code=404" in source
    assert "router = APIRouter(" in source
    assert "@router.post(" in source
    assert "@router.get(" in source
