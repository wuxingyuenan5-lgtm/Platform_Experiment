from __future__ import annotations

import ast
from pathlib import Path

from app import execution_schemas, schemas

BACKEND_ROOT = Path(__file__).resolve().parents[1]
EXECUTION_SCHEMA_NAMES = (
    "BatchLegRequest",
    "BatchLegResponse",
    "CreateExecutionBatchRequest",
    "CreateOrderRequest",
    "CreateStrategyRunRequest",
    "ExecutionBatchResponse",
    "OrderResponse",
    "PnlResponse",
    "PositionResponse",
    "StrategyRunResponse",
    "StrategyV1ReadinessResponse",
)


def test_legacy_schema_imports_reexport_execution_types() -> None:
    for name in EXECUTION_SCHEMA_NAMES:
        assert getattr(schemas, name) is getattr(execution_schemas, name)


def test_cross_domain_schema_module_does_not_redefine_execution_types() -> None:
    path = BACKEND_ROOT / "app/schemas.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defined_classes = {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }
    assert defined_classes.isdisjoint(EXECUTION_SCHEMA_NAMES)
