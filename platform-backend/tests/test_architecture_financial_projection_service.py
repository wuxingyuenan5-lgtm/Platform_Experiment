import ast
from pathlib import Path

from app import financial_facts
from app import financial_projection_service as service

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SERVICE_PATH = APP_ROOT / "financial_projection_service.py"
API_PATH = APP_ROOT / "financial_facts.py"

PROJECTION_FUNCTIONS = {
    "calculate_position_update",
    "conversion_rate",
    "optional_decimal",
    "rebuild_account_instrument_projection",
    "rebuild_strategy_financials",
    "run_formal_nav_snapshot",
}
REPOSITORY_ORCHESTRATION_CALLS = {
    "list_projection_fact_rows",
    "save_formal_projection",
    "prepare_strategy_rebuild",
    "record_projection_rebuild_audit",
    "list_active_account_rows",
    "load_latest_balance_rows",
    "store_formal_nav_snapshot",
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
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def test_projection_service_is_the_formula_owner() -> None:
    service_functions = function_names(SERVICE_PATH)
    api_functions = function_names(API_PATH)
    compatibility_helpers = {
        "calculate_position_update",
        "conversion_rate",
        "optional_decimal",
    }

    assert PROJECTION_FUNCTIONS <= service_functions
    assert not (compatibility_helpers & api_functions)


def test_api_module_keeps_compatibility_callables() -> None:
    assert financial_facts.calculate_position_update is service.calculate_position_update
    assert financial_facts.conversion_rate is service.conversion_rate
    assert financial_facts.optional_decimal is service.optional_decimal
    assert callable(financial_facts.rebuild_account_instrument_projection)
    assert callable(financial_facts.rebuild_strategy_financials)
    assert callable(financial_facts.run_formal_nav_snapshot)


def test_projection_service_has_no_fastapi_or_config_dependency() -> None:
    imports = imported_modules(SERVICE_PATH)
    assert "fastapi" not in imports
    assert "app.config" not in imports
    assert "app.financial_fact_repository" in imports
    assert "app.financial_fact_normalization" in imports


def test_repository_projection_orchestration_is_not_in_api_module() -> None:
    api_source = API_PATH.read_text(encoding="utf-8")
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    api_calls = {
        call
        for call in REPOSITORY_ORCHESTRATION_CALLS
        if f"repository.{call}" in api_source
    }
    missing_service_calls = {
        call
        for call in REPOSITORY_ORCHESTRATION_CALLS
        if f"repository.{call}" not in service_source
    }

    assert not api_calls
    assert not missing_service_calls
