import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
REPOSITORY_PATH = APP_ROOT / "eod_reconciliation_repository.py"
FACADE_PATH = APP_ROOT / "eod_reconciliation.py"
SERVICE_PATH = APP_ROOT / "eod_reconciliation_service.py"
POLICY_PATH = APP_ROOT / "eod_policy.py"


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_repository_is_the_only_eod_ddl_and_direct_sql_owner() -> None:
    repository_source = REPOSITORY_PATH.read_text(encoding="utf-8")
    facade_source = FACADE_PATH.read_text(encoding="utf-8")
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    policy_source = POLICY_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS eod_reconciliation_reports" in repository_source
    assert "db.execute(" in repository_source
    assert "connection()" in repository_source
    for source in (facade_source, service_source, policy_source):
        assert "CREATE TABLE" not in source
        assert "db.execute(" not in source
        assert "connection()" not in source
        assert "SELECT " not in source
        assert "INSERT " not in source
        assert "UPDATE " not in source


def test_service_and_policy_delegate_to_repository() -> None:
    facade_source = FACADE_PATH.read_text(encoding="utf-8")
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    policy_source = POLICY_PATH.read_text(encoding="utf-8")

    assert "from app import eod_reconciliation_repository as repository" in facade_source
    assert "from app import eod_reconciliation_repository as repository" in service_source
    assert "repository.insert_initial_report(" in service_source
    assert "repository.complete_report(" in service_source
    assert "repository.review_report(" in service_source
    assert "repository.insert_initial_report(" not in facade_source
    assert "repository.review_report(" not in facade_source
    assert "from app import eod_reconciliation_repository as repository" in policy_source
    assert "repository.list_strategy_order_ids(" in policy_source
    assert "repository.historical_difference_counts(" in policy_source
    assert "repository.update_report_gate(" in policy_source


def test_repository_has_no_fastapi_or_cross_domain_orchestration_dependency() -> None:
    imports = imported_modules(REPOSITORY_PATH)
    source = REPOSITORY_PATH.read_text(encoding="utf-8")

    assert "fastapi" not in imports
    assert "app.financial_facts" not in imports
    assert "app.live_venue_accounting" not in imports
    assert "app.venue_reconciliation" not in imports
    assert "HTTPException" not in source
    assert "record_financial_fact" not in source
    assert "reconcile_order_with_venue" not in source
