#!/usr/bin/env python3
"""Apply bounded Service typing and ownership updates for Issue #81."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    if old not in content:
        raise RuntimeError(f"expected snippet missing from {path}: {old[:140]!r}")
    target.write_text(content.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        "platform-backend/app/eod_reconciliation_service.py",
        '''        account_run_id = account_run.run_id
        difference_ids.update(repository.list_difference_ids_for_run(account_run_id))
''',
        '''        resolved_account_run_id: str = account_run.run_id
        account_run_id = resolved_account_run_id
        difference_ids.update(
            repository.list_difference_ids_for_run(resolved_account_run_id)
        )
''',
    )
    replace_once(
        "docs/architecture/OWNERSHIP.md",
        "| EOD Reconciliation orchestration and routes | `platform-backend/app/eod_reconciliation.py` | EOD use-case sequencing, compatibility aliases, HTTP error mapping and routes pending staged extraction | Direct SQL, DDL, row mapping or duplicate public DTO definitions |\n",
        "| EOD Reconciliation Service | `platform-backend/app/eod_reconciliation_service.py` | Report creation/read/list/review sequencing, cross-domain coordination, partial-failure capture and explicit service failures | FastAPI/APIRouter/Query, direct SQL/DDL, duplicate Policy decisions or routes |\n"
        "| EOD Reconciliation facade | `platform-backend/app/eod_reconciliation.py` | Per-call dependency wiring, compatibility delegates, exact service-error-to-HTTP mapping and routes pending dedicated route-module extraction | Cross-domain use-case sequencing, direct SQL/DDL or duplicate Policy decisions |\n",
    )
    replace_once(
        "scripts/check-documentation-consistency.py",
        '    "EOD Reconciliation orchestration and routes": "platform-backend/app/eod_reconciliation.py",\n',
        '    "EOD Reconciliation Service": "platform-backend/app/eod_reconciliation_service.py",\n'
        '    "EOD Reconciliation facade": "platform-backend/app/eod_reconciliation.py",\n',
    )
    replace_once(
        "docs/codex/current-state.md",
        "Latest completed engineering scope: Issue #79 / PR #80\n",
        "Latest completed engineering scope: Issue #81 / PR #82\n",
    )
    replace_once(
        "docs/codex/current-state.md",
        "- `eod_reconciliation.py` retains EOD use-case sequencing, compatibility aliases, exact HTTP mapping and routes; `eod_policy.py` coordinates order-window and historical-Difference persistence without duplicating decisions.\n",
        "- EOD report creation/read/list/review sequencing, cross-domain coordination, exact partial-failure capture and explicit service failures are owned only by `eod_reconciliation_service.py`.\n"
        "- `eod_reconciliation.py` retains per-call dependency wiring, compatibility delegates, exact service-error-to-HTTP mapping and routes; `eod_policy.py` coordinates order-window and historical-Difference persistence without duplicating decisions.\n",
    )
    replace_once(
        "docs/codex/current-state.md",
        "32. Pure EOD report/review Policy ownership with exhaustive status, gate, replay, conflict and approval Goldens.\n",
        "32. Pure EOD report/review Policy ownership with exhaustive status, gate, replay, conflict and approval Goldens.\n"
        "33. EOD Reconciliation Service ownership with per-call compatibility injection, exact partial-failure and HTTP-mapping evidence.\n",
    )
    replace_once(
        "docs/codex/current-state.md",
        "No engineering code workstream is active by default after PR #80 merges.\n",
        "No engineering code workstream is active by default after PR #82 merges.\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "Status: active; critical execution, FinancialFact, Venue Reconciliation, EOD schemas/policy/repository and SQLite boundaries selected\n",
        "Status: active; critical execution, FinancialFact, Venue Reconciliation, EOD schemas/policy/repository/service and SQLite boundaries selected\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "EOD Reconciliation DTOs/Policy/Repository, SQLite Connection/Bootstrap/Seeds",
        "EOD Reconciliation DTOs/Policy/Repository/Service, SQLite Connection/Bootstrap/Seeds",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "Status: active; public schemas, pure decision Policy and persistence repository extracted through Issues #75, #77 and #79\n",
        "Status: active; public schemas, pure decision Policy, persistence Repository and Service extracted through Issues #75, #77, #79 and #81\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "- `app/eod_reconciliation.py`: compatibility aliases, cross-domain orchestration, exact HTTP mapping and routes.\n",
        "- `app/eod_reconciliation_service.py`: framework-independent report creation/read/list/review sequencing, cross-domain coordination and exact partial-failure capture;\n"
        "- `app/eod_reconciliation.py`: per-call dependency wiring, compatibility delegates, exact HTTP mapping and routes.\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "Remaining risk: cross-domain orchestration, partial-failure capture and FastAPI routes still share one module. Splitting Service and routes together would recreate an oversized refactor.\n\nTrigger: extract one framework-independent EOD Service, then a thin route facade in a later bounded Issue.\n",
        "Remaining risk: FastAPI route declarations still share the compatibility facade with dependency wiring and HTTP translation. This is now a thin boundary rather than a mixed business module.\n\nTrigger: extract a dedicated EOD route module only when route ownership or API assembly receives material work.\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "Safe approach: framework-independent Service → thin route facade, with one small PR and exact behavioral evidence per boundary.\n",
        "Safe approach: dedicated route module only, preserving facade compatibility delegates until usage evidence supports removal.\n",
    )
    replace_once(
        "CHANGELOG.md",
        "## Unreleased\n\n### Pure EOD report/review Policy ownership — Issue #79 / PR #80\n",
        "## Unreleased\n\n"
        "### EOD Reconciliation Service ownership — Issue #81 / PR #82\n\n"
        "- Added `platform-backend/app/eod_reconciliation_service.py` as the framework-independent report creation/read/list/review sequencing owner.\n"
        "- Reduced `app.eod_reconciliation` to per-call dependency wiring, compatibility delegates, exact service-error-to-HTTP mapping and existing routes.\n"
        "- Preserved all existing `app.eod_reconciliation.*` monkeypatch targets by rebuilding Service dependencies on every facade call.\n"
        "- Added exact utility/exception identities, dynamic dependency injection, partial-failure ownership and 404/409/422 mapping evidence.\n"
        "- Preserved every report identity, cross-domain call order, partial-failure string, persistence transaction, API and both Live Write defaults.\n\n"
        "### Pure EOD report/review Policy ownership — Issue #79 / PR #80\n",
    )


if __name__ == "__main__":
    main()
