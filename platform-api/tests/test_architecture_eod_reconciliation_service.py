import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SERVICE_PATH = APP_ROOT / "eod_reconciliation_service.py"
FACADE_PATH = APP_ROOT / "eod_reconciliation.py"
ROUTES_PATH = APP_ROOT / "eod_reconciliation_routes.py"
MAIN_PATH = APP_ROOT / "application.py"


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


def test_facade_keeps_http_mapping_compatibility_and_dependency_wiring() -> None:
    imports = imported_modules(FACADE_PATH)
    source = FACADE_PATH.read_text(encoding="utf-8")
    functions = function_names(FACADE_PATH)

    assert "from app import eod_reconciliation_service as service" in source
    assert "def _service_dependencies()" in source
    assert "validate_strategy_account=validate_strategy_account" in source
    assert "list_strategy_orders=list_strategy_orders" in source
    assert "reconcile_order_with_venue=reconcile_order_with_venue" in source
    assert "run_account_reconciliation=run_account_reconciliation" in source
    assert "import_live_economic_events=import_live_economic_events" in source
    assert "def _call_service" in source
    assert "HTTPException(" in source
    assert {
        "create_eod_report",
        "get_eod_report",
        "list_eod_reports",
        "review_eod_report",
    } <= functions

    assert "fastapi" in imports
    assert "app.config" not in imports
    assert "APIRouter" not in source
    assert "Query(" not in source
    assert "@router." not in source
    assert "get_settings" not in source


def test_routes_own_only_the_exact_eod_http_contract() -> None:
    imports = imported_modules(ROUTES_PATH)
    source = ROUTES_PATH.read_text(encoding="utf-8")
    functions = function_names(ROUTES_PATH)

    assert "fastapi" in imports
    assert "app" in imports
    assert "from app import eod_reconciliation as facade" in source
    assert "app.config" in imports
    assert {
        "create_report",
        "read_report",
        "read_reports",
        "review_report",
    } <= functions
    assert source.count("@router.post(") == 2
    assert source.count("@router.get(") == 2
    assert '"/ops/eod-reconciliation/reports"' in source
    assert '"/ops/eod-reconciliation/reports/{report_id}"' in source
    assert '"/ops/eod-reconciliation/reports/{report_id}/review"' in source
    assert 'alias="strategyInstanceId"' in source
    assert 'alias="accountId"' in source
    assert 'alias="businessDate"' in source
    assert source.count("response_model=EodReconciliationReportResponse") == 3
    assert "response_model=list[EodReconciliationReportResponse]" in source
    assert source.count('tags=["eod-reconciliation"]') == 4
    assert "facade.create_eod_report(request)" in source
    assert "facade.get_eod_report(report_id)" in source
    assert "facade.list_eod_reports(" in source
    assert "facade.review_eod_report(report_id, request)" in source

    for forbidden in (
        "eod_reconciliation_service",
        "eod_reconciliation_repository",
        "HTTPException",
        "_service_dependencies",
        "connection()",
        "db.execute(",
        "SELECT ",
        "INSERT ",
        "UPDATE ",
    ):
        assert forbidden not in source


def test_composition_root_imports_the_dedicated_eod_router() -> None:
    source = MAIN_PATH.read_text(encoding="utf-8")

    assert (
        "from app.eod_reconciliation_routes import router as eod_reconciliation_router"
        in source
    )
    assert "from app.eod_reconciliation import router" not in source
    assert source.count("application.include_router(eod_reconciliation_router)") == 1
