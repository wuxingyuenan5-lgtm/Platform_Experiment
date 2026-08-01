from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app import eod_reconciliation
from app.auth import require_principal
from app.config import get_settings
from app.database import connection
from app.disaster_recovery import CreateBackupRequest, create_backup
from app.disaster_recovery import ensure_schema as ensure_dr_schema
from app.redaction import redact_sensitive

AlertSeverity = Literal["info", "warning", "critical"]
AlertStatus = Literal["open", "acknowledged", "closed"]
ControlledTaskType = Literal["health_scan", "backup", "eod"]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS operational_alerts (
    id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    message TEXT NOT NULL,
    details_json TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    acknowledged_by TEXT,
    acknowledged_at TEXT,
    closed_by TEXT,
    closed_at TEXT,
    resolution_reason TEXT
);

CREATE TABLE IF NOT EXISTS operational_alert_scan_runs (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    owner TEXT NOT NULL,
    actor TEXT NOT NULL,
    alert_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS controlled_operation_runs (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    task_type TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL,
    actor TEXT NOT NULL,
    result_json TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_operational_alert_status
ON operational_alerts(status, severity, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_controlled_operation_created
ON controlled_operation_runs(created_at DESC);
"""


class AlertScanRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    owner: str | None = Field(default=None, min_length=1, max_length=128)


class AlertActionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=512)
    owner: str | None = Field(default=None, min_length=1, max_length=128)


class OperationalAlertResponse(BaseModel):
    alert_id: str = Field(alias="alertId")
    fingerprint: str
    category: str
    severity: AlertSeverity
    status: AlertStatus
    subject_type: str = Field(alias="subjectType")
    subject_id: str = Field(alias="subjectId")
    owner: str
    message: str
    details: dict[str, object]
    occurrence_count: int = Field(alias="occurrenceCount")
    first_seen_at: datetime = Field(alias="firstSeenAt")
    last_seen_at: datetime = Field(alias="lastSeenAt")
    acknowledged_by: str | None = Field(default=None, alias="acknowledgedBy")
    acknowledged_at: datetime | None = Field(default=None, alias="acknowledgedAt")
    closed_by: str | None = Field(default=None, alias="closedBy")
    closed_at: datetime | None = Field(default=None, alias="closedAt")
    resolution_reason: str | None = Field(default=None, alias="resolutionReason")


class ProductionStatusResponse(BaseModel):
    status: str
    observed_at: datetime = Field(alias="observedAt")
    platform_database: dict[str, object] = Field(alias="platformDatabase")
    runtime: dict[str, object]
    venue: dict[str, object]
    credential_readiness: dict[str, object] = Field(alias="credentialReadiness")
    risk: dict[str, object]
    reconciliation: dict[str, object]
    eod: dict[str, object]
    backup: dict[str, object]
    restore: dict[str, object]


class ControlledOperationRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    task_type: ControlledTaskType = Field(alias="taskType")
    scheduled_for: datetime = Field(alias="scheduledFor")
    payload: dict[str, object] = Field(default_factory=dict)


class ControlledOperationResponse(BaseModel):
    run_id: str = Field(alias="runId")
    idempotency_key: str = Field(alias="idempotencyKey")
    task_type: ControlledTaskType = Field(alias="taskType")
    scheduled_for: datetime = Field(alias="scheduledFor")
    status: str
    actor: str
    result: dict[str, object]
    error: str | None = None
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)
    ensure_dr_schema()


def table_exists(db, table_name: str) -> bool:
    row = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def count_rows(db, table_name: str, where: str = "", parameters: tuple[object, ...] = ()) -> int:
    if not table_exists(db, table_name):
        return 0
    suffix = f" WHERE {where}" if where else ""
    row = db.execute(
        f"SELECT COUNT(*) AS count FROM {table_name}{suffix}",
        parameters,
    ).fetchone()
    return int(row["count"])


def runtime_json(path: str) -> dict[str, object]:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.runtime_base_url}{path}",
            timeout=max(settings.runtime_timeout_seconds, 10.0),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return {"status": "invalid_response"}
        return redact_sensitive(payload)
    except (httpx.HTTPError, ValueError):
        return {"status": "not_connected"}


def collect_production_status() -> ProductionStatusResponse:
    ensure_schema()
    observed_at = datetime.now(UTC)
    runtime = runtime_json("/status")
    venue = runtime_json("/gateway/venue-readiness")
    connectivity = runtime_json("/gateway/connectivity")

    with connection() as db:
        db.execute("SELECT 1").fetchone()
        result_unknown = count_rows(db, "orders", "status = 'result_unknown'")
        manual_batches = count_rows(
            db,
            "execution_batches",
            "requires_manual_intervention = 1",
        )
        residual_risk = count_rows(
            db,
            "execution_batch_risk",
            "risk_status IN ('residual_exposure', 'disposition_in_progress', 'escalated')",
        )
        kill_switches = count_rows(db, "trading_kill_switches", "enabled = 1")
        approved_sessions = count_rows(
            db,
            "live_trading_sessions",
            "status = 'approved' AND starts_at <= ? AND ends_at > ?",
            (observed_at.isoformat(), observed_at.isoformat()),
        )
        open_differences = count_rows(
            db,
            "reconciliation_differences",
            "status = 'open'",
        )
        accepted_differences = count_rows(
            db,
            "reconciliation_differences",
            "status = 'accepted'",
        )
        latest_eod = None
        if table_exists(db, "eod_reconciliation_reports"):
            latest_eod = db.execute(
                """
                SELECT id, business_date, status, scale_gate_status, due_at,
                       created_at, completed_at
                FROM eod_reconciliation_reports
                ORDER BY business_date DESC, created_at DESC
                LIMIT 1
                """
            ).fetchone()
        latest_backup = db.execute(
            """
            SELECT id, status, created_at, completed_at, error
            FROM production_backup_records
            ORDER BY created_at DESC LIMIT 1
            """
        ).fetchone()
        latest_restore = db.execute(
            """
            SELECT id, status, created_at, completed_at, error
            FROM production_restore_drills
            ORDER BY created_at DESC LIMIT 1
            """
        ).fetchone()

    credentials = connectivity.get("credentials", [])
    credential_count = len(credentials) if isinstance(credentials, list) else 0
    unconfigured_credentials = 0
    if isinstance(credentials, list):
        unconfigured_credentials = sum(
            1
            for item in credentials
            if isinstance(item, dict) and item.get("configured") is not True
        )

    eod_payload = eod_status(latest_eod, observed_at)
    runtime_available = runtime.get("status") not in {"not_connected", "invalid_response"}
    venue_available = venue.get("status") not in {"not_connected", "invalid_response"}
    critical = (
        not runtime_available
        or not venue_available
        or result_unknown > 0
        or residual_risk > 0
        or open_differences > 0
        or eod_payload.get("overdue") is True
        or eod_payload.get("status") in {"failed", "partial"}
        or (latest_backup is not None and latest_backup["status"] == "failed")
        or (latest_restore is not None and latest_restore["status"] == "failed")
    )
    warning = manual_batches > 0 or accepted_differences > 0 or unconfigured_credentials > 0
    overall = "critical" if critical else ("warning" if warning else "ok")

    return ProductionStatusResponse(
        status=overall,
        observedAt=observed_at,
        platformDatabase={"status": "available"},
        runtime=runtime,
        venue=venue,
        credentialReadiness={
            "status": "incomplete" if unconfigured_credentials else "available",
            "credentialCount": credential_count,
            "unconfiguredCredentialCount": unconfigured_credentials,
        },
        risk={
            "enabledKillSwitchCount": kill_switches,
            "approvedLiveSessionCount": approved_sessions,
            "resultUnknownOrderCount": result_unknown,
            "manualInterventionBatchCount": manual_batches,
            "residualRiskBatchCount": residual_risk,
        },
        reconciliation={
            "openDifferenceCount": open_differences,
            "acceptedDifferenceCount": accepted_differences,
        },
        eod=eod_payload,
        backup=row_summary(latest_backup),
        restore=row_summary(latest_restore),
    )


def row_summary(row) -> dict[str, object]:
    if row is None:
        return {"status": "not_available"}
    return {
        "id": row["id"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "completedAt": row["completed_at"],
        "error": row["error"],
    }


def eod_status(row, observed_at: datetime) -> dict[str, object]:
    if row is None:
        return {"status": "not_available", "overdue": False}
    due_at = datetime.fromisoformat(row["due_at"])
    completed_at = datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
    grace = timedelta(minutes=max(get_settings().operations_eod_overdue_grace_minutes, 0))
    overdue = completed_at is None and observed_at > due_at.astimezone(UTC) + grace
    return {
        "reportId": row["id"],
        "businessDate": row["business_date"],
        "status": row["status"],
        "scaleGateStatus": row["scale_gate_status"],
        "dueAt": row["due_at"],
        "createdAt": row["created_at"],
        "completedAt": row["completed_at"],
        "overdue": overdue,
    }


def alert_candidates(status: ProductionStatusResponse) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []

    def add(
        category: str,
        severity: AlertSeverity,
        subject_type: str,
        subject_id: str,
        message: str,
        details: dict[str, object],
    ) -> None:
        candidates.append(
            {
                "category": category,
                "severity": severity,
                "subjectType": subject_type,
                "subjectId": subject_id,
                "message": message,
                "details": details,
            }
        )

    if status.runtime.get("status") in {"not_connected", "invalid_response"}:
        add(
            "runtime_unavailable",
            "critical",
            "service",
            "execution-runtime",
            "Platform Execution Runtime is unavailable",
            status.runtime,
        )
    if status.venue.get("status") in {"not_connected", "invalid_response"}:
        add(
            "venue_unavailable",
            "critical",
            "service",
            "venue-gateway",
            "Venue readiness is unavailable",
            status.venue,
        )
    risk = status.risk
    for category, severity, key, message in (
        (
            "result_unknown_orders",
            "critical",
            "resultUnknownOrderCount",
            "Orders with unknown external result require reconciliation",
        ),
        (
            "manual_intervention_batches",
            "warning",
            "manualInterventionBatchCount",
            "Execution batches require manual intervention",
        ),
        (
            "residual_execution_risk",
            "critical",
            "residualRiskBatchCount",
            "Execution batches retain residual exposure or escalated risk",
        ),
    ):
        count = int(risk.get(key, 0))
        if count:
            add(category, severity, "portfolio", "global", message, {"count": count})

    reconciliation = status.reconciliation
    open_count = int(reconciliation.get("openDifferenceCount", 0))
    accepted_count = int(reconciliation.get("acceptedDifferenceCount", 0))
    if open_count:
        add(
            "open_reconciliation_differences",
            "critical",
            "reconciliation",
            "global",
            "Open reconciliation differences block live operation",
            {"count": open_count},
        )
    if accepted_count:
        add(
            "accepted_reconciliation_differences",
            "warning",
            "reconciliation",
            "global",
            "Accepted differences remain unresolved economic discrepancies",
            {"count": accepted_count},
        )

    credential_count = int(status.credential_readiness.get("unconfiguredCredentialCount", 0))
    if credential_count:
        add(
            "credential_reference_unavailable",
            "critical",
            "credential",
            "runtime",
            "One or more Runtime credential references are not configured",
            {"count": credential_count},
        )

    if status.eod.get("overdue") is True:
        add(
            "eod_overdue",
            "critical",
            "eod_report",
            str(status.eod.get("reportId", "latest")),
            "Latest EOD report is overdue",
            status.eod,
        )
    if status.eod.get("status") in {"failed", "partial", "completed_with_differences"}:
        severity: AlertSeverity = (
            "critical" if status.eod.get("status") in {"failed", "partial"} else "warning"
        )
        add(
            "eod_not_clean",
            severity,
            "eod_report",
            str(status.eod.get("reportId", "latest")),
            "Latest EOD report is not clean",
            status.eod,
        )

    if status.backup.get("status") == "failed":
        add(
            "backup_failed",
            "critical",
            "production_backup",
            str(status.backup.get("id", "latest")),
            "Latest production backup failed",
            status.backup,
        )
    if status.restore.get("status") == "failed":
        add(
            "restore_drill_failed",
            "critical",
            "production_restore_drill",
            str(status.restore.get("id", "latest")),
            "Latest restore drill failed",
            status.restore,
        )
    return candidates


def alert_fingerprint(candidate: dict[str, object]) -> str:
    raw = "|".join(
        (
            str(candidate["category"]),
            str(candidate["subjectType"]),
            str(candidate["subjectId"]),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def scan_alerts(
    request: AlertScanRequest,
    *,
    actor: str,
) -> list[OperationalAlertResponse]:
    ensure_schema()
    owner = request.owner or get_settings().operations_alert_default_owner
    payload_hash = canonical_hash({"owner": owner, "actor": actor})
    with connection() as db:
        existing_run = db.execute(
            "SELECT * FROM operational_alert_scan_runs WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing_run is not None:
            if existing_run["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Alert scan idempotency key was reused with a different payload",
                )
            alert_ids = json.loads(existing_run["alert_ids_json"])
            return alerts_by_ids(alert_ids)

    status = collect_production_status()
    timestamp = now_iso()
    touched_ids: list[str] = []
    with connection() as db:
        for candidate in alert_candidates(status):
            fingerprint = alert_fingerprint(candidate)
            details = redact_sensitive(candidate["details"])
            existing = db.execute(
                "SELECT * FROM operational_alerts WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()
            if existing is None:
                alert_id = str(uuid4())
                db.execute(
                    """
                    INSERT INTO operational_alerts (
                        id, fingerprint, category, severity, status, subject_type,
                        subject_id, owner, message, details_json, occurrence_count,
                        first_seen_at, last_seen_at, acknowledged_by, acknowledged_at,
                        closed_by, closed_at, resolution_reason
                    ) VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, 1, ?, ?, NULL, NULL,
                              NULL, NULL, NULL)
                    """,
                    (
                        alert_id,
                        fingerprint,
                        candidate["category"],
                        candidate["severity"],
                        candidate["subjectType"],
                        candidate["subjectId"],
                        owner,
                        candidate["message"],
                        json.dumps(details, ensure_ascii=False, sort_keys=True, default=str),
                        timestamp,
                        timestamp,
                    ),
                )
            else:
                alert_id = existing["id"]
                db.execute(
                    """
                    UPDATE operational_alerts
                    SET severity = ?, status = CASE WHEN status = 'closed' THEN 'open' ELSE status END,
                        owner = ?, message = ?, details_json = ?,
                        occurrence_count = occurrence_count + 1, last_seen_at = ?,
                        acknowledged_by = CASE WHEN status = 'closed' THEN NULL ELSE acknowledged_by END,
                        acknowledged_at = CASE WHEN status = 'closed' THEN NULL ELSE acknowledged_at END,
                        closed_by = NULL, closed_at = NULL,
                        resolution_reason = CASE WHEN status = 'closed' THEN NULL ELSE resolution_reason END
                    WHERE id = ?
                    """,
                    (
                        candidate["severity"],
                        owner,
                        candidate["message"],
                        json.dumps(details, ensure_ascii=False, sort_keys=True, default=str),
                        timestamp,
                        alert_id,
                    ),
                )
            touched_ids.append(alert_id)
        db.execute(
            """
            INSERT INTO operational_alert_scan_runs (
                id, idempotency_key, payload_hash, owner, actor,
                alert_ids_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                request.idempotency_key,
                payload_hash,
                owner,
                actor,
                json.dumps(touched_ids),
                timestamp,
            ),
        )
    audit(
        "operational_alert_scan_completed",
        "operational_alert_scan",
        request.idempotency_key,
        {"actor": actor, "owner": owner, "alertIds": touched_ids, "status": status.status},
    )
    return alerts_by_ids(touched_ids)


def alerts_by_ids(alert_ids: list[str]) -> list[OperationalAlertResponse]:
    if not alert_ids:
        return []
    placeholders = ",".join("?" for _ in alert_ids)
    with connection() as db:
        rows = db.execute(
            f"SELECT * FROM operational_alerts WHERE id IN ({placeholders})",
            tuple(alert_ids),
        ).fetchall()
    by_id = {row["id"]: row for row in rows}
    return [alert_from_row(by_id[alert_id]) for alert_id in alert_ids if alert_id in by_id]


def list_alerts(status: str | None = None) -> list[OperationalAlertResponse]:
    ensure_schema()
    with connection() as db:
        if status is None:
            rows = db.execute(
                "SELECT * FROM operational_alerts ORDER BY last_seen_at DESC"
            ).fetchall()
        else:
            if status not in {"open", "acknowledged", "closed"}:
                raise HTTPException(status_code=422, detail="Unsupported alert status")
            rows = db.execute(
                """
                SELECT * FROM operational_alerts
                WHERE status = ? ORDER BY last_seen_at DESC
                """,
                (status,),
            ).fetchall()
    return [alert_from_row(row) for row in rows]


def transition_alert(
    alert_id: str,
    request: AlertActionRequest,
    *,
    actor: str,
    target_status: Literal["acknowledged", "closed"],
) -> OperationalAlertResponse:
    ensure_schema()
    timestamp = now_iso()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM operational_alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Operational alert not found")
        if target_status == "acknowledged" and row["status"] == "closed":
            raise HTTPException(status_code=409, detail="Closed alert cannot be acknowledged")
        if target_status == "acknowledged":
            db.execute(
                """
                UPDATE operational_alerts
                SET status = 'acknowledged', owner = COALESCE(?, owner),
                    acknowledged_by = ?, acknowledged_at = ?, resolution_reason = ?
                WHERE id = ?
                """,
                (request.owner, actor, timestamp, request.reason, alert_id),
            )
        else:
            db.execute(
                """
                UPDATE operational_alerts
                SET status = 'closed', owner = COALESCE(?, owner),
                    closed_by = ?, closed_at = ?, resolution_reason = ?
                WHERE id = ?
                """,
                (request.owner, actor, timestamp, request.reason, alert_id),
            )
        updated = db.execute(
            "SELECT * FROM operational_alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()
    audit(
        f"operational_alert_{target_status}",
        "operational_alert",
        alert_id,
        {
            "actor": actor,
            "owner": request.owner or updated["owner"],
            "reason": request.reason,
        },
    )
    return alert_from_row(updated)


def run_controlled_operation(
    request: ControlledOperationRequest,
    *,
    actor: str,
) -> ControlledOperationResponse:
    ensure_schema()
    if request.scheduled_for.tzinfo is None:
        raise HTTPException(status_code=422, detail="scheduledFor must include a timezone")
    scheduled_utc = request.scheduled_for.astimezone(UTC)
    if scheduled_utc > datetime.now(UTC) + timedelta(minutes=5):
        raise HTTPException(
            status_code=422,
            detail="Controlled operation must be invoked by the scheduler near scheduledFor",
        )
    payload = {
        "taskType": request.task_type,
        "scheduledFor": scheduled_utc.isoformat(),
        "payload": request.payload,
        "actor": actor,
    }
    payload_hash = canonical_hash(payload)
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM controlled_operation_runs WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
    if existing is not None:
        if existing["payload_hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="Controlled operation idempotency key was reused with a different payload",
            )
        return controlled_from_row(existing)

    run_id = str(uuid4())
    created_at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT INTO controlled_operation_runs (
                id, idempotency_key, payload_hash, task_type, scheduled_for,
                status, actor, result_json, error, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, 'running', ?, '{}', NULL, ?, NULL)
            """,
            (
                run_id,
                request.idempotency_key,
                payload_hash,
                request.task_type,
                scheduled_utc.isoformat(),
                actor,
                created_at,
            ),
        )

    try:
        if request.task_type == "health_scan":
            result_items = scan_alerts(
                AlertScanRequest(
                    idempotencyKey=f"scheduled:{request.idempotency_key}:scan",
                    owner=str(
                        request.payload.get(
                            "owner",
                            get_settings().operations_alert_default_owner,
                        )
                    ),
                ),
                actor=actor,
            )
            result: dict[str, object] = {
                "alertCount": len(result_items),
                "alertIds": [item.alert_id for item in result_items],
            }
        elif request.task_type == "backup":
            backup = create_backup(
                CreateBackupRequest(
                    idempotencyKey=f"scheduled:{request.idempotency_key}:backup",
                    label=str(request.payload.get("label", "scheduled")),
                ),
                actor=actor,
            )
            result = {"backupId": backup.backup_id, "status": backup.status}
        elif request.task_type == "eod":
            eod_payload = dict(request.payload)
            supplied_actor = eod_payload.get("actor")
            if supplied_actor is not None and str(supplied_actor) != actor:
                raise HTTPException(
                    status_code=403,
                    detail="Scheduled EOD actor must match the authenticated principal",
                )
            eod_payload["actor"] = actor
            eod_request = eod_reconciliation.EodReconciliationReportRequest.model_validate(
                eod_payload
            )
            report = eod_reconciliation.create_eod_report(eod_request)
            result = {"reportId": report.report_id, "status": report.status}
        else:  # pragma: no cover - Literal validation rejects unsupported tasks.
            raise HTTPException(status_code=422, detail="Unsupported controlled task")

        completed_at = now_iso()
        safe_result = redact_sensitive(result)
        with connection() as db:
            db.execute(
                """
                UPDATE controlled_operation_runs
                SET status = 'completed', result_json = ?, completed_at = ?, error = NULL
                WHERE id = ?
                """,
                (
                    json.dumps(safe_result, ensure_ascii=False, sort_keys=True, default=str),
                    completed_at,
                    run_id,
                ),
            )
            row = db.execute(
                "SELECT * FROM controlled_operation_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        audit(
            "controlled_operation_completed",
            "controlled_operation",
            run_id,
            {"actor": actor, "taskType": request.task_type, "result": safe_result},
        )
        return controlled_from_row(row)
    except HTTPException:
        raise
    except Exception as exc:
        safe_error = str(redact_sensitive(exc))
        with connection() as db:
            db.execute(
                """
                UPDATE controlled_operation_runs
                SET status = 'failed', error = ?, completed_at = ?
                WHERE id = ?
                """,
                (safe_error, now_iso(), run_id),
            )
        audit(
            "controlled_operation_failed",
            "controlled_operation",
            run_id,
            {"actor": actor, "taskType": request.task_type, "error": safe_error},
        )
        raise HTTPException(status_code=500, detail="Controlled operation failed") from exc


def list_controlled_operations() -> list[ControlledOperationResponse]:
    ensure_schema()
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM controlled_operation_runs ORDER BY created_at DESC"
        ).fetchall()
    return [controlled_from_row(row) for row in rows]


def audit(event_type: str, subject_type: str, subject_id: str, details: dict[str, object]) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                event_type,
                subject_type,
                subject_id,
                json.dumps(
                    redact_sensitive(details),
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ),
                now_iso(),
            ),
        )


def alert_from_row(row) -> OperationalAlertResponse:
    return OperationalAlertResponse(
        alertId=row["id"],
        fingerprint=row["fingerprint"],
        category=row["category"],
        severity=row["severity"],
        status=row["status"],
        subjectType=row["subject_type"],
        subjectId=row["subject_id"],
        owner=row["owner"],
        message=row["message"],
        details=json.loads(row["details_json"]),
        occurrenceCount=row["occurrence_count"],
        firstSeenAt=row["first_seen_at"],
        lastSeenAt=row["last_seen_at"],
        acknowledgedBy=row["acknowledged_by"],
        acknowledgedAt=row["acknowledged_at"],
        closedBy=row["closed_by"],
        closedAt=row["closed_at"],
        resolutionReason=row["resolution_reason"],
    )


def controlled_from_row(row) -> ControlledOperationResponse:
    return ControlledOperationResponse(
        runId=row["id"],
        idempotencyKey=row["idempotency_key"],
        taskType=row["task_type"],
        scheduledFor=row["scheduled_for"],
        status=row["status"],
        actor=row["actor"],
        result=json.loads(row["result_json"]),
        error=row["error"],
        createdAt=row["created_at"],
        completedAt=row["completed_at"],
    )


router = APIRouter(prefix=get_settings().api_prefix, tags=["production-operations"])


@router.get("/ops/production-status", response_model=ProductionStatusResponse)
def production_status() -> ProductionStatusResponse:
    return collect_production_status()


@router.post("/ops/alerts/scan", response_model=list[OperationalAlertResponse])
def run_alert_scan(
    request: AlertScanRequest,
    http_request: Request,
) -> list[OperationalAlertResponse]:
    principal = require_principal(http_request)
    return scan_alerts(request, actor=principal.user_id)


@router.get("/ops/alerts", response_model=list[OperationalAlertResponse])
def alerts(
    status: str | None = Query(default=None),
) -> list[OperationalAlertResponse]:
    return list_alerts(status)


@router.post(
    "/ops/alerts/{alert_id}/acknowledge",
    response_model=OperationalAlertResponse,
)
def acknowledge_alert(
    alert_id: str,
    request: AlertActionRequest,
    http_request: Request,
) -> OperationalAlertResponse:
    principal = require_principal(http_request)
    return transition_alert(
        alert_id,
        request,
        actor=principal.user_id,
        target_status="acknowledged",
    )


@router.post(
    "/ops/alerts/{alert_id}/close",
    response_model=OperationalAlertResponse,
)
def close_alert(
    alert_id: str,
    request: AlertActionRequest,
    http_request: Request,
) -> OperationalAlertResponse:
    principal = require_principal(http_request)
    return transition_alert(
        alert_id,
        request,
        actor=principal.user_id,
        target_status="closed",
    )


@router.post("/ops/controlled-operations", response_model=ControlledOperationResponse)
def create_controlled_operation(
    request: ControlledOperationRequest,
    http_request: Request,
) -> ControlledOperationResponse:
    principal = require_principal(http_request)
    return run_controlled_operation(request, actor=principal.user_id)


@router.get(
    "/ops/controlled-operations",
    response_model=list[ControlledOperationResponse],
)
def controlled_operations() -> list[ControlledOperationResponse]:
    return list_controlled_operations()
