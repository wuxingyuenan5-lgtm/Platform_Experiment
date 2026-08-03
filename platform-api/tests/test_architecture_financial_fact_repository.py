from __future__ import annotations

import ast
from pathlib import Path

from app import financial_fact_repository, financial_facts

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SQL_ANCHORS = (
    "CREATE TABLE",
    "CREATE INDEX",
    "SELECT ",
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
)


def string_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_financial_fact_service_has_no_direct_persistence() -> None:
    path = BACKEND_ROOT / "app/financial_facts.py"
    source = path.read_text(encoding="utf-8")
    literals = string_literals(path)

    assert "from app.database import connection" not in source
    assert "connection()" not in source
    assert all(anchor not in literal.upper() for literal in literals for anchor in SQL_ANCHORS)


def test_financial_fact_repository_is_the_single_sql_owner() -> None:
    source = (BACKEND_ROOT / "app/financial_fact_repository.py").read_text(encoding="utf-8")

    assert "from app.database import connection" in source
    for anchor in (
        "CREATE TABLE IF NOT EXISTS financial_facts",
        "INSERT INTO financial_facts",
        "INSERT INTO formal_positions",
        "INSERT INTO formal_pnl_results",
        "INSERT INTO formal_strategy_nav_snapshots",
    ):
        assert anchor in source


def test_financial_fact_persistence_compatibility_aliases_are_identity_stable() -> None:
    assert financial_facts.ensure_schema is financial_fact_repository.ensure_schema
    assert (
        financial_facts.financial_fact_from_row
        is financial_fact_repository.financial_fact_from_row
    )
    assert financial_facts.formal_pnl_from_row is financial_fact_repository.formal_pnl_from_row
    assert (
        financial_facts.formal_position_from_row
        is financial_fact_repository.formal_position_from_row
    )
    assert financial_facts.formal_nav_from_row is financial_fact_repository.formal_nav_from_row
