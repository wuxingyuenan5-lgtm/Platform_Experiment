from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise SystemExit(f"expected exactly one match in {path}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


replace_once(
    ROOT / "platform-backend/app/trading.py",
    "from decimal import Decimal\nimport httpx\n",
    "from decimal import Decimal\n\nimport httpx\n",
)

replace_once(
    ROOT / "platform-backend/tests/test_architecture_order_submission.py",
    '    assert "from app.trade_command_execution import submit_order_through_runtime" in compatibility_source\n',
    '    assert (\n'
    '        "from app.trade_command_execution import submit_order_through_runtime"\n'
    '        in compatibility_source\n'
    '    )\n',
)

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-63-fix-ruff.yml"
if workflow.exists():
    workflow.unlink()
