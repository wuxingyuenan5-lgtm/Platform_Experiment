#!/usr/bin/env python3
"""Make EOD review compatibility re-exports explicit for Ruff."""

from pathlib import Path

path = Path(__file__).resolve().parents[1] / "platform-backend/app/eod_reconciliation_repository.py"
content = path.read_text(encoding="utf-8")
old = """from app.eod_reconciliation_policy import (
    EodReviewConflictError,
    EodReviewNotEligibleError,
    review_disposition,
)
"""
new = """from app.eod_reconciliation_policy import (
    EodReviewConflictError as EodReviewConflictError,
    EodReviewNotEligibleError as EodReviewNotEligibleError,
    review_disposition,
)
"""
if old not in content:
    raise RuntimeError("expected EOD review compatibility import block is missing")
path.write_text(content.replace(old, new, 1), encoding="utf-8")
