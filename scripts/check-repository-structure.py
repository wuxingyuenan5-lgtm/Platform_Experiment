"""Fail CI when repository structure or architectural safety boundaries regress."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "platform-backend" / "app"
TEST_ROOTS = (
    ROOT / "platform-backend" / "tests",
    ROOT / "execution-runtime" / "tests",
)
WORKFLOW_ROOT = ROOT / ".github" / "workflows"

FORBIDDEN_BACKEND_IMPORTS = {
    "MetaTrader5",
    "binance",
    "ccxt",
    "ib_insync",
    "pybit",
}
FORBIDDEN_TEST_NAME = re.compile(
    r"^test_.+_(?:backup|copy|final|new|old|temp|tmp)\.py$",
    re.IGNORECASE,
)
FORBIDDEN_WORKFLOW_NAME = re.compile(
    r"(?:^|[-_])(?:capture|debug|fix-once|one-time|once)(?:[-_]|\.)",
    re.IGNORECASE,
)
ALLOWED_COMPOSITION_CALLS = {"add_middleware", "include_router"}


def imported_top_levels(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return imports


def check_backend_venue_boundary(errors: list[str]) -> None:
    for path in sorted(BACKEND_APP.rglob("*.py")):
        forbidden = imported_top_levels(path) & FORBIDDEN_BACKEND_IMPORTS
        if forbidden:
            relative = path.relative_to(ROOT)
            errors.append(
                f"{relative}: backend imports venue SDK(s) {sorted(forbidden)}; "
                "external execution belongs in execution-runtime"
            )


def is_allowed_composition_call(node: ast.Expr) -> bool:
    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return True
    if not isinstance(node.value, ast.Call):
        return False
    function = node.value.func
    return (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "app"
        and function.attr in ALLOWED_COMPOSITION_CALLS
    )


def check_composition_root(errors: list[str]) -> None:
    path = BACKEND_APP / "main.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and is_allowed_composition_call(node):
            continue
        if isinstance(node, ast.Assign) and all(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        errors.append(
            "platform-backend/app/main.py: composition root may only import, "
            "wire routers/middleware, and define __all__"
        )
        break


def check_test_names(errors: list[str]) -> None:
    for root in TEST_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if FORBIDDEN_TEST_NAME.match(path.name):
                errors.append(
                    f"{path.relative_to(ROOT)}: temporary/versioned test suffix is forbidden; "
                    "merge the scenario into the canonical suite or use a domain-specific name"
                )


def check_workflow_names(errors: list[str]) -> None:
    for path in sorted(WORKFLOW_ROOT.glob("*.yml")):
        if FORBIDDEN_WORKFLOW_NAME.search(path.name):
            errors.append(
                f"{path.relative_to(ROOT)}: temporary diagnostic workflow must not be committed"
            )


def main() -> int:
    errors: list[str] = []
    check_backend_venue_boundary(errors)
    check_composition_root(errors)
    check_test_names(errors)
    check_workflow_names(errors)
    if errors:
        print("Repository structure check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Repository structure check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
