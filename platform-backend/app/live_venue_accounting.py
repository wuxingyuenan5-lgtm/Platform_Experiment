from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import connection
from app.financial_facts import CreateFinancialFactRequest, record_financial_fact
from app.venue_reconciliation import (
    audit,
    canonical_hash,
    runtime_get,
    validate_strategy_account,
)

EconomicEventType = Literal["funding", "swap", "fee"]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS live_economic_event_imports (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    event_type TEXT,
    status TEXT NOT NULL,
    imported_fact_ids_json TEXT NOT NULL,
    skipped_external_ids_json TEXT NOT NULL,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);
"""


class LiveEconomicEventImportRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    event_type: EconomicEventType | None = Field(default=None, alias="eventType")
    actor: str = Field(min_length=1, max_length=128)


class LiveEconomicEventImportResponse(BaseModel):
    import_id: str = Field(alias="importId")
    idempotency_key: str = Field(alias="idempotencyKey")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    event_type: EconomicEventType | None = Field(default=None, alias="eventType")
    status: str
    imported_fact_ids: list[str] = Field(alias="importedFactIds")
    skipped_external_ids: list[str] = Field(alias="skippedExternalIds")
    actor: str
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def import_live_economic_events(
    request: LiveEconomicEventImportRequest,
) -> LiveEconomicEventImportResponse:
    ensure_schema()
    validate_strategy_account(request.strategy_instance_id, request.account_id)
    payload = request.model_dump(by_alias=True, mode="json")
    payload_hash = canonical_hash(payload)
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM live_economic_event_imports WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Economic-event import idempotency key was reused with a different payload",
                )
            return response_from_row(existing)

    params = {"accountId": request.account_id}
    if request.event_type is not None:
        params["eventType"] = request.event_type
    response = runtime_get("/venue/economic-events", params=params)
    response.raise_for_status()
    events = response.json()

    import_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            """
            INSERT INTO live_economic_event_imports (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                event_type, status, imported_fact_ids_json, skipped_external_ids_json,
                actor, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                import_id,
                request.idempotency_key,
                payload_hash,
                request.strategy_instance_id,
                request.account_id,
                request.event_type,
                "processing",
                "[]",
                "[]",
                request.actor,
                created_at,
                None,
            ),
        )

    imported_fact_ids: list[str] = []
    skipped_external_ids: list[str] = []
    for event in events:
        external_id = str(event.get("externalEventId") or "unknown")
        instrument_id = event.get("instrumentId")
        event_type = str(event.get("eventType") or "")
        if instrument_id is None or event_type not in {"funding", "swap", "fee"}:
            skipped_external_ids.append(external_id)
            continue
        fact = record_financial_fact(
            CreateFinancialFactRequest(
                idempotencyKey=f"live-economic:{event['source']}:{external_id}",
                factType=event_type,
                source=event["source"],
                externalId=external_id,
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                instrumentId=instrument_id,
                amount=event["amount"],
                currency=event["currency"],
                occurredAt=event["occurredAt"],
                payload=event,
            )
        )
        imported_fact_ids.append(fact.fact_id)

    completed_at = datetime.now(UTC).isoformat()
    status = "completed" if not skipped_external_ids else "completed_with_skips"
    with connection() as db:
        db.execute(
            """
            UPDATE live_economic_event_imports
            SET status = ?, imported_fact_ids_json = ?, skipped_external_ids_json = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (
                status,
                json.dumps(imported_fact_ids, sort_keys=True),
                json.dumps(skipped_external_ids, sort_keys=True),
                completed_at,
                import_id,
            ),
        )
        row = db.execute(
            "SELECT * FROM live_economic_event_imports WHERE id = ?",
            (import_id,),
        ).fetchone()
    audit(
        "live_economic_events_imported",
        "live_economic_event_import",
        import_id,
        {
            "strategyInstanceId": request.strategy_instance_id,
            "accountId": request.account_id,
            "eventType": request.event_type,
            "importedFactIds": imported_fact_ids,
            "skippedExternalIds": skipped_external_ids,
            "actor": request.actor,
        },
    )
    return response_from_row(row)


def response_from_row(row) -> LiveEconomicEventImportResponse:
    return LiveEconomicEventImportResponse(
        importId=row["id"],
        idempotencyKey=row["idempotency_key"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        eventType=row["event_type"],
        status=row["status"],
        importedFactIds=json.loads(row["imported_fact_ids_json"]),
        skippedExternalIds=json.loads(row["skipped_external_ids_json"]),
        actor=row["actor"],
        createdAt=row["created_at"],
        completedAt=row["completed_at"],
    )


router = APIRouter(prefix=get_settings().api_prefix)


@router.post(
    "/ops/live-economic-events/import",
    response_model=LiveEconomicEventImportResponse,
    tags=["live-accounting"],
)
def import_live_events(
    request: LiveEconomicEventImportRequest,
) -> LiveEconomicEventImportResponse:
    return import_live_economic_events(request)
