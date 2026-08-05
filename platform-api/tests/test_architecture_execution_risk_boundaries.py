import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def test_execution_risk_dependencies_are_converged() -> None:
    router_path = ROOT / "platform-api" / "app" / "execution_risk.py"
    policy_path = ROOT / "platform-api" / "app" / "execution_risk_policy.py"
    repository_path = ROOT / "platform-api" / "app" / "execution_risk_repository.py"

    router_source = router_path.read_text(encoding="utf-8")
    router_tree = ast.parse(router_source)
    imported_modules = {
        node.module
        for node in ast.walk(router_tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "app.trade_commands" not in imported_modules
    assert "app.database" not in imported_modules
    assert "connection()" not in router_source

    policy_source = policy_path.read_text(encoding="utf-8")
    assert "app.database" not in policy_source
    assert "fastapi" not in policy_source
    assert "trade_command" not in policy_source

    repository_source = repository_path.read_text(encoding="utf-8")
    assert "fastapi" not in repository_source
    assert "APIRouter" not in repository_source
    assert "HTTPException" not in repository_source


def test_trade_command_port_is_wired_in_composition_root() -> None:
    application_source = (
        ROOT / "platform-api" / "app" / "application.py"
    ).read_text(encoding="utf-8")
    assert "configure_trade_command_port(create_trade_command)" in application_source
