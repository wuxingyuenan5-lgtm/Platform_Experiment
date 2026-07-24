import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "venue_reconciliation_schemas.py"
COMPATIBILITY_PATH = APP_ROOT / "venue_reconciliation.py"
MODEL_NAMES = {
    "VenueReconciliationRunRequest",
    "VenueReconciliationRunResponse",
    "ReconciliationDifferenceResponse",
    "ResolveDifferenceRequest",
    "OrderVenueReconciliationResponse",
}


def class_names(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.ClassDef)
    }


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_schema_owner_is_the_only_model_definition_location() -> None:
    owners = {
        path.name: class_names(path) & MODEL_NAMES
        for path in APP_ROOT.glob("*.py")
        if class_names(path) & MODEL_NAMES
    }

    assert owners == {"venue_reconciliation_schemas.py": MODEL_NAMES}


def test_compatibility_module_imports_the_schema_owner() -> None:
    source = COMPATIBILITY_PATH.read_text(encoding="utf-8")

    assert "from app.venue_reconciliation_schemas import (" in source
    assert "class VenueReconciliationRunRequest" not in source
    assert "DifferenceType = Literal[" not in source


def test_schema_owner_has_no_framework_or_persistence_dependency() -> None:
    imports = imported_modules(OWNER_PATH)

    assert imports <= {"__future__", "datetime", "typing", "pydantic"}
