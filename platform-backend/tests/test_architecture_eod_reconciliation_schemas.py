import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "eod_reconciliation_schemas.py"
COMPATIBILITY_PATH = APP_ROOT / "eod_reconciliation.py"
MODEL_NAMES = {
    "EodReconciliationReportRequest",
    "EodReconciliationReviewRequest",
    "EodReconciliationReportResponse",
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

    assert owners == {"eod_reconciliation_schemas.py": MODEL_NAMES}


def test_compatibility_module_imports_the_schema_owner() -> None:
    source = COMPATIBILITY_PATH.read_text(encoding="utf-8")

    assert "from app.eod_reconciliation_schemas import (" in source
    assert "class EodReconciliationReportRequest" not in source
    assert "class EodReconciliationReviewRequest" not in source
    assert "class EodReconciliationReportResponse" not in source
    assert "ReportStatus = Literal[" not in source
    assert "ScaleGateStatus = Literal[" not in source
    assert "ReviewDecision = Literal[" not in source


def test_schema_owner_has_no_framework_or_persistence_dependency() -> None:
    imports = imported_modules(OWNER_PATH)

    assert imports <= {
        "__future__",
        "datetime",
        "typing",
        "zoneinfo",
        "pydantic",
    }
