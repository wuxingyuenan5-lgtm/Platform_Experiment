import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
CLIENT_PATH = APP_ROOT / "venue_reconciliation_runtime_client.py"
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


def test_runtime_client_is_the_only_reconciliation_http_transport_owner() -> None:
    client_source = CLIENT_PATH.read_text(encoding="utf-8")
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    facade_source = FACADE_PATH.read_text(encoding="utf-8")

    assert "httpx.get(" in client_source
    assert "settings.runtime_base_url" in client_source
    assert "settings.runtime_timeout_seconds" in client_source
    assert "httpx.get(" not in service_source
    assert "httpx.get(" not in facade_source
    assert "import httpx" not in service_source
    assert "import httpx" not in facade_source
    assert "runtime_client.get(" in service_source
    assert "service.runtime_get" in facade_source


def test_runtime_client_has_only_transport_configuration_dependencies() -> None:
    imports = imported_modules(CLIENT_PATH)
    source = CLIENT_PATH.read_text(encoding="utf-8")

    assert imports <= {"__future__", "httpx", "app.config"}
    assert "fastapi" not in imports
    assert "app.database" not in imports
    assert "app.financial_facts" not in imports
    assert "venue_reconciliation_repository" not in source
    assert "venue_reconciliation_policy" not in source


def test_facade_retains_http_error_mapping_compatibility_delegate() -> None:
    source = FACADE_PATH.read_text(encoding="utf-8")

    assert "def runtime_get(" in source
    assert "except runtime_client.RuntimeQueryError as exc:" in source
    assert 'detail="Platform Execution Runtime query failed"' in source
