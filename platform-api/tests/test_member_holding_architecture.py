from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
HOLDING_MODULES = (
    "member_holding_decimal.py",
    "member_holding_repository.py",
    "member_holding_routes.py",
    "member_holding_schemas.py",
    "member_holding_service.py",
    "member_holding_valuation.py",
)
FORBIDDEN_PREFIXES = (
    "app.trading",
    "app.trade_commands",
    "app.trade_command_execution",
    "app.execution_batches",
    "app.financial_projection_service",
    "app.financial_fact_repository",
    "app.live_trading_sessions",
    "app.cross_spread",
    "execution_runtime",
    "pybit",
    "MetaTrader5",
)


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.architecture
def test_holding_modules_do_not_depend_on_trading_runtime_or_formal_projection() -> None:
    violations: list[str] = []
    for filename in HOLDING_MODULES:
        path = APP_ROOT / filename
        for imported in imports(path):
            if imported.startswith(FORBIDDEN_PREFIXES):
                violations.append(f"{filename}: {imported}")
    assert violations == []


@pytest.mark.architecture
def test_decimal_policy_has_no_http_or_persistence_dependency() -> None:
    imported = imports(APP_ROOT / "member_holding_decimal.py")
    forbidden = {
        name
        for name in imported
        if name.startswith(("fastapi", "sqlite3", "app.database", "app.auth"))
    }
    assert forbidden == set()


@pytest.mark.architecture
def test_self_holding_route_accepts_no_user_identifier() -> None:
    tree = ast.parse(
        (APP_ROOT / "member_holding_routes.py").read_text(encoding="utf-8"),
        filename="member_holding_routes.py",
    )
    route = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "self_holdings"
    )
    argument_names = {argument.arg for argument in route.args.args}
    assert "user_id" not in argument_names
    assert "member_user_id" not in argument_names
