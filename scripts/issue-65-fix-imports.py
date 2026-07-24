from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
venue = ROOT / "platform-backend/app/venue_reconciliation.py"
content = venue.read_text(encoding="utf-8")
old = "from fastapi import APIRouter, HTTPException\nfrom app.config import get_settings\n"
new = "from fastapi import APIRouter, HTTPException\n\nfrom app.config import get_settings\n"
if content.count(old) != 1:
    raise SystemExit("expected exactly one Venue Reconciliation import boundary")
venue.write_text(content.replace(old, new, 1), encoding="utf-8")

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-65-fix-imports.yml"
if workflow.exists():
    workflow.unlink()
