#!/usr/bin/env python3
"""Validate canonical architecture ownership and Agent-context consistency."""

from __future__ import annotations

from pathlib import Path

REQUIRED_ENTRYPOINTS = (
    "AGENTS.md",
    "00-人工可读目录/README.md",
    "docs/architecture/README.md",
    "docs/architecture/OWNERSHIP.md",
    "docs/codex/context-map.md",
    "docs/codex/current-state.md",
    "docs/codex/task-template.md",
    "docs/database/README.md",
)

REQUIRED_OWNERS = {
    "Platform composition root": "platform-backend/app/main.py",
    "Execution API DTOs": "platform-backend/app/execution_schemas.py",
    "Operational fill projection": "platform-backend/app/trading.py",
    "FinancialFact public DTOs": "platform-backend/app/financial_fact_schemas.py",
    "FinancialFact normalization": "platform-backend/app/financial_fact_normalization.py",
    "FinancialFact persistence": "platform-backend/app/financial_fact_repository.py",
    "Formal projection calculations": "platform-backend/app/financial_projection_service.py",
    "FinancialFact API orchestration": "platform-backend/app/financial_facts.py",
    "SQLite connection": "platform-backend/app/database_connection.py",
    "Core database bootstrap": "platform-backend/app/database_bootstrap.py",
    "Fixed reference Seeds": "platform-backend/app/database_seeds.py",
    "Database compatibility facade": "platform-backend/app/database.py",
    "Migration ledger": "platform-backend/app/schema_migrations.py",
    "Runtime journal": "execution-runtime/app/journal.py",
    "Platform execution exposure": "platform-backend/app/execution_exposure.py",
    "Durable Agent rules": "AGENTS.md",
    "Agent context loading": "docs/codex/context-map.md",
    "Current engineering truth": "docs/codex/current-state.md",
    "Architecture ownership": "docs/architecture/OWNERSHIP.md",
    "Workstream enforcement": "scripts/check-workstream.py",
}

DOCUMENT_CATALOG_REFERENCES = (
    "AGENTS.md",
    "docs/architecture/README.md",
    "docs/codex/context-map.md",
    "docs/codex/current-state.md",
)

STALE_CONTEXT_SNIPPETS = (
    "Formal accounting authority: `platform-backend/app/financial_facts.py`",
    "Formal accounting authority: platform-backend/app/financial_facts.py",
)


def read_text(root: Path, relative_path: str) -> str:
    return (root / relative_path).read_text(encoding="utf-8")


def validate_repository(root: Path) -> list[str]:
    """Return deterministic documentation-consistency errors for ``root``."""

    errors: list[str] = []

    for relative_path in REQUIRED_ENTRYPOINTS:
        if not (root / relative_path).is_file():
            errors.append(f"missing canonical documentation entrypoint: {relative_path}")

    ownership_path = root / "docs/architecture/OWNERSHIP.md"
    if ownership_path.is_file():
        ownership = ownership_path.read_text(encoding="utf-8")
        for boundary, owner_path in REQUIRED_OWNERS.items():
            expected_row = f"| {boundary} | `{owner_path}` |"
            if expected_row not in ownership:
                errors.append(
                    f"ownership catalog missing canonical mapping: {boundary} -> {owner_path}"
                )
            if not (root / owner_path).exists():
                errors.append(f"canonical owner path does not exist: {owner_path}")

    catalog_reference = "docs/architecture/OWNERSHIP.md"
    for relative_path in DOCUMENT_CATALOG_REFERENCES:
        path = root / relative_path
        if path.is_file() and catalog_reference not in path.read_text(encoding="utf-8"):
            errors.append(f"{relative_path} must reference {catalog_reference}")

    context_path = root / "docs/codex/context-map.md"
    if context_path.is_file():
        context = context_path.read_text(encoding="utf-8")
        for stale in STALE_CONTEXT_SNIPPETS:
            if stale in context:
                errors.append(f"stale Agent context ownership statement: {stale}")

    return sorted(errors)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(root)
    if errors:
        print("Documentation consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Documentation consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
