#!/usr/bin/env python3
"""Mechanically extract EOD reconciliation FastAPI routes from the compatibility facade."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "platform-api/app"
TEST_ROOT = ROOT / "platform-api/tests"
FACADE_PATH = APP_ROOT / "eod_reconciliation.py"
ROUTES_PATH = APP_ROOT / "eod_reconciliation_routes.py"
MAIN_PATH = APP_ROOT / "main.py"
ARCH_TEST_PATH = TEST_ROOT / "test_architecture_eod_reconciliation_service.py"
OWNERSHIP_PATH = ROOT / "docs/architecture/OWNERSHIP.md"

OLD_FASTAPI_IMPORT = "from fastapi import APIRouter, HTTPException, Query\n"
NEW_FASTAPI_IMPORT = "from fastapi import HTTPException\n"
OLD_CONFIG_IMPORT = "from app.config import get_settings\n"
ROUTER_MARKER = "\n\nrouter = APIRouter(prefix=get_settings().api_prefix)\n"
OLD_MAIN_IMPORT = (
    "from app.eod_reconciliation import router as eod_reconciliation_router\n"
)
NEW_MAIN_IMPORT = (
    "from app.eod_reconciliation_routes import router as eod_reconciliation_router\n"
)

OLD_OWNERSHIP_ROW = (
    "| EOD Reconciliation facade | `platform-api/app/eod_reconciliation.py` | "
    "Per-call dependency wiring, compatibility delegates, exact service-error-to-HTTP "
    "mapping and routes pending dedicated route-module extraction | Cross-domain use-case "
    "sequencing, direct SQL/DDL or duplicate Policy decisions |"
)
NEW_OWNERSHIP_ROWS = """| EOD Reconciliation facade | `platform-api/app/eod_reconciliation.py` | Per-call dependency wiring, stable compatibility delegates and exact service-error-to-HTTP mapping | FastAPI route assembly, cross-domain use-case sequencing, direct SQL/DDL or duplicate Policy decisions |
| EOD Reconciliation routes | `platform-api/app/eod_reconciliation_routes.py` | Four EOD HTTP endpoints, response models and stable query aliases delegated to the facade | Service/Repository imports, dependency wiring, error translation, SQL or report policy |"""

ROUTES_CONTENT = '''from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app import eod_reconciliation as facade
from app.config import get_settings
from app.eod_reconciliation_schemas import (
    EodReconciliationReportRequest,
    EodReconciliationReportResponse,
    EodReconciliationReviewRequest,
)

router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/ops/eod-reconciliation/reports",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def create_report(
    request: EodReconciliationReportRequest,
) -> EodReconciliationReportResponse:
    return facade.create_eod_report(request)


@router.get(
    "/ops/eod-reconciliation/reports/{report_id}",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def read_report(report_id: str) -> EodReconciliationReportResponse:
    return facade.get_eod_report(report_id)


@router.get(
    "/ops/eod-reconciliation/reports",
    response_model=list[EodReconciliationReportResponse],
    tags=["eod-reconciliation"],
)
def read_reports(
    strategy_instance_id: str | None = Query(default=None, alias="strategyInstanceId"),
    account_id: str | None = Query(default=None, alias="accountId"),
    business_date: date | None = Query(default=None, alias="businessDate"),
) -> list[EodReconciliationReportResponse]:
    return facade.list_eod_reports(strategy_instance_id, account_id, business_date)


@router.post(
    "/ops/eod-reconciliation/reports/{report_id}/review",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def review_report(
    report_id: str,
    request: EodReconciliationReviewRequest,
) -> EodReconciliationReportResponse:
    return facade.review_eod_report(report_id, request)
'''

ARCH_TEST_CONTENT = '''import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SERVICE_PATH = APP_ROOT / "eod_reconciliation_service.py"
FACADE_PATH = APP_ROOT / "eod_reconciliation.py"
ROUTES_PATH = APP_ROOT / "eod_reconciliation_routes.py"
MAIN_PATH = APP_ROOT / "main.py"


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
    assert "app.eod_reconciliation" in imports
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
    assert source.count("app.include_router(eod_reconciliation_router)") == 1
'''

REQUIRED_ROUTE_FRAGMENTS = (
    '@router.post(\n    "/ops/eod-reconciliation/reports",',
    '@router.get(\n    "/ops/eod-reconciliation/reports/{report_id}",',
    '@router.get(\n    "/ops/eod-reconciliation/reports",',
    '@router.post(\n    "/ops/eod-reconciliation/reports/{report_id}/review",',
    'alias="strategyInstanceId"',
    'alias="accountId"',
    'alias="businessDate"',
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
            raise SystemExit("Dedicated EOD routes exist but facade routes remain")
        if NEW_MAIN_IMPORT not in main_source:
            raise SystemExit("Dedicated EOD routes exist but main import is missing")
        print("EOD route extraction is already applied.")
        return

    for fragment in REQUIRED_ROUTE_FRAGMENTS:
        if facade.count(fragment) != 1:
            raise SystemExit(f"Expected exactly one frozen route fragment: {fragment!r}")
    if facade.count(ROUTER_MARKER) != 1:
        raise SystemExit("Expected exactly one EOD router block")
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
        "EOD router composition import",
    )
    ownership = replace_once(
        ownership,
        OLD_OWNERSHIP_ROW,
        NEW_OWNERSHIP_ROWS,
        "EOD ownership row",
    )

    if "APIRouter" in facade or "Query(" in facade or "@router." in facade:
        raise SystemExit("FastAPI route assembly remains in the EOD facade")
    for compatibility_name in (
        "list_strategy_orders = list_strategy_orders_for_eod",
        "def _service_dependencies()",
        "def _call_service",
        "def create_eod_report(",
        "def get_eod_report(",
        "def list_eod_reports(",
        "def review_eod_report(",
    ):
        if compatibility_name not in facade:
            raise SystemExit(f"Facade compatibility contract changed: {compatibility_name}")

    ROUTES_PATH.write_text(ROUTES_CONTENT, encoding="utf-8")
    FACADE_PATH.write_text(facade, encoding="utf-8")
    MAIN_PATH.write_text(main_source, encoding="utf-8")
    ARCH_TEST_PATH.write_text(ARCH_TEST_CONTENT, encoding="utf-8")
    OWNERSHIP_PATH.write_text(ownership, encoding="utf-8")
    print("Extracted EOD reconciliation routes without moving facade or service behavior.")


if __name__ == "__main__":
    main()
