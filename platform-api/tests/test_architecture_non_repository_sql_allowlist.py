from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "platform-api/app"
ALLOWLIST = ROOT / "docs/architecture/non-repository-sql-allowlist.json"
DIRECT_SQL = re.compile(
    r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE)\b",
    re.IGNORECASE,
)


def has_direct_sql(source: str) -> bool:
    tree = ast.parse(source)
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and DIRECT_SQL.search(node.value)
        for node in ast.walk(tree)
    )


def test_non_repository_direct_sql_has_no_new_owner() -> None:
    policy = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    allowed = set(policy["files"])
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in APP_ROOT.rglob("*.py")
        if "repository" not in path.stem and has_direct_sql(path.read_text(encoding="utf-8"))
    }

    unexpected = sorted(actual - allowed)
    assert unexpected == [], f"New non-Repository direct SQL owners: {unexpected}"
    assert all(item["owner"] and item["reason"] for item in policy["files"].values())


def test_sql_detection_ignores_prose_but_covers_runtime_strings():
    assert not has_direct_sql('"""A SELECT read does not commit."""\n# SELECT in comment')
    assert not has_direct_sql(
        'def f():\n    """SELECT from documented sources."""\n    return None'
    )
    assert has_direct_sql('query = "SELECT id " "FROM orders"')
    assert has_direct_sql('db.execute(f"UPDATE orders SET status={status}")')
    assert has_direct_sql('def f():\n    db.execute("INSERT INTO orders VALUES (?)")')
