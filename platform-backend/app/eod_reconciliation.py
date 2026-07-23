from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from app.config import get_settings
from app.database import connection
from app.eod_policy import apply_outstanding_difference_gate, list_strategy_orders_for_eod
from app.financial_facts import rebuild_strategy_financials, run_formal_nav_snapshot
from app.live_venue_accounting import (
    LiveEconomicEventImportRequest,
    import_live_economic_events,
)
from app.venue_reconciliation import (
    VenueReconciliationRunRequest,
    audit,
    reconcile_order_with_venue,
    run_account_reconciliation,
    validate_strategy_account,
)

# Stable orchestration port backed by the single policy implementation.
list_strategy_orders = list_strategy_orders_for_eod

ReportStatus = Literal[
    "complete",
    "completed_with_differences",
    "partial",
    "failed",
]
ScaleGateStatus = Literal[
    "blocked",
    "eligible_for_review",
    "approved_same_limits",
    "needs_remediation",
    "rejected",
]
ReviewDecision = Literal["approved_same_limits", "needs_remediation", "rejected"]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS eod_reconciliation_reports (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    natural_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    business_date TEXT NOT NULL,
    timezone TEXT NOT NULL,
    valuation_time TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    owner TEXT NOT NULL,
    due_at TEXT NOT NULL,
    status TEXT NOT NULL,
    scale_gate_status TEXT NOT NULL,
    order_reconciliation_count INTEGER NOT NULL,
    account_reconciliation_run_id TEXT,
    economic_event_import_id TEXT,
    nav_snapshot_id TEXT,
    formal_pnl_count INTEGER NOT NULL,
    formal_pnl_incomplete_count INTEGER NOT NULL,
    open_difference_count INTEGER NOT NULL,
    resolved_difference_count INTEGER NOT NULL,
    accepted_difference_count INTEGER NOT NULL,
    skipped_external_ids_json TEXT NOT NULL,
    missing_account_ids_json TEXT NOT NULL,
    errors_json TEXT NOT NULL,
    review_payload_hash TEXT,
    reviewer TEXT,
    review_decision TEXT,
    review_reason TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_eod_reports_business_date
ON eod_reconciliation_reports(business_date, strategy_instance_id, account_id);

CREATE INDEX IF NOT EXISTS idx_eod_reports_status
ON eod_reconciliation_reports(status, scale_gate_status, due_at);
"""


class EodReconciliationReportRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    business_date: date = Field(alias="businessDate")
    timezone: str = Field(min_length=1, max_length=128)
    valuation_time: datetime = Field(alias="valuationTime")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    actor: str = Field(min_length=1, max_length=128)
    owner: str = Field(min_length=1, max_length=128)
    due_at: datetime = Field(alias="dueAt")

    @model_validator(mode="after")
    def validate_time_contract(self) -> "EodReconciliationReportRequest":
        if self.valuation_time.tzinfo is None or self.due_at.tzinfo is None:
            raise ValueError("valuationTime and dueAt must include a timezone")
        try:
            timezone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        local_business_date = self.valuation_time.astimezone(timezone).date()
        if local_business_date != self.business_date:
            raise ValueError("businessDate must match valuationTime in the configured timezone")
        return self


class EodReconciliationReviewRequest(BaseModel):
    decision: ReviewDecision
    reviewer: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class EodReconciliationReportResponse(BaseModel):
    report_id: str = Field(alias="reportId")
    idempotency_key: str = Field(alias="idempotencyKey")
    business_date: date = Field(alias="businessDate")
    timezone: str
    valuation_time: datetime = Field(alias="valuationTime")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    actor: str
    owner: str
    due_at: datetime = Field(alias="dueAt")
    status: ReportStatus
    sla_status: str = Field(alias="slaStatus")
    scale_gate_status: ScaleGateStatus = Field(alias="scaleGateStatus")
    order_reconciliation_count: int = Field(alias="orderReconciliationCount")
    account_reconciliation_run_id: str | None = Field(
        default=None,
        alias="accountReconciliationRunId",
    )
    economic_event_import_id: str | None = Field(
        default=None,
        alias="economicEventImportId",
    )
    nav_snapshot_id: str | None = Field(default=None, alias="navSnapshotId")
    formal_pnl_count: int = Field(alias="formalPnlCount")
    formal_pnl_incomplete_count: int = Field(alias="formalPnlIncompleteCount")
    open_difference_count: int = Field(alias="openDifferenceCount")
    resolved_difference_count: int = Field(alias="resolvedDifferenceCount")
    accepted_difference_count: int = Field(alias="acceptedDifferenceCount")
    skipped_external_ids: list[str] = Field(alias="skippedExternalIds")
    missing_account_ids: list[str] = Field(alias="missingAccountIds")
    errors: list[str]
    reviewer: str | None = None
    review_decision: ReviewDecision | None = Field(default=None, alias="reviewDecision")
    review_reason: str | None = Field(default=None, alias="reviewReason")
    reviewed_at: datetime | None = Field(default=None, alias="reviewedAt")
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def natural_key(request: EodReconciliationReportRequest) -> str:
    return ":".join(
        [
            request.business_date.isoformat(),
            request.strategy_instance_id,
            request.account_id,
        ]
    )


def create_eod_report(
    request: EodReconciliationReportRequest,
) -> EodReconciliationReportResponse:
    ensure_schema()
    validate_strategy_account(request.strategy_instance_id, request.account_id)
    payload = request.model_dump(by_alias=True, mode="json")
    payload_hash = canonical_hash(payload)
    report_natural_key = natural_key(request)

    with connection() as db:
        existing = db.execute(
            """
            SELECT * FROM eod_reconciliation_reports
            WHERE idempotency_key = ? OR natural_key = ?
            ORDER BY created_at
            LIMIT 1
            """,
            (request.idempotency_key, report_natural_key),
        ).fetchone()
    if existing is not None:
        if existing["payload_hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="EOD report identity was reused with a different payload",
            )
        return report_from_row(existing)

    report_id = str(uuid4())
    created_at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT INTO eod_reconciliation_reports (
                id, idempotency_key, natural_key, payload_hash, business_date,
                timezone, valuation_time, strategy_instance_id, account_id,
                actor, owner, due_at, status, scale_gate_status,
                order_reconciliation_count, account_reconciliation_run_id,
                economic_event_import_id, nav_snapshot_id, formal_pnl_count,
                formal_pnl_incomplete_count, open_difference_count,
                resolved_difference_count, accepted_difference_count,
                skipped_external_ids_json, missing_account_ids_json, errors_json,
                review_payload_hash, reviewer, review_decision, review_reason,
                reviewed_at, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                request.idempotency_key,
                report_natural_key,
                payload_hash,
                request.business_date.isoformat(),
                request.timezone,
                request.valuation_time.astimezone(UTC).isoformat(),
                request.strategy_instance_id,
                request.account_id,
                request.actor,
                request.owner,
                request.due_at.astimezone(UTC).isoformat(),
                "partial",
                "blocked",
                0,
                None,
                None,
                None,
                0,
                0,
                0,
                0,
                0,
                "[]",
                "[]",
                "[]",
                None,
                None,
                None,
                None,
                None,
                created_at,
                None,
            ),
        )

    order_count = 0
    account_run_id: str | None = None
    economic_import_id: str | None = None
    nav_snapshot_id: str | None = None
    skipped_external_ids: list[str] = []
    missing_account_ids: list[str] = []
    errors: list[str] = []
    difference_ids: set[str] = set()

    for order_id in list_strategy_orders(
        request.strategy_instance_id,
        request.account_id,
        request.valuation_time,
    ):
        try:
            result = reconcile_order_with_venue(order_id)
            order_count += 1
            difference_ids.update(result.difference_ids)
        except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
            errors.append(f"order:{order_id}:{type(exc).__name__}:{exc}")

    try:
        account_run = run_account_reconciliation(
            VenueReconciliationRunRequest(
                idempotencyKey=f"{request.idempotency_key}:account",
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                actor=request.actor,
            )
        )
        account_run_id = account_run.run_id
        with connection() as db:
            rows = db.execute(
                "SELECT id FROM reconciliation_differences WHERE run_id = ?",
                (account_run_id,),
            ).fetchall()
        difference_ids.update(row["id"] for row in rows)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"account-reconciliation:{type(exc).__name__}:{exc}")

    try:
        economic_import = import_live_economic_events(
            LiveEconomicEventImportRequest(
                idempotencyKey=f"{request.idempotency_key}:economic-events",
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                actor=request.actor,
            )
        )
        economic_import_id = economic_import.import_id
        skipped_external_ids = list(economic_import.skipped_external_ids)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"economic-events:{type(exc).__name__}:{exc}")

    try:
        rebuild_strategy_financials(request.strategy_instance_id)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"formal-rebuild:{type(exc).__name__}:{exc}")

    try:
        nav = run_formal_nav_snapshot(
            request.strategy_instance_id,
            request.valuation_time,
        )
        nav_snapshot_id = nav.snapshot_id
        missing_account_ids = list(nav.missing_account_ids)
    except Exception as exc:  # noqa: BLE001 - report must preserve partial failures
        errors.append(f"formal-nav:{type(exc).__name__}:{exc}")

    formal_pnl_count, formal_pnl_incomplete_count = formal_pnl_counts(
        request.strategy_instance_id,
        request.account_id,
    )
    open_count, resolved_count, accepted_count = difference_status_counts(difference_ids)

    status: ReportStatus
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
    completed_at = now_iso()
    with connection() as db:
        db.execute(
            """
            UPDATE eod_reconciliation_reports
            SET status = ?, scale_gate_status = ?, order_reconciliation_count = ?,
                account_reconciliation_run_id = ?, economic_event_import_id = ?,
                nav_snapshot_id = ?, formal_pnl_count = ?,
                formal_pnl_incomplete_count = ?, open_difference_count = ?,
                resolved_difference_count = ?, accepted_difference_count = ?,
                skipped_external_ids_json = ?, missing_account_ids_json = ?,
                errors_json = ?, completed_at = ?
            WHERE id = ?
            """,
            (
                status,
                scale_gate_status,
                order_count,
                account_run_id,
                economic_import_id,
                nav_snapshot_id,
                formal_pnl_count,
                formal_pnl_incomplete_count,
                open_count,
                resolved_count,
                accepted_count,
                json.dumps(skipped_external_ids, sort_keys=True),
                json.dumps(missing_account_ids, sort_keys=True),
                json.dumps(errors, ensure_ascii=False, sort_keys=True),
                completed_at,
                report_id,
            ),
        )

    audit(
        "eod_reconciliation_completed",
        "eod_reconciliation_report",
        report_id,
        {
            "businessDate": request.business_date.isoformat(),
            "timezone": request.timezone,
            "valuationTime": request.valuation_time,
            "strategyInstanceId": request.strategy_instance_id,
            "accountId": request.account_id,
            "status": status,
            "scaleGateStatus": scale_gate_status,
            "orderReconciliationCount": order_count,
            "openDifferenceCount": open_count,
            "skippedExternalIds": skipped_external_ids,
            "missingAccountIds": missing_account_ids,
            "errors": errors,
            "actor": request.actor,
            "owner": request.owner,
        },
    )
    apply_outstanding_difference_gate(
        report_id,
        request.strategy_instance_id,
        request.account_id,
    )
    return get_eod_report(report_id)


def formal_pnl_counts(strategy_instance_id: str, account_id: str) -> tuple[int, int]:
    with connection() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN data_quality_state != 'complete' THEN 1 ELSE 0 END)
                       AS incomplete
            FROM formal_pnl_results
            WHERE strategy_instance_id = ? AND account_id = ?
            """,
            (strategy_instance_id, account_id),
        ).fetchone()
    return int(row["total"] or 0), int(row["incomplete"] or 0)


def difference_status_counts(difference_ids: set[str]) -> tuple[int, int, int]:
    if not difference_ids:
        return 0, 0, 0
    placeholders = ",".join("?" for _ in difference_ids)
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT status, COUNT(*) AS count
            FROM reconciliation_differences
            WHERE id IN ({placeholders})
            GROUP BY status
            """,
            tuple(sorted(difference_ids)),
        ).fetchall()
    counts = {row["status"]: int(row["count"]) for row in rows}
    return counts.get("open", 0), counts.get("resolved", 0), counts.get("accepted", 0)


def get_eod_report(report_id: str) -> EodReconciliationReportResponse:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM eod_reconciliation_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="EOD reconciliation report not found")
    return report_from_row(row)


def list_eod_reports(
    strategy_instance_id: str | None = None,
    account_id: str | None = None,
    business_date: date | None = None,
) -> list[EodReconciliationReportResponse]:
    ensure_schema()
    clauses: list[str] = []
    parameters: list[object] = []
    if strategy_instance_id is not None:
        clauses.append("strategy_instance_id = ?")
        parameters.append(strategy_instance_id)
    if account_id is not None:
        clauses.append("account_id = ?")
        parameters.append(account_id)
    if business_date is not None:
        clauses.append("business_date = ?")
        parameters.append(business_date.isoformat())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT * FROM eod_reconciliation_reports
            {where}
            ORDER BY business_date DESC, created_at DESC
            """,
            tuple(parameters),
        ).fetchall()
    return [report_from_row(row) for row in rows]


def review_eod_report(
    report_id: str,
    request: EodReconciliationReviewRequest,
) -> EodReconciliationReportResponse:
    ensure_schema()
    payload_hash = canonical_hash(request.model_dump(mode="json"))
    with connection() as db:
        row = db.execute(
            "SELECT * FROM eod_reconciliation_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="EOD reconciliation report not found")
        if row["review_payload_hash"] is not None:
            if row["review_payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="EOD report review is immutable and already has a different decision",
                )
            return report_from_row(row)
        if request.decision == "approved_same_limits" and row["scale_gate_status"] != (
            "eligible_for_review"
        ):
            raise HTTPException(
                status_code=422,
                detail="Only a clean EOD report can be approved for the existing live limits",
            )
        reviewed_at = now_iso()
        db.execute(
            """
            UPDATE eod_reconciliation_reports
            SET review_payload_hash = ?, reviewer = ?, review_decision = ?,
                review_reason = ?, reviewed_at = ?, scale_gate_status = ?
            WHERE id = ?
            """,
            (
                payload_hash,
                request.reviewer,
                request.decision,
                request.reason,
                reviewed_at,
                request.decision,
                report_id,
            ),
        )
        row = db.execute(
            "SELECT * FROM eod_reconciliation_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
    audit(
        "eod_reconciliation_reviewed",
        "eod_reconciliation_report",
        report_id,
        {
            "decision": request.decision,
            "reviewer": request.reviewer,
            "reason": request.reason,
        },
    )
    return report_from_row(row)


def sla_status(row) -> str:
    due_at = datetime.fromisoformat(row["due_at"])
    completed_at = (
        datetime.fromisoformat(row["completed_at"]) if row["completed_at"] is not None else None
    )
    if completed_at is not None:
        return "met" if completed_at <= due_at else "breached"
    return "overdue" if datetime.now(UTC) > due_at else "pending"


def report_from_row(row) -> EodReconciliationReportResponse:
    return EodReconciliationReportResponse(
        reportId=row["id"],
        idempotencyKey=row["idempotency_key"],
        businessDate=row["business_date"],
        timezone=row["timezone"],
        valuationTime=row["valuation_time"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        actor=row["actor"],
        owner=row["owner"],
        dueAt=row["due_at"],
        status=row["status"],
        slaStatus=sla_status(row),
        scaleGateStatus=row["scale_gate_status"],
        orderReconciliationCount=row["order_reconciliation_count"],
        accountReconciliationRunId=row["account_reconciliation_run_id"],
        economicEventImportId=row["economic_event_import_id"],
        navSnapshotId=row["nav_snapshot_id"],
        formalPnlCount=row["formal_pnl_count"],
        formalPnlIncompleteCount=row["formal_pnl_incomplete_count"],
        openDifferenceCount=row["open_difference_count"],
        resolvedDifferenceCount=row["resolved_difference_count"],
        acceptedDifferenceCount=row["accepted_difference_count"],
        skippedExternalIds=json.loads(row["skipped_external_ids_json"]),
        missingAccountIds=json.loads(row["missing_account_ids_json"]),
        errors=json.loads(row["errors_json"]),
        reviewer=row["reviewer"],
        reviewDecision=row["review_decision"],
        reviewReason=row["review_reason"],
        reviewedAt=row["reviewed_at"],
        createdAt=row["created_at"],
        completedAt=row["completed_at"],
    )


router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/ops/eod-reconciliation/reports",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def create_report(
    request: EodReconciliationReportRequest,
) -> EodReconciliationReportResponse:
    return create_eod_report(request)


@router.get(
    "/ops/eod-reconciliation/reports/{report_id}",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def read_report(report_id: str) -> EodReconciliationReportResponse:
    return get_eod_report(report_id)


@router.get(
    "/ops/eod-reconciliation/reports",
    response_model=list[EodReconciliationReportResponse],
    tags=["eod-reconciliation"],
)
def read_reports(
    strategy_instance_id: str | None = Query(default=None, alias="strategyInstanceId"),
    account_id: str | None = Query(default=None, alias="accountId"),
    business_date: date | None = Query(default=None, alias="businessDate"),
) -> list[EodReconciliationReportResponse]:
    return list_eod_reports(strategy_instance_id, account_id, business_date)


@router.post(
    "/ops/eod-reconciliation/reports/{report_id}/review",
    response_model=EodReconciliationReportResponse,
    tags=["eod-reconciliation"],
)
def review_report(
    report_id: str,
    request: EodReconciliationReviewRequest,
) -> EodReconciliationReportResponse:
    return review_eod_report(report_id, request)
