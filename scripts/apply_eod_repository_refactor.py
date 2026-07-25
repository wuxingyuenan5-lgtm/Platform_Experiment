#!/usr/bin/env python3
"""Apply bounded ownership-registry updates for Issue #77."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_if_present(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    if old not in content:
        return
    target.write_text(content.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_if_present(
        "scripts/check-repository-structure.py",
        '    "platform-backend/app/eod_reconciliation.py",\n',
        '    "platform-backend/app/eod_reconciliation_repository.py",\n',
    )
    replace_if_present(
        "scripts/check-repository-structure.py",
        '    "platform-backend/app/venue_reconciliation.py",\n',
        '    "platform-backend/app/venue_reconciliation_repository.py",\n',
    )
    replace_if_present(
        "scripts/check-documentation-consistency.py",
        '    "EOD Reconciliation public DTOs": "platform-backend/app/eod_reconciliation_schemas.py",\n',
        '    "EOD Reconciliation public DTOs": "platform-backend/app/eod_reconciliation_schemas.py",\n'
        '    "EOD Reconciliation persistence": "platform-backend/app/eod_reconciliation_repository.py",\n'
        '    "EOD Reconciliation orchestration and routes": "platform-backend/app/eod_reconciliation.py",\n'
        '    "EOD scale-gate policy": "platform-backend/app/eod_policy.py",\n',
    )


if __name__ == "__main__":
    main()
