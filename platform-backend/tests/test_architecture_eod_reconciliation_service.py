import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SERVICE_PATH = APP_ROOT / "eod_reconciliation_service.py"
FACADE_PATH = APP_ROOT / "eod_reconciliation.py"


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


def test_service_owns_eod_use_case_implementation() -> None:
    service_functions = function_names(SERVICE_PATH)
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    facade_source = FACADE_PATH.read_text(encoding="utf-8")

    assert {
        "create_eod_report",
        "get_eod_report",
        "list_eod_reports",
        "review_eod_report",
        "canonical_hash",
        "natural_key",
    } <= service_functions
    assert "repository.insert_initial_report(" in service_source
    assert "dependencies.run_account_reconciliation(" in service_source
    assert "dependencies.import_live_economic_events(" in service_source
    assert "dependencies.run_formal_nav_snapshot(" in service_source
    assert "order:{order_id}:{type(exc).__name__}:{exc}" in service_source
    assert "repository.insert_initial_report(" not in facade_source
    assert "repository.review_report(" not in facade_source
    assert "account-reconciliation:{type(exc).__name__}:{exc}" not in facade_source


def test_service_has_no_fastapi_configuration_or_route_dependency() -> None:
    imports = imported_modules(SERVICE_PATH)
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "fastapi" not in imports
    assert "app.config" not in imports
    assert "APIRouter" not in source
    assert "HTTPException" not in source
    assert "Query(" not in source
    assert "get_settings" not in source


def test_facade_keeps_routes_http_mapping_and_per_call_dependency_wiring() -> None:
    source = FACADE_PATH.read_text(encoding="utf-8")

    assert "from app import eod_reconciliation_service as service" in source
    assert "def _service_dependencies()" in source
    assert "validate_strategy_account=validate_strategy_account" in source
    assert "list_strategy_orders=list_strategy_orders" in source
    assert "reconcile_order_with_venue=reconcile_order_with_venue" in source
    assert "run_account_reconciliation=run_account_reconciliation" in source
    assert "import_live_economic_events=import_live_economic_events" in source
    assert "def _call_service" in source
    assert "APIRouter(" in source
    assert "HTTPException(" in source
    assert "@router.post(" in source
    assert "@router.get(" in source
