import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
REPOSITORY_PATH = APP_ROOT / "venue_reconciliation_repository.py"
SERVICE_PATH = APP_ROOT / "venue_reconciliation_service.py"
FACADE_PATH = APP_ROOT / "venue_reconciliation.py"


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_repository_is_the_only_ddl_and_direct_sql_owner() -> None:
    repository_source = REPOSITORY_PATH.read_text(encoding="utf-8")
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    facade_source = FACADE_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS venue_reconciliation_runs" in repository_source
    assert "CREATE TABLE IF NOT EXISTS reconciliation_differences" in repository_source
    assert "db.execute(" in repository_source
    assert "connection()" in repository_source
    for source in (service_source, facade_source):
        assert "CREATE TABLE" not in source
        assert "db.execute(" not in source
        assert "connection()" not in source
        assert "SELECT " not in source
        assert "INSERT " not in source
        assert "UPDATE " not in source


def test_service_keeps_external_effects_and_facade_keeps_http_mapping() -> None:
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    facade_source = FACADE_PATH.read_text(encoding="utf-8")

    assert "runtime_client.get(" in service_source
    assert "record_financial_fact(" in service_source
    assert "HTTPException(" not in service_source
    assert "from app import venue_reconciliation_repository as repository" in service_source
    assert "from app import venue_reconciliation_runtime_client as runtime_client" in service_source
    assert "HTTPException(" in facade_source
    assert "from app import venue_reconciliation_service as service" in facade_source


def test_repository_has_no_fastapi_httpx_config_or_financial_fact_dependency() -> None:
    imports = imported_modules(REPOSITORY_PATH)
    source = REPOSITORY_PATH.read_text(encoding="utf-8")

    assert "fastapi" not in imports
    assert "httpx" not in imports
    assert "app.config" not in imports
    assert "app.financial_facts" not in imports
    assert "HTTPException" not in source
