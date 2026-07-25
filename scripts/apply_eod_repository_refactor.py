#!/usr/bin/env python3
"""Apply bounded ownership-registry updates for Issue #77."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    if old not in content:
        raise RuntimeError(f"expected snippet missing from {path}: {old!r}")
    updated = content.replace(old, new, 1)
    target.write_text(updated, encoding="utf-8")


def main() -> None:
    replace_once(
        "scripts/check-repository-structure.py",
        '    "platform-backend/app/eod_reconciliation.py",\n',
        '    "platform-backend/app/eod_reconciliation_repository.py",\n',
    )
    replace_once(
        "scripts/check-documentation-consistency.py",
        '    "EOD Reconciliation public DTOs": "platform-backend/app/eod_reconciliation_schemas.py",\n',
        '    "EOD Reconciliation public DTOs": "platform-backend/app/eod_reconciliation_schemas.py",\n'
        '    "EOD Reconciliation persistence": "platform-backend/app/eod_reconciliation_repository.py",\n'
        '    "EOD Reconciliation orchestration and routes": "platform-backend/app/eod_reconciliation.py",\n'
        '    "EOD scale-gate policy": "platform-backend/app/eod_policy.py",\n',
    )


if __name__ == "__main__":
    main()
