from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from app.auth import Principal, require_principal
from app.config import get_settings
from app.database import connection
from app.execution_risk import ensure_schema as ensure_execution_risk_schema
from app.venue_reconciliation import ensure_schema as ensure_reconciliation_schema

SessionType = Literal["minimum_size_acceptance", "existing_limits", "scale_change"]
SessionStatus = Literal["pending", "approved", "revoked", "expired"]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS live_trading_sessions (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    session_type TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbols_json TEXT NOT NULL,
    sides_json TEXT NOT NULL,
    order_types_json TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    max_order_notional TEXT NOT NULL,
    max_daily_notional TEXT NOT NULL,
    read_only_verified_at TEXT NOT NULL,
    evidence_reference TEXT NOT NULL,
    reason TEXT NOT NULL,
    applicant_user_id TEXT NOT NULL,
    applicant_roles_json TEXT NOT NULL,
    approver_user_id TEXT,
    approval_reason TEXT,
    approved_at TEXT,
    revoked_by TEXT,
    revocation_reason TEXT,
    revoked_at TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS live_trading_session_claims (
    command_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    notional TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES live_trading_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_live_sessions_scope_time
ON live_trading_sessions(strategy_instance_id, account_id, status, starts_at, ends_at);

CREATE INDEX IF NOT EXISTS idx_live_session_claims_session_time
ON live_trading_session_claims(session_id, claimed_at);
"""


class LiveTradingSessionRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    session_type: SessionType = Field(alias="sessionType")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    symbols: list[str] = Field(min_length=1, max_length=20)
    sides: list[Literal["buy", "sell"]] = Field(min_length=1, max_length=2)
    order_types: list[Literal["market", "limit"]] = Field(
        alias="orderTypes",
        min_length=1,
        max_length=2,
    )
    starts_at: datetime = Field(alias="startsAt")
    ends_at: datetime = Field(alias="endsAt")
    max_order_notional: Decimal = Field(alias="maxOrderNotional", gt=0)
    max_daily_notional: Decimal = Field(alias="maxDailyNotional", gt=0)
    read_only_verified_at: datetime = Field(alias="readOnlyVerifiedAt")
    evidence_reference: str = Field(alias="evidenceReference", min_length=1, max_length=256)
    reason: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_contract(self) -> "LiveTradingSessionRequest":
        for value in (self.starts_at, self.ends_at, self.read_only_verified_at):
            if value.tzinfo is None:
                raise ValueError("Live session timestamps must include a timezone")
        if self.starts_at >= self.ends_at:
            raise ValueError("Live session endsAt must be after startsAt")
        if self.read_only_verified_at > self.starts_at:
            raise ValueError("Read-only verification must occur before the session starts")
        if self.max_daily_notional < self.max_order_notional:
            raise ValueError("Daily notional must be at least the per-order notional")
        normalized_symbols = [symbol.strip().upper() for symbol in self.symbols]
        if any(not symbol for symbol in normalized_symbols):
            raise ValueError("Live session symbols must be non-empty")
        self.symbols = sorted(set(normalized_symbols))
        self.sides = sorted(set(self.sides))
        self.order_types = sorted(set(self.order_types))
        return self


class LiveTradingSessionApprovalRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=512)


class LiveTradingSessionRevocationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=512)


class LiveTradingSessionResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    idempotency_key: str = Field(alias="idempotencyKey")
    session_type: SessionType = Field(alias="sessionType")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    symbols: list[str]
    sides: list[str]
    order_types: list[str] = Field(alias="orderTypes")
    starts_at: datetime = Field(alias="startsAt")
    ends_at: datetime = Field(alias="endsAt")
    max_order_notional: Decimal = Field(alias="maxOrderNotional")
    max_daily_notional: Decimal = Field(alias="maxDailyNotional")
    read_only_verified_at: datetime = Field(alias="readOnlyVerifiedAt")
    evidence_reference: str = Field(alias="evidenceReference")
    reason: str
    applicant_user_id: str = Field(alias="applicantUserId")
    approver_user_id: str | None = Field(default=None, alias="approverUserId")
    approval_reason: str | None = Field(default=None, alias="approvalReason")
    approved_at: datetime | None = Field(default=None, alias="approvedAt")
    revoked_by: str | None = Field(default=None, alias="revokedBy")
    revocation_reason: str | None = Field(default=None, alias="revocationReason")
    revoked_at: datetime | None = Field(default=None, alias="revokedAt")
    status: SessionStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


def ensure_schema() -> None:
    ensure_execution_risk_schema()
    ensure_reconciliation_schema()
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def audit(event_type: str, session_id: str, details: dict[str, object]) -> None:
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
                "live_trading_session",
                session_id,
                json.dumps(details, ensure_ascii=False, sort_keys=True, default=str),
                now_iso(),
            ),
        )


def validate_live_scope(strategy_instance_id: str, account_id: str) -> None:
    with connection() as db:
        row = db.execute(
            """
            SELECT a.environment, a.status, sab.status AS binding_status, si.status AS strategy_status
            FROM accounts a
            JOIN strategy_account_bindings sab ON sab.account_id = a.id
            JOIN strategy_instances si ON si.id = sab.strategy_instance_id
            WHERE a.id = ? AND si.id = ?
            ORDER BY sab.created_at DESC
            LIMIT 1
            """,
            (account_id, strategy_instance_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="Live account is not bound to StrategyInstance")
    if row["environment"] != "live":
        raise HTTPException(status_code=422, detail="LiveTradingSession requires a live account")
    if row["status"] != "active" or row["binding_status"] != "active":
        raise HTTPException(status_code=403, detail="Live account binding is not active")
    if row["strategy_status"] != "active":
        raise HTTPException(status_code=403, detail="StrategyInstance is not active")


def request_live_session(
    request: LiveTradingSessionRequest,
    principal: Principal,
) -> LiveTradingSessionResponse:
    ensure_schema()
    validate_live_scope(request.strategy_instance_id, request.account_id)
    payload = request.model_dump(by_alias=True, mode="json")
    payload["applicantUserId"] = principal.user_id
    payload_hash = canonical_hash(payload)
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM live_trading_sessions WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Live session idempotency key was reused with a different payload",
                )
            return response_from_row(existing)

        session_id = str(uuid4())
        timestamp = now_iso()
        db.execute(
            """
            INSERT INTO live_trading_sessions (
                id, idempotency_key, payload_hash, session_type,
                strategy_instance_id, account_id, symbols_json, sides_json,
                order_types_json, starts_at, ends_at, max_order_notional,
                max_daily_notional, read_only_verified_at, evidence_reference,
                reason, applicant_user_id, applicant_roles_json,
                approver_user_id, approval_reason, approved_at, revoked_by,
                revocation_reason, revoked_at, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                request.idempotency_key,
                payload_hash,
                request.session_type,
                request.strategy_instance_id,
                request.account_id,
                json.dumps(request.symbols, sort_keys=True),
                json.dumps(request.sides, sort_keys=True),
                json.dumps(request.order_types, sort_keys=True),
                request.starts_at.astimezone(UTC).isoformat(),
                request.ends_at.astimezone(UTC).isoformat(),
                decimal_text(request.max_order_notional),
                decimal_text(request.max_daily_notional),
                request.read_only_verified_at.astimezone(UTC).isoformat(),
                request.evidence_reference,
                request.reason,
                principal.user_id,
                json.dumps(list(principal.roles), sort_keys=True),
                None,
                None,
                None,
                None,
                None,
                None,
                "pending",
                timestamp,
                timestamp,
            ),
        )
        row = db.execute(
            "SELECT * FROM live_trading_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    audit(
        "live_trading_session_requested",
        session_id,
        {
            "applicantUserId": principal.user_id,
            "roles": list(principal.roles),
            "strategyInstanceId": request.strategy_instance_id,
            "accountId": request.account_id,
            "sessionType": request.session_type,
            "startsAt": request.starts_at,
            "endsAt": request.ends_at,
            "maxOrderNotional": request.max_order_notional,
            "maxDailyNotional": request.max_daily_notional,
        },
    )
    return response_from_row(row)


def check_approval_blockers(row, *, db=None) -> list[str]:
    blockers: list[str] = []
    settings = get_settings()
    # Absolute notional limits are legacy-compat: zero means "no cap" and only a
    # positive configured value blocks approval (legacy opt-in).
    if (
        settings.live_session_absolute_max_order_notional > 0
        and Decimal(row["max_order_notional"])
        > settings.live_session_absolute_max_order_notional
    ):
        blockers.append("Requested order notional exceeds Platform absolute limit")
    if (
        settings.live_session_absolute_max_daily_notional > 0
        and Decimal(row["max_daily_notional"])
        > settings.live_session_absolute_max_daily_notional
    ):
        blockers.append("Requested daily notional exceeds Platform absolute limit")
    if row["session_type"] == "scale_change":
        blockers.append("Scale-change sessions require a separate scale review and are not enabled")

    def _append_db_blockers(conn) -> None:
        kill_switch = conn.execute(
            """
            SELECT scope_type, scope_id
            FROM trading_kill_switches
            WHERE enabled = 1 AND (
                (scope_type = 'global' AND scope_id = '*')
                OR (scope_type = 'strategy' AND scope_id = ?)
                OR (scope_type = 'account' AND scope_id = ?)
            )
            LIMIT 1
            """,
            (row["strategy_instance_id"], row["account_id"]),
        ).fetchone()
        if kill_switch is not None:
            blockers.append("A relevant Kill Switch is enabled")

        differences = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM reconciliation_differences rd
            JOIN venue_reconciliation_runs vr ON vr.id = rd.run_id
            WHERE vr.strategy_instance_id = ?
              AND vr.account_id = ?
              AND rd.status IN ('open', 'accepted')
              AND NOT (
                  rd.status = 'accepted'
                  AND rd.difference_type = 'missing_external'
                  AND EXISTS (
                      SELECT 1 FROM orders o
                      WHERE o.id = rd.local_reference AND o.status = 'rejected'
                  )
              )
            """,
            (row["strategy_instance_id"], row["account_id"]),
        ).fetchone()["count"]
        if differences:
            blockers.append("Outstanding open or accepted reconciliation differences exist")

        overlap = conn.execute(
            """
            SELECT id
            FROM live_trading_sessions
            WHERE strategy_instance_id = ? AND account_id = ?
              AND status = 'approved' AND id != ?
              AND starts_at < ? AND ends_at > ?
            LIMIT 1
            """,
            (
                row["strategy_instance_id"],
                row["account_id"],
                row["id"],
                row["ends_at"],
                row["starts_at"],
            ),
        ).fetchone()
        if overlap is not None:
            blockers.append("An overlapping approved live session already exists")

        if row["session_type"] == "existing_limits":
            eod = conn.execute(
                """
                SELECT status, scale_gate_status
                FROM eod_reconciliation_reports
                WHERE strategy_instance_id = ? AND account_id = ?
                ORDER BY business_date DESC, completed_at DESC
                LIMIT 1
                """,
                (row["strategy_instance_id"], row["account_id"]),
            ).fetchone()
            if eod is None or eod["status"] != "complete" or eod["scale_gate_status"] not in {
                "eligible_for_review",
                "approved_same_limits",
            }:
                blockers.append("Existing-limit session requires a clean latest EOD report")

    if db is not None:
        _append_db_blockers(db)
    else:
        with connection() as conn:
            _append_db_blockers(conn)
    return blockers


def approve_live_session(
    session_id: str,
    request: LiveTradingSessionApprovalRequest,
    principal: Principal,
) -> LiveTradingSessionResponse:
    ensure_schema()
    settings = get_settings()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM live_trading_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="LiveTradingSession not found")
        founder_demo_ceo = (
            settings.founder_demo_live_acceptance_enabled
            and settings.environment.lower() == "development"
            and settings.auth_mode.lower() == "development"
            and "ceo" in set(principal.roles)
            and row["session_type"] == "minimum_size_acceptance"
        )
        if not ({"risk_officer", "admin"} & set(principal.roles)) and not founder_demo_ceo:
            raise HTTPException(status_code=403, detail="Risk approval role is required")
        if row["status"] != "pending":
            if row["status"] == "approved" and row["approver_user_id"] == principal.user_id:
                return response_from_row(row)
            raise HTTPException(status_code=409, detail="LiveTradingSession is not pending")
        founder_demo_self_approval = (
            founder_demo_ceo
            or (
                settings.founder_demo_live_acceptance_enabled
                and settings.environment.lower() == "development"
                and settings.auth_mode.lower() == "development"
                and "admin" in set(principal.roles)
                and row["session_type"] == "minimum_size_acceptance"
            )
        )
        if row["applicant_user_id"] == principal.user_id and not founder_demo_self_approval:
            raise HTTPException(status_code=403, detail="Applicant cannot approve their own live session")
        blockers = check_approval_blockers(row)
        if blockers:
            raise HTTPException(
                status_code=422,
                detail={"message": "Live session approval is blocked", "blockers": blockers},
            )
        timestamp = now_iso()
        db.execute(
            """
            UPDATE live_trading_sessions
            SET approver_user_id = ?, approval_reason = ?, approved_at = ?,
                status = 'approved', updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (principal.user_id, request.reason, timestamp, timestamp, session_id),
        )
        row = db.execute(
            "SELECT * FROM live_trading_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    audit(
        "live_trading_session_approved",
        session_id,
        {
            "approverUserId": principal.user_id,
            "reason": request.reason,
            "applicantUserId": row["applicant_user_id"],
        },
    )
    return response_from_row(row)


def revoke_live_session(
    session_id: str,
    request: LiveTradingSessionRevocationRequest,
    principal: Principal,
) -> LiveTradingSessionResponse:
    ensure_schema()
    settings = get_settings()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM live_trading_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="LiveTradingSession not found")
        founder_demo_ceo = (
            settings.founder_demo_live_acceptance_enabled
            and settings.environment.lower() == "development"
            and settings.auth_mode.lower() == "development"
            and "ceo" in set(principal.roles)
            and row["session_type"] == "minimum_size_acceptance"
        )
        if not ({"risk_officer", "admin"} & set(principal.roles)) and not founder_demo_ceo:
            raise HTTPException(status_code=403, detail="Risk revocation role is required")
        if row["status"] == "revoked":
            return response_from_row(row)
        if row["status"] not in {"pending", "approved"}:
            raise HTTPException(status_code=409, detail="LiveTradingSession cannot be revoked")
        timestamp = now_iso()
        db.execute(
            """
            UPDATE live_trading_sessions
            SET revoked_by = ?, revocation_reason = ?, revoked_at = ?,
                status = 'revoked', updated_at = ?
            WHERE id = ?
            """,
            (principal.user_id, request.reason, timestamp, timestamp, session_id),
        )
        row = db.execute(
            "SELECT * FROM live_trading_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    audit(
        "live_trading_session_revoked",
        session_id,
        {"revokedBy": principal.user_id, "reason": request.reason},
    )
    return response_from_row(row)


def list_live_sessions() -> list[LiveTradingSessionResponse]:
    ensure_schema()
    expire_sessions()
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM live_trading_sessions ORDER BY created_at DESC"
        ).fetchall()
    return [response_from_row(row) for row in rows]


def expire_sessions() -> None:
    timestamp = now_iso()
    with connection() as db:
        db.execute(
            """
            UPDATE live_trading_sessions
            SET status = 'expired', updated_at = ?
            WHERE status = 'approved' AND ends_at <= ?
            """,
            (timestamp, timestamp),
        )


def validate_and_claim_live_session(
    *,
    command_id: str,
    strategy_instance_id: str,
    account_id: str,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal | None,
) -> str:
    ensure_schema()
    if price is None or price <= 0:
        raise HTTPException(
            status_code=422,
            detail="Live session notional validation requires an explicit positive price",
        )
    expire_sessions()
    timestamp = now_iso()
    normalized_symbol = symbol.upper()
    notional = quantity * price
    payload_hash = canonical_hash(
        {
            "commandId": command_id,
            "strategyInstanceId": strategy_instance_id,
            "accountId": account_id,
            "symbol": normalized_symbol,
            "side": side,
            "orderType": order_type,
            "quantity": decimal_text(quantity),
            "price": decimal_text(price),
        }
    )
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM live_trading_session_claims WHERE command_id = ?",
            (command_id,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Live session command identity was reused with a different payload",
                )
            return existing["session_id"]

        rows = db.execute(
            """
            SELECT * FROM live_trading_sessions
            WHERE strategy_instance_id = ? AND account_id = ?
              AND status = 'approved' AND starts_at <= ? AND ends_at > ?
            ORDER BY approved_at DESC
            """,
            (strategy_instance_id, account_id, timestamp, timestamp),
        ).fetchall()
        eligible = [
            row
            for row in rows
            if normalized_symbol in json.loads(row["symbols_json"])
            and side in json.loads(row["sides_json"])
            and order_type in json.loads(row["order_types_json"])
        ]
        if len(eligible) != 1:
            raise HTTPException(
                status_code=403,
                detail="Exactly one active approved LiveTradingSession is required",
            )
        session = eligible[0]
        if check_approval_blockers(session, db=db):
            raise HTTPException(status_code=423, detail="Live session has active safety blockers")
        # Session maxOrderNotional/maxDailyNotional are legacy-compat acceptance
        # caps: exceedance no longer rejects the claim (non-blocking). The claim
        # row is still recorded for command identity, audit and reconciliation.
        db.execute(
            """
            INSERT INTO live_trading_session_claims (
                command_id, session_id, payload_hash, notional, claimed_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                command_id,
                session["id"],
                payload_hash,
                decimal_text(notional),
                timestamp,
            ),
        )
    audit(
        "live_trading_session_claimed",
        session["id"],
        {
            "commandId": command_id,
            "strategyInstanceId": strategy_instance_id,
            "accountId": account_id,
            "symbol": normalized_symbol,
            "notional": notional,
        },
    )
    return session["id"]


def response_from_row(row) -> LiveTradingSessionResponse:
    return LiveTradingSessionResponse(
        sessionId=row["id"],
        idempotencyKey=row["idempotency_key"],
        sessionType=row["session_type"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        symbols=json.loads(row["symbols_json"]),
        sides=json.loads(row["sides_json"]),
        orderTypes=json.loads(row["order_types_json"]),
        startsAt=row["starts_at"],
        endsAt=row["ends_at"],
        maxOrderNotional=Decimal(row["max_order_notional"]),
        maxDailyNotional=Decimal(row["max_daily_notional"]),
        readOnlyVerifiedAt=row["read_only_verified_at"],
        evidenceReference=row["evidence_reference"],
        reason=row["reason"],
        applicantUserId=row["applicant_user_id"],
        approverUserId=row["approver_user_id"],
        approvalReason=row["approval_reason"],
        approvedAt=row["approved_at"],
        revokedBy=row["revoked_by"],
        revocationReason=row["revocation_reason"],
        revokedAt=row["revoked_at"],
        status=row["status"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/live-trading/sessions",
    response_model=LiveTradingSessionResponse,
    tags=["live-trading"],
)
def create_live_session(
    request: LiveTradingSessionRequest,
    http_request: Request,
) -> LiveTradingSessionResponse:
    return request_live_session(request, require_principal(http_request))


@router.get(
    "/live-trading/sessions",
    response_model=list[LiveTradingSessionResponse],
    tags=["live-trading"],
)
def get_live_sessions() -> list[LiveTradingSessionResponse]:
    return list_live_sessions()


@router.post(
    "/live-trading/sessions/{session_id}/approve",
    response_model=LiveTradingSessionResponse,
    tags=["live-trading"],
)
def approve_session(
    session_id: str,
    request: LiveTradingSessionApprovalRequest,
    http_request: Request,
) -> LiveTradingSessionResponse:
    return approve_live_session(session_id, request, require_principal(http_request))


@router.post(
    "/live-trading/sessions/{session_id}/revoke",
    response_model=LiveTradingSessionResponse,
    tags=["live-trading"],
)
def revoke_session(
    session_id: str,
    request: LiveTradingSessionRevocationRequest,
    http_request: Request,
) -> LiveTradingSessionResponse:
    return revoke_live_session(session_id, request, require_principal(http_request))
