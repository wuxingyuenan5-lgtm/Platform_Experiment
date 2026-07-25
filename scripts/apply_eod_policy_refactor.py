#!/usr/bin/env python3
"""Apply the bounded source and ownership edits for Issue #79."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    if old not in content:
        raise RuntimeError(f"expected snippet missing from {path}: {old[:120]!r}")
    target.write_text(content.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        "platform-backend/app/eod_reconciliation.py",
        "from app.eod_policy import apply_outstanding_difference_gate, list_strategy_orders_for_eod\n",
        "from app.eod_policy import apply_outstanding_difference_gate, list_strategy_orders_for_eod\n"
        "from app.eod_reconciliation_policy import report_disposition\n",
    )
    replace_once(
        "platform-backend/app/eod_reconciliation.py",
        '''    status: ReportStatus
    if errors and not any([account_run_id, economic_import_id, nav_snapshot_id, order_count]):
        status = "failed"
    elif errors:
        status = "partial"
    elif open_count or skipped_external_ids or missing_account_ids or formal_pnl_incomplete_count:
        status = "completed_with_differences"
    else:
        status = "complete"

    scale_gate_status: ScaleGateStatus = (
        "eligible_for_review" if status == "complete" else "blocked"
    )
''',
        '''    disposition = report_disposition(
        errors=errors,
        account_reconciliation_run_id=account_run_id,
        economic_event_import_id=economic_import_id,
        nav_snapshot_id=nav_snapshot_id,
        order_reconciliation_count=order_count,
        open_difference_count=open_count,
        skipped_external_ids=skipped_external_ids,
        missing_account_ids=missing_account_ids,
        formal_pnl_incomplete_count=formal_pnl_incomplete_count,
    )
    status = disposition.status
    scale_gate_status = disposition.scale_gate_status
''',
    )
    replace_once(
        "platform-backend/app/eod_reconciliation_repository.py",
        '''from app.eod_reconciliation_schemas import (
    EodReconciliationReportResponse,
    ReviewDecision,
)
''',
        '''from app.eod_reconciliation_policy import (
    EodReviewConflictError,
    EodReviewNotEligibleError,
    review_disposition,
)
from app.eod_reconciliation_schemas import (
    EodReconciliationReportResponse,
    ReviewDecision,
)
''',
    )
    replace_once(
        "platform-backend/app/eod_reconciliation_repository.py",
        '''class EodReviewConflictError(RuntimeError):
    pass


class EodReviewNotEligibleError(RuntimeError):
    pass


''',
        "",
    )
    replace_once(
        "platform-backend/app/eod_reconciliation_repository.py",
        '''        if row["review_payload_hash"] is not None:
            if row["review_payload_hash"] != payload_hash:
                raise EodReviewConflictError(
                    "EOD report review is immutable and already has a different decision"
                )
            return ReviewWriteResult(row=row, changed=False)
        if decision == "approved_same_limits" and row["scale_gate_status"] != (
            "eligible_for_review"
        ):
            raise EodReviewNotEligibleError(
                "Only a clean EOD report can be approved for the existing live limits"
            )
        db.execute(
''',
        '''        disposition = review_disposition(
            existing_payload_hash=row["review_payload_hash"],
            requested_payload_hash=payload_hash,
            decision=decision,
            current_scale_gate_status=row["scale_gate_status"],
        )
        if not disposition.changed:
            return ReviewWriteResult(row=row, changed=False)
        db.execute(
''',
    )
    replace_once(
        "platform-backend/app/eod_reconciliation_repository.py",
        '''                decision,
                report_id,
''',
        '''                disposition.scale_gate_status,
                report_id,
''',
    )
    replace_once(
        "platform-backend/pyproject.toml",
        '  "app/eod_reconciliation_repository.py",\n',
        '  "app/eod_reconciliation_policy.py",\n  "app/eod_reconciliation_repository.py",\n',
    )
    replace_once(
        "docs/architecture/OWNERSHIP.md",
        "| EOD Reconciliation public DTOs | `platform-backend/app/eod_reconciliation_schemas.py` | EOD report/review request-response models and public status types | DDL, SQL, report orchestration, review policy or routes |\n",
        "| EOD Reconciliation public DTOs | `platform-backend/app/eod_reconciliation_schemas.py` | EOD report/review request-response models and public status types | DDL, SQL, report orchestration, review policy or routes |\n"
        "| EOD report and review policy | `platform-backend/app/eod_reconciliation_policy.py` | Pure report status, scale-gate, historical-Difference and immutable-review decisions | FastAPI, database/repository access, HTTP or cross-domain orchestration |\n",
    )
    replace_once(
        "docs/architecture/OWNERSHIP.md",
        "| EOD scale-gate policy | `platform-backend/app/eod_policy.py` | Business-day order selection inputs and outstanding-Difference scale-gate decisions | Direct SQL, DDL, report row mapping or routes |\n",
        "| EOD operational gate coordination | `platform-backend/app/eod_policy.py` | Business-day order selection and repository coordination for the historical-Difference gate | Direct SQL/DDL, report row mapping, duplicate status/review decisions or routes |\n",
    )
    repeated_owners = (
        '    "EOD Reconciliation public DTOs": "platform-backend/app/eod_reconciliation_schemas.py",\n'
        + (
            '    "EOD Reconciliation persistence": "platform-backend/app/eod_reconciliation_repository.py",\n'
            '    "EOD Reconciliation orchestration and routes": "platform-backend/app/eod_reconciliation.py",\n'
            '    "EOD scale-gate policy": "platform-backend/app/eod_policy.py",\n'
        )
        * 4
    )
    replace_once(
        "scripts/check-documentation-consistency.py",
        repeated_owners,
        '    "EOD Reconciliation public DTOs": "platform-backend/app/eod_reconciliation_schemas.py",\n'
        '    "EOD report and review policy": "platform-backend/app/eod_reconciliation_policy.py",\n'
        '    "EOD Reconciliation persistence": "platform-backend/app/eod_reconciliation_repository.py",\n'
        '    "EOD Reconciliation orchestration and routes": "platform-backend/app/eod_reconciliation.py",\n'
        '    "EOD operational gate coordination": "platform-backend/app/eod_policy.py",\n',
    )
    replace_once(
        "docs/codex/current-state.md",
        "Latest completed engineering scope: Issue #77 / PR #78\n",
        "Latest completed engineering scope: Issue #79 / PR #80\n",
    )
    replace_once(
        "docs/codex/current-state.md",
        "- EOD Reconciliation DDL, direct SQL, report row mapping, report identity, review transactions and policy persistence reads/writes are owned only by `eod_reconciliation_repository.py`.\n- `eod_reconciliation.py` retains EOD use-case sequencing, compatibility aliases, exact HTTP mapping and routes; `eod_policy.py` retains order-window and outstanding-Difference scale-gate decisions without direct database access.\n",
        "- EOD report status, scale-gate, historical-Difference and immutable-review decisions are owned only by the pure `eod_reconciliation_policy.py` module.\n- EOD Reconciliation DDL, direct SQL, report row mapping, report identity and atomic review persistence are owned only by `eod_reconciliation_repository.py`.\n- `eod_reconciliation.py` retains EOD use-case sequencing, compatibility aliases, exact HTTP mapping and routes; `eod_policy.py` coordinates order-window and historical-Difference persistence without duplicating decisions.\n",
    )
    replace_once(
        "docs/codex/current-state.md",
        "31. EOD Reconciliation Repository ownership with exact DDL, report identity, immutable-review transaction and rollback evidence.\n",
        "31. EOD Reconciliation Repository ownership with exact DDL, report identity, immutable-review transaction and rollback evidence.\n32. Pure EOD report/review Policy ownership with exhaustive status, gate, replay, conflict and approval Goldens.\n",
    )
    replace_once(
        "docs/codex/current-state.md",
        "No engineering code workstream is active by default after PR #78 merges.\n",
        "No engineering code workstream is active by default after PR #80 merges.\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "Status: active; critical execution, FinancialFact, Venue Reconciliation, EOD schemas/repository and SQLite boundaries selected\n",
        "Status: active; critical execution, FinancialFact, Venue Reconciliation, EOD schemas/policy/repository and SQLite boundaries selected\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "EOD Reconciliation DTOs/Repository, SQLite Connection/Bootstrap/Seeds",
        "EOD Reconciliation DTOs/Policy/Repository, SQLite Connection/Bootstrap/Seeds",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "Status: active; public schemas and persistence repository extracted through Issues #75 and #77\n",
        "Status: active; public schemas, pure decision Policy and persistence repository extracted through Issues #75, #77 and #79\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "- `app/eod_reconciliation_schemas.py`: public status types and request/response DTOs;\n- `app/eod_reconciliation_repository.py`: EOD DDL, direct SQL, report identity, row mapping, report persistence, immutable review transactions and policy persistence reads/writes;\n- `app/eod_policy.py`: business-day order selection and outstanding-Difference scale-gate decisions without direct database access;\n",
        "- `app/eod_reconciliation_schemas.py`: public status types and request/response DTOs;\n- `app/eod_reconciliation_policy.py`: pure report status, scale-gate, historical-Difference and immutable-review decisions;\n- `app/eod_reconciliation_repository.py`: EOD DDL, direct SQL, report identity, row mapping, report persistence and atomic review transactions;\n- `app/eod_policy.py`: business-day order selection and repository coordination for historical Difference gates without duplicate decisions;\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "Remaining risk: status/review decisions, cross-domain orchestration, partial-failure capture and FastAPI routes still share one module. Splitting these together would recreate an oversized refactor.\n\nTrigger: open one separate Issue for a pure EOD status/review Policy only after Repository CI is stable; then extract a framework-independent Service and thin route facade in later bounded Issues.\n",
        "Remaining risk: cross-domain orchestration, partial-failure capture and FastAPI routes still share one module. Splitting Service and routes together would recreate an oversized refactor.\n\nTrigger: extract one framework-independent EOD Service, then a thin route facade in a later bounded Issue.\n",
    )
    replace_once(
        "docs/engineering/TECHNICAL_DEBT.md",
        "Safe approach: pure review/status Policy → framework-independent Service → thin route facade, with one small PR and exact behavioral evidence per boundary.\n",
        "Safe approach: framework-independent Service → thin route facade, with one small PR and exact behavioral evidence per boundary.\n",
    )
    replace_once(
        "CHANGELOG.md",
        "## Unreleased\n\n### EOD Reconciliation Repository ownership — Issue #77 / PR #78\n",
        "## Unreleased\n\n"
        "### Pure EOD report/review Policy ownership — Issue #79 / PR #80\n\n"
        "- Added `platform-backend/app/eod_reconciliation_policy.py` as the sole pure report-status, scale-gate, historical-Difference and immutable-review decision owner.\n"
        "- Kept Repository review read/decision/write handling inside one protected transaction and preserved compatibility exception identities.\n"
        "- Added exhaustive report, gate, replay, conflict and approval-eligibility Goldens plus framework/persistence purity checks.\n"
        "- Removed duplicate decision branches from EOD orchestration, Repository and operational gate coordination without changing any result or API.\n"
        "- Consolidated duplicated EOD machine-owner mappings and registered the Policy in progressive Pyright and Architecture Ownership.\n\n"
        "### EOD Reconciliation Repository ownership — Issue #77 / PR #78\n",
    )


if __name__ == "__main__":
    main()
