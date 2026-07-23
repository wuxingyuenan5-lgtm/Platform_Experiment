from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import require_principal
from app.config import get_settings
from app.database import connection
from app.redaction import redact_sensitive

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS credential_rotation_records (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    credential_ref TEXT NOT NULL,
    provider TEXT NOT NULL,
    version TEXT NOT NULL,
    rotated_at TEXT NOT NULL,
    rotated_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(credential_ref, provider, version)
);

CREATE INDEX IF NOT EXISTS idx_credential_rotation_ref_time
ON credential_rotation_records(credential_ref, rotated_at DESC);
"""


class RecordCredentialRotationRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    credential_ref: str = Field(alias="credentialRef", min_length=10, max_length=512)
    provider: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=128)
    rotated_at: datetime = Field(alias="rotatedAt")
    reason: str = Field(min_length=1, max_length=512)


class CredentialRotationResponse(BaseModel):
    rotation_id: str = Field(alias="rotationId")
    idempotency_key: str = Field(alias="idempotencyKey")
    credential_ref: str = Field(alias="credentialRef")
    provider: str
    version: str
    rotated_at: datetime = Field(alias="rotatedAt")
    rotated_by: str = Field(alias="rotatedBy")
    reason: str
    created_at: datetime = Field(alias="createdAt")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def parse_reference_provider(credential_ref: str) -> str:
    if not credential_ref.startswith("secret://"):
        raise HTTPException(status_code=422, detail="Credential reference must start with secret://")
    body = credential_ref.removeprefix("secret://").strip("/")
    if not body:
        raise HTTPException(status_code=422, detail="Credential reference is empty")
    provider, separator, secret_name = body.partition("/")
    if not separator:
        return "environment"
    if not provider or not secret_name or ".." in secret_name.split("/"):
        raise HTTPException(status_code=422, detail="Credential reference is invalid")
    return provider.lower()


def record_rotation(
    request: RecordCredentialRotationRequest,
    *,
    actor: str,
) -> CredentialRotationResponse:
    ensure_schema()
    reference_provider = parse_reference_provider(request.credential_ref)
    if request.provider.lower() != reference_provider:
        raise HTTPException(
            status_code=422,
            detail="Rotation provider must match the credential reference provider",
        )
    rotated_at = request.rotated_at
    if rotated_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="rotatedAt must include a timezone")
    rotated_iso = rotated_at.astimezone(UTC).isoformat()
    payload = {
        "credentialRef": request.credential_ref,
        "provider": request.provider.lower(),
        "version": request.version,
        "rotatedAt": rotated_iso,
        "rotatedBy": actor,
        "reason": request.reason,
    }
    payload_hash = canonical_hash(payload)

    with connection() as db:
        existing = db.execute(
            """
            SELECT * FROM credential_rotation_records
            WHERE idempotency_key = ?
               OR (credential_ref = ? AND provider = ? AND version = ?)
            LIMIT 1
            """,
            (
                request.idempotency_key,
                request.credential_ref,
                request.provider.lower(),
                request.version,
            ),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Credential rotation identity was reused with a different payload",
                )
            return response_from_row(existing)

        rotation_id = str(uuid4())
        created_at = now_iso()
        db.execute(
            """
            INSERT INTO credential_rotation_records (
                id, idempotency_key, payload_hash, credential_ref, provider,
                version, rotated_at, rotated_by, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rotation_id,
                request.idempotency_key,
                payload_hash,
                request.credential_ref,
                request.provider.lower(),
                request.version,
                rotated_iso,
                actor,
                request.reason,
                created_at,
            ),
        )
        audit_details = redact_sensitive(
            {
                "credentialRef": request.credential_ref,
                "provider": request.provider.lower(),
                "version": request.version,
                "rotatedAt": rotated_iso,
                "rotatedBy": actor,
                "reason": request.reason,
            }
        )
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "credential_rotation_recorded",
                "credential_reference",
                request.credential_ref,
                json.dumps(audit_details, ensure_ascii=False, sort_keys=True),
                created_at,
            ),
        )
        row = db.execute(
            "SELECT * FROM credential_rotation_records WHERE id = ?",
            (rotation_id,),
        ).fetchone()
    return response_from_row(row)


def list_rotations(credential_ref: str | None = None) -> list[CredentialRotationResponse]:
    ensure_schema()
    with connection() as db:
        if credential_ref is None:
            rows = db.execute(
                """
                SELECT * FROM credential_rotation_records
                ORDER BY rotated_at DESC, created_at DESC
                """
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT * FROM credential_rotation_records
                WHERE credential_ref = ?
                ORDER BY rotated_at DESC, created_at DESC
                """,
                (credential_ref,),
            ).fetchall()
    return [response_from_row(row) for row in rows]


def response_from_row(row) -> CredentialRotationResponse:
    return CredentialRotationResponse(
        rotationId=row["id"],
        idempotencyKey=row["idempotency_key"],
        credentialRef=row["credential_ref"],
        provider=row["provider"],
        version=row["version"],
        rotatedAt=row["rotated_at"],
        rotatedBy=row["rotated_by"],
        reason=row["reason"],
        createdAt=row["created_at"],
    )


router = APIRouter(prefix=get_settings().api_prefix, tags=["security"])


@router.post(
    "/security/credential-rotations",
    response_model=CredentialRotationResponse,
)
def create_credential_rotation(
    request: RecordCredentialRotationRequest,
    http_request: Request,
) -> CredentialRotationResponse:
    principal = require_principal(http_request)
    return record_rotation(request, actor=principal.user_id)


@router.get(
    "/security/credential-rotations",
    response_model=list[CredentialRotationResponse],
)
def credential_rotations(
    credential_ref: str | None = None,
) -> list[CredentialRotationResponse]:
    return list_rotations(credential_ref)
