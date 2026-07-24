import ast
from pathlib import Path

from app import financial_facts, position_math, trading
from app import financial_projection_service as formal_projection

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "position_math.py"


def defined_functions(path: Path) -> set[str]:
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


def test_position_math_is_the_only_function_definition_owner() -> None:
    definitions = [
        path.relative_to(APP_ROOT).as_posix()
        for path in APP_ROOT.glob("*.py")
        if "calculate_position_update" in defined_functions(path)
    ]

    assert definitions == ["position_math.py"]


def test_existing_import_paths_share_the_identical_callable() -> None:
    owner = position_math.calculate_position_update

    assert trading.calculate_position_update is owner
    assert formal_projection.calculate_position_update is owner
    assert financial_facts.calculate_position_update is owner


def test_position_math_has_no_framework_or_persistence_dependency() -> None:
    imports = imported_modules(OWNER_PATH)

    assert imports <= {"__future__", "decimal"}
