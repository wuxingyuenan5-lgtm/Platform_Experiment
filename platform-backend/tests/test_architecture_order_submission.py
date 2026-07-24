import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "trade_command_execution.py"
COMPATIBILITY_PATH = APP_ROOT / "trading.py"


def function_names(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_trade_command_execution_is_the_single_submission_owner() -> None:
    owner_source = OWNER_PATH.read_text(encoding="utf-8")
    compatibility_source = COMPATIBILITY_PATH.read_text(encoding="utf-8")

    assert owner_source.count("INSERT INTO orders") == 1
    assert compatibility_source.count("INSERT INTO orders") == 0
    assert owner_source.count("/commands/orders") == 1
    assert compatibility_source.count("/commands/orders") == 0
    assert owner_source.count("httpx.post(") == 1
    assert compatibility_source.count("httpx.post(") == 0


def test_legacy_and_v1_entry_points_delegate_to_the_owner() -> None:
    owner_functions = function_names(OWNER_PATH)
    compatibility_source = COMPATIBILITY_PATH.read_text(encoding="utf-8")

    assert "submit_order_through_runtime" in owner_functions
    assert "submit_trade_command_order" in owner_functions
    assert "from app.trade_command_execution import submit_order_through_runtime" in compatibility_source
    assert 'mode="legacy"' in compatibility_source


def test_owner_retains_explicit_legacy_and_v1_modes() -> None:
    source = OWNER_PATH.read_text(encoding="utf-8")

    assert 'SubmissionMode = Literal["legacy", "v1"]' in source
    assert 'mode="v1"' in source
    assert '"contract_name"' not in COMPATIBILITY_PATH.read_text(encoding="utf-8")
