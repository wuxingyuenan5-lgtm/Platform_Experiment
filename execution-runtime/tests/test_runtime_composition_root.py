from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app" / "main.py"


def test_main_is_bounded_composition_root() -> None:
    source = MAIN.read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 80
    assert "@app." not in source
    assert "@application." not in source
    assert "SELECT " not in source
    assert "RuntimeSubmitOrderCommandV1" not in source
    assert "GatewayResultUnknownError" not in source
    assert "from app.version import PLATFORM_VERSION" in source
    assert '\nPLATFORM_VERSION = "' not in source
    for factory in (
        "create_system_router",
        "create_gateway_router",
        "create_command_router",
        "create_venue_query_router",
    ):
        assert factory in source


def test_main_only_defines_lifecycle_and_composition_functions() -> None:
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert functions == {"lifespan", "create_app"}
