from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "platform-backend/app/venue_reconciliation.py"
content = path.read_text(encoding="utf-8")
old = (
    "from app.config import get_settings\n"
    "from app import venue_reconciliation_repository as repository\n"
)
new = (
    "from app import venue_reconciliation_repository as repository\n"
    "from app.config import get_settings\n"
)
if content.count(old) != 1:
    raise SystemExit("expected exactly one Venue Reconciliation import block")
path.write_text(content.replace(old, new, 1), encoding="utf-8")

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-69-fix-imports.yml"
if workflow.exists():
    workflow.unlink()
