import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SERVICE_PATH = APP_ROOT / "venue_reconciliation_service.py"
FACADE_PATH = APP_ROOT / "venue_reconciliation.py"
ROUTES_PATH = APP_ROOT / "venue_reconciliation_routes.py"
MAIN_PATH = APP_ROOT / "main.py"

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

FACADE_DELEGATES = SERVICE_FUNCTIONS | {"runtime_get"}


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


def test_facade_owns_http_mapping_and_all_compatibility_ports() -> None:
    imports = imported_modules(FACADE_PATH)
    source = FACADE_PATH.read_text(encoding="utf-8")
    functions = function_names(FACADE_PATH)

    assert "fastapi" in imports
    assert "from app import venue_reconciliation_service as service" in source
    assert "def _call_service" in source
    assert "HTTPException(status_code=503" in source
    assert "status_code=422" in source
    assert "status_code=409" in source
    assert "status_code=403" in source
    assert source.count("status_code=404") == 2
    assert FACADE_DELEGATES <= functions

    for compatibility_alias in (
        "SCHEMA_SQL = repository.SCHEMA_SQL",
        "ensure_schema = repository.ensure_schema",
        "audit = repository.audit",
        "create_difference = repository.store_difference",
        "run_from_row = repository.run_from_row",
        "difference_from_row = repository.difference_from_row",
        "now_iso = service.now_iso",
        "canonical_hash = service.canonical_hash",
    ):
        assert compatibility_alias in source

    assert "app.config" not in imports
    assert "APIRouter" not in source
    assert "router =" not in source
    assert "@router." not in source
    assert "get_settings" not in source


def test_routes_own_only_the_exact_venue_http_contract() -> None:
    imports = imported_modules(ROUTES_PATH)
    source = ROUTES_PATH.read_text(encoding="utf-8")
    functions = function_names(ROUTES_PATH)

    assert "fastapi" in imports
    assert "app" in imports
    assert "from app import venue_reconciliation as facade" in source
    assert "app.config" in imports
    assert {
        "reconcile_platform_order",
        "create_reconciliation_run",
        "read_reconciliation_run",
        "read_reconciliation_differences",
        "resolve_reconciliation_difference",
    } <= functions
    assert source.count("@router.post(") == 3
    assert source.count("@router.get(") == 2
    assert '"/trading/orders/{order_id}/venue-reconcile"' in source
    assert '"/ops/venue-reconciliation/runs"' in source
    assert '"/ops/venue-reconciliation/runs/{run_id}"' in source
    assert '"/ops/venue-reconciliation/runs/{run_id}/differences"' in source
    assert '"/ops/venue-reconciliation/differences/{difference_id}/resolve"' in source
    assert source.count('tags=["venue-reconciliation"]') == 5
    assert "response_model=OrderVenueReconciliationResponse" in source
    assert source.count("response_model=VenueReconciliationRunResponse") == 2
    assert "response_model=list[ReconciliationDifferenceResponse]" in source
    assert "response_model=ReconciliationDifferenceResponse" in source
    assert "facade.reconcile_order_with_venue(order_id)" in source
    assert "facade.run_account_reconciliation(request)" in source
    assert "facade.get_run(run_id)" in source
    assert "facade.list_differences(run_id)" in source
    assert "facade.resolve_difference(difference_id, request)" in source

    for forbidden in (
        "venue_reconciliation_service",
        "venue_reconciliation_repository",
        "venue_reconciliation_runtime_client",
        "HTTPException",
        "record_financial_fact",
        "apply_execution_events",
        "connection()",
        "db.execute(",
        "SELECT ",
        "INSERT ",
        "UPDATE ",
    ):
        assert forbidden not in source


def test_composition_root_imports_the_dedicated_venue_router() -> None:
    source = MAIN_PATH.read_text(encoding="utf-8")

    assert (
        "from app.venue_reconciliation_routes import router as venue_reconciliation_router"
        in source
    )
    assert "from app.venue_reconciliation import router" not in source
    assert source.count("app.include_router(venue_reconciliation_router)") == 1
