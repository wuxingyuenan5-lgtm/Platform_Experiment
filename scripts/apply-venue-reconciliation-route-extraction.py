#!/usr/bin/env python3
"""Mechanically extract Venue reconciliation FastAPI routes from the compatibility facade."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "platform-api/app"
TEST_ROOT = ROOT / "platform-api/tests"
FACADE_PATH = APP_ROOT / "venue_reconciliation.py"
ROUTES_PATH = APP_ROOT / "venue_reconciliation_routes.py"
MAIN_PATH = APP_ROOT / "main.py"
ARCH_TEST_PATH = TEST_ROOT / "test_architecture_venue_reconciliation_service.py"
OWNERSHIP_PATH = ROOT / "docs/architecture/OWNERSHIP.md"

OLD_FASTAPI_IMPORT = "from fastapi import APIRouter, HTTPException\n"
NEW_FASTAPI_IMPORT = "from fastapi import HTTPException\n"
OLD_CONFIG_IMPORT = "from app.config import get_settings\n"
ROUTER_MARKER = "\n\nrouter = APIRouter(prefix=get_settings().api_prefix)\n"
OLD_MAIN_IMPORT = (
    "from app.venue_reconciliation import router as venue_reconciliation_router\n"
)
NEW_MAIN_IMPORT = (
    "from app.venue_reconciliation_routes import router as venue_reconciliation_router\n"
)

OLD_OWNERSHIP_ROW = (
    "| Venue Reconciliation facade | `platform-api/app/venue_reconciliation.py` | "
    "Compatibility exports/delegates, exact domain/transport-error-to-HTTP mapping and "
    "routes pending dedicated route-module extraction | FinancialFact import, "
    "reconciliation sequencing, direct Runtime HTTP, SQL/DDL or duplicate DTO/policy definitions |"
)
NEW_OWNERSHIP_ROWS = """| Venue Reconciliation facade | `platform-api/app/venue_reconciliation.py` | Stable compatibility exports/delegates and exact domain/transport-error-to-HTTP mapping | FastAPI route assembly, FinancialFact import, reconciliation sequencing, direct Runtime HTTP, SQL/DDL or duplicate DTO/policy definitions |
| Venue Reconciliation routes | `platform-api/app/venue_reconciliation_routes.py` | Five Venue HTTP endpoints, response models and delegation to the compatibility facade | Service/Repository/Runtime Client imports, error translation, SQL, FinancialFact import or difference policy |"""

ROUTES_CONTENT = '''from __future__ import annotations

from fastapi import APIRouter

from app import venue_reconciliation as facade
from app.config import get_settings
from app.venue_reconciliation_schemas import (
    OrderVenueReconciliationResponse,
    ReconciliationDifferenceResponse,
    ResolveDifferenceRequest,
    VenueReconciliationRunRequest,
    VenueReconciliationRunResponse,
)

router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/trading/orders/{order_id}/venue-reconcile",
    response_model=OrderVenueReconciliationResponse,
    tags=["venue-reconciliation"],
)
def reconcile_platform_order(order_id: str) -> OrderVenueReconciliationResponse:
    return facade.reconcile_order_with_venue(order_id)


@router.post(
    "/ops/venue-reconciliation/runs",
    response_model=VenueReconciliationRunResponse,
    tags=["venue-reconciliation"],
)
def create_reconciliation_run(
    request: VenueReconciliationRunRequest,
) -> VenueReconciliationRunResponse:
    return facade.run_account_reconciliation(request)


@router.get(
    "/ops/venue-reconciliation/runs/{run_id}",
    response_model=VenueReconciliationRunResponse,
    tags=["venue-reconciliation"],
)
def read_reconciliation_run(run_id: str) -> VenueReconciliationRunResponse:
    return facade.get_run(run_id)


@router.get(
    "/ops/venue-reconciliation/runs/{run_id}/differences",
    response_model=list[ReconciliationDifferenceResponse],
    tags=["venue-reconciliation"],
)
def read_reconciliation_differences(run_id: str) -> list[ReconciliationDifferenceResponse]:
    return facade.list_differences(run_id)


@router.post(
    "/ops/venue-reconciliation/differences/{difference_id}/resolve",
    response_model=ReconciliationDifferenceResponse,
    tags=["venue-reconciliation"],
)
def resolve_reconciliation_difference(
    difference_id: str,
    request: ResolveDifferenceRequest,
) -> ReconciliationDifferenceResponse:
    return facade.resolve_difference(difference_id, request)
'''

ARCH_TEST_CONTENT = '''import ast
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
'''

REQUIRED_ROUTE_FRAGMENTS = (
    '@router.post(\n    "/trading/orders/{order_id}/venue-reconcile",',
    '@router.post(\n    "/ops/venue-reconciliation/runs",',
    '@router.get(\n    "/ops/venue-reconciliation/runs/{run_id}",',
    '@router.get(\n    "/ops/venue-reconciliation/runs/{run_id}/differences",',
    '@router.post(\n    "/ops/venue-reconciliation/differences/{difference_id}/resolve",',
)


def replace_once(content: str, old: str, new: str, label: str) -> str:
    if new in content and old not in content:
        return content
    if content.count(old) != 1:
        raise SystemExit(f"Expected exactly one {label}")
    return content.replace(old, new, 1)


def main() -> None:
    facade = FACADE_PATH.read_text(encoding="utf-8")
    main_source = MAIN_PATH.read_text(encoding="utf-8")
    ownership = OWNERSHIP_PATH.read_text(encoding="utf-8")

    if ROUTES_PATH.exists():
        if ROUTER_MARKER in facade or "@router." in facade:
            raise SystemExit("Dedicated Venue routes exist but facade routes remain")
        if NEW_MAIN_IMPORT not in main_source:
            raise SystemExit("Dedicated Venue routes exist but main import is missing")
        print("Venue route extraction is already applied.")
        return

    for fragment in REQUIRED_ROUTE_FRAGMENTS:
        if facade.count(fragment) != 1:
            raise SystemExit(f"Expected exactly one frozen route fragment: {fragment!r}")
    if facade.count(ROUTER_MARKER) != 1:
        raise SystemExit("Expected exactly one Venue router block")
    if facade.count(OLD_FASTAPI_IMPORT) != 1:
        raise SystemExit("Expected the combined FastAPI import")
    if facade.count(OLD_CONFIG_IMPORT) != 1:
        raise SystemExit("Expected the facade configuration import")

    router_start = facade.index(ROUTER_MARKER)
    facade = facade[:router_start].rstrip() + "\n"
    facade = facade.replace(OLD_FASTAPI_IMPORT, NEW_FASTAPI_IMPORT, 1)
    facade = facade.replace(OLD_CONFIG_IMPORT, "", 1)

    main_source = replace_once(
        main_source,
        OLD_MAIN_IMPORT,
        NEW_MAIN_IMPORT,
        "Venue router composition import",
    )
    ownership = replace_once(
        ownership,
        OLD_OWNERSHIP_ROW,
        NEW_OWNERSHIP_ROWS,
        "Venue ownership row",
    )

    if "APIRouter" in facade or "@router." in facade or "get_settings" in facade:
        raise SystemExit("FastAPI route assembly remains in the Venue facade")
    for compatibility_name in (
        "SCHEMA_SQL = repository.SCHEMA_SQL",
        "ensure_schema = repository.ensure_schema",
        "audit = repository.audit",
        "def _call_service",
        "def runtime_get(",
        "def reconcile_order_with_venue(",
        "def run_account_reconciliation(",
        "def validate_strategy_account(",
        "def get_run(",
        "def list_differences(",
        "def resolve_difference(",
    ):
        if compatibility_name not in facade:
            raise SystemExit(f"Facade compatibility contract changed: {compatibility_name}")

    ROUTES_PATH.write_text(ROUTES_CONTENT, encoding="utf-8")
    FACADE_PATH.write_text(facade, encoding="utf-8")
    MAIN_PATH.write_text(main_source, encoding="utf-8")
    ARCH_TEST_PATH.write_text(ARCH_TEST_CONTENT, encoding="utf-8")
    OWNERSHIP_PATH.write_text(ownership, encoding="utf-8")
    print("Extracted Venue reconciliation routes without moving compatibility or service behavior.")


if __name__ == "__main__":
    main()
