import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
POLICY_PATH = APP_ROOT / "eod_reconciliation_policy.py"
FACADE_PATH = APP_ROOT / "eod_reconciliation.py"
SERVICE_PATH = APP_ROOT / "eod_reconciliation_service.py"
REPOSITORY_PATH = APP_ROOT / "eod_reconciliation_repository.py"
OPERATIONAL_POLICY_PATH = APP_ROOT / "eod_policy.py"
DECISION_FUNCTIONS = {
    "historical_difference_disposition",
    "report_disposition",
    "review_disposition",
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


def test_policy_is_the_only_decision_function_owner() -> None:
    assert DECISION_FUNCTIONS <= function_names(POLICY_PATH)
    for path in (FACADE_PATH, SERVICE_PATH, REPOSITORY_PATH, OPERATIONAL_POLICY_PATH):
        assert not (DECISION_FUNCTIONS & function_names(path))


def test_policy_has_no_framework_persistence_or_network_dependency() -> None:
    imports = imported_modules(POLICY_PATH)
    source = POLICY_PATH.read_text(encoding="utf-8")

    assert imports <= {
        "__future__",
        "collections.abc",
        "dataclasses",
        "app.eod_reconciliation_schemas",
    }
    assert "fastapi" not in source
    assert "httpx" not in source
    assert "repository" not in source
    assert "connection" not in source
    assert "SELECT " not in source
    assert "INSERT " not in source
    assert "UPDATE " not in source


def test_existing_layers_delegate_to_policy_without_duplicate_decisions() -> None:
    facade = FACADE_PATH.read_text(encoding="utf-8")
    service = SERVICE_PATH.read_text(encoding="utf-8")
    repository = REPOSITORY_PATH.read_text(encoding="utf-8")
    operational_policy = OPERATIONAL_POLICY_PATH.read_text(encoding="utf-8")

    assert "policy.report_disposition(" in service
    assert "review_disposition(" in repository
    assert "historical_difference_disposition(" in operational_policy
    assert "report_disposition(" not in facade
    assert 'if errors and not any(' not in service
    assert 'decision == "approved_same_limits"' not in repository
    assert 'if open_count or accepted_count:' not in operational_policy
