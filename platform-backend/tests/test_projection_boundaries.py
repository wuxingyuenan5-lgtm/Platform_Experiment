from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OPERATIONAL_TABLE_WRITES = (
    "INSERT INTO positions",
    "UPDATE positions",
    "INSERT INTO pnl_results",
    "UPDATE pnl_results",
)
FORMAL_TABLE_WRITES = (
    "INSERT INTO financial_facts",
    "INSERT INTO formal_positions",
    "UPDATE formal_positions",
    "INSERT INTO formal_pnl_results",
    "UPDATE formal_pnl_results",
)
OPERATIONAL_TABLE_READS = (
    "FROM positions",
    "FROM pnl_results",
)


def function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_fill_projection_function_is_explicitly_operational() -> None:
    names = function_names(BACKEND_ROOT / "app/trading.py")
    assert "record_fill_and_update_operational_projections" in names
    assert "record_fill_and_update_projections" not in names


def test_trading_owns_only_operational_projection_writes() -> None:
    source = (BACKEND_ROOT / "app/trading.py").read_text(encoding="utf-8")
    assert all(statement in source for statement in OPERATIONAL_TABLE_WRITES)
    assert all(statement not in source for statement in FORMAL_TABLE_WRITES)


def test_formal_accounting_does_not_read_operational_projection_tables() -> None:
    source = (BACKEND_ROOT / "app/financial_facts.py").read_text(encoding="utf-8")
    assert all(statement not in source for statement in OPERATIONAL_TABLE_READS)
