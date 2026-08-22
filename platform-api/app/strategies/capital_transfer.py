from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import get_settings
from app.database import connection

CROSS_SPREAD_INSTANCE_ID = "strategy_cross_venue_spread_instance_default"
FUNDING_BRIDGE_ACCOUNT_ID = "fake:bybit-funding"
TRANSFER_CURRENCY = "USDT"

TransferDirection = Literal["bybit_to_mt5", "mt5_to_bybit"]
TransferStatus = Literal["pending", "completed", "failed", "result_unknown"]


class CreateInternalCapitalTransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    direction: TransferDirection
    amount: Decimal = Field(gt=0)

    @field_validator("amount", mode="before")
    @classmethod
    def require_decimal_string(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("amount must be a Decimal string")
        return value


class FundingBalanceQuote(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: Decimal | None
    currency: str
    data_quality_state: Literal["complete", "unavailable"] = Field(alias="dataQualityState")
    as_of: datetime | None = Field(alias="asOf")
    reason: str | None = None


class FundingTransferQuoteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_instance_id: str = Field(alias="strategyInstanceId")
    bybit_transferable: FundingBalanceQuote = Field(alias="bybitTransferable")
    mt5_withdrawable: FundingBalanceQuote = Field(alias="mt5Withdrawable")
    suggested_direction: TransferDirection | None = Field(alias="suggestedDirection")
    suggested_amount: Decimal | None = Field(alias="suggestedAmount")
    mode: Literal["automated", "assisted"]
    official_funding_url: str = Field(alias="officialFundingUrl")
    as_of: datetime = Field(alias="asOf")


class InternalCapitalTransferResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    transfer_id: str = Field(alias="transferId")
    idempotency_key: str = Field(alias="idempotencyKey")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    direction: TransferDirection
    currency: str
    amount: Decimal
    status: TransferStatus
    external_transfer_id: str | None = Field(alias="externalTransferId")
    failure_reason: str | None = Field(alias="failureReason")
    requested_by: str = Field(alias="requestedBy")
    mode: Literal["automated", "assisted"]
    official_funding_url: str = Field(alias="officialFundingUrl")
    current_location: Literal["bybit_uta", "funding", "mt5", "unknown"] = Field(
        alias="currentLocation"
    )
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


def _now() -> datetime:
    return datetime.now(UTC)


def _bound_accounts() -> tuple[str, str]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT sab.account_id, sab.role
            FROM strategy_account_bindings AS sab
            JOIN accounts AS account ON account.id = sab.account_id
            WHERE sab.strategy_instance_id = ?
              AND sab.role IN ('venue_a', 'mt5_leg')
              AND sab.status = 'active'
              AND sab.capability = 'trade_and_read'
              AND account.status IN ('active', 'paused')
            """,
            (CROSS_SPREAD_INSTANCE_ID,),
        ).fetchall()
    by_role = {row["role"]: row["account_id"] for row in rows}
    if len(rows) != 2 or set(by_role) != {"venue_a", "mt5_leg"}:
        raise HTTPException(
            status_code=503,
            detail="Cross-spread funding account bindings are unavailable or ambiguous",
        )
    return by_role["venue_a"], by_role["mt5_leg"]


def _runtime_account_risk(account_id: str) -> dict[str, object]:
    settings = get_settings()
    with httpx.Client(trust_env=False, timeout=settings.runtime_timeout_seconds) as client:
        response = client.get(
            f"{settings.runtime_base_url}/venue/account-risk",
            params={"accountId": account_id},
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Runtime account-risk response is malformed")
    return payload


def _balance_quote(account_id: str) -> tuple[FundingBalanceQuote, str | None]:
    try:
        payload = _runtime_account_risk(account_id)
        amount_value = payload.get("availableBalance")
        if amount_value is None or payload.get("dataQualityState") != "complete":
            raise ValueError("Transferable balance is unavailable")
        amount = Decimal(str(amount_value))
        if amount < 0:
            raise ValueError("Transferable balance is invalid")
        as_of = datetime.fromisoformat(str(payload["asOf"]).replace("Z", "+00:00"))
        return (
            FundingBalanceQuote(
                amount=amount,
                currency=str(payload.get("currency") or TRANSFER_CURRENCY),
                dataQualityState="complete",
                asOf=as_of,
            ),
            str(payload.get("source")) if payload.get("source") is not None else None,
        )
    except (httpx.HTTPError, KeyError, ValueError, ArithmeticError) as exc:
        return (
            FundingBalanceQuote(
                amount=None,
                currency=TRANSFER_CURRENCY,
                dataQualityState="unavailable",
                asOf=None,
                reason=str(exc) or "Balance query failed",
            ),
            None,
        )


def get_funding_transfer_quote() -> FundingTransferQuoteResponse:
    bybit_account_id, mt5_account_id = _bound_accounts()
    bybit, bybit_source = _balance_quote(bybit_account_id)
    mt5, mt5_source = _balance_quote(mt5_account_id)
    direction: TransferDirection | None = None
    amount: Decimal | None = None
    if bybit.amount is not None and mt5.amount is not None:
        if bybit.amount > mt5.amount:
            direction = "bybit_to_mt5"
            amount = min((bybit.amount - mt5.amount) / Decimal("2"), bybit.amount)
        elif mt5.amount > bybit.amount:
            direction = "mt5_to_bybit"
            amount = min((mt5.amount - bybit.amount) / Decimal("2"), mt5.amount)
        else:
            amount = Decimal("0")
    mode: Literal["automated", "assisted"] = (
        "automated" if bybit_source == mt5_source == "fake" else "assisted"
    )
    return FundingTransferQuoteResponse(
        strategyInstanceId=CROSS_SPREAD_INSTANCE_ID,
        bybitTransferable=bybit,
        mt5Withdrawable=mt5,
        suggestedDirection=direction,
        suggestedAmount=amount,
        mode=mode,
        officialFundingUrl=get_settings().bybit_mt5_funding_url,
        asOf=_now(),
    )


def _runtime_transfer_step(
    *,
    idempotency_key: str,
    source_account_id: str,
    destination_account_id: str,
    source_currency: str,
    destination_currency: str,
    amount: Decimal,
) -> dict[str, object]:
    settings = get_settings()
    with httpx.Client(trust_env=False, timeout=settings.runtime_timeout_seconds) as client:
        response = client.post(
            f"{settings.runtime_base_url}/venue/internal-capital-transfers",
            json={
                "idempotencyKey": idempotency_key,
                "sourceAccountId": source_account_id,
                "destinationAccountId": destination_account_id,
                "sourceCurrency": source_currency,
                "destinationCurrency": destination_currency,
                "amount": format(amount, "f"),
            },
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or payload.get("status") not in {
        "completed",
        "result_unknown",
    }:
        raise ValueError("Runtime transfer response is malformed")
    return payload


def create_funding_transfer(
    request: CreateInternalCapitalTransferRequest,
    *,
    requested_by: str,
) -> InternalCapitalTransferResponse:
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM internal_capital_transfers WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
    if existing is not None:
        if (
            existing["direction"] != request.direction
            or Decimal(existing["amount"]) != request.amount
        ):
            raise HTTPException(
                status_code=409,
                detail="Idempotency key is already used by a different funding transfer",
            )
        return _response(existing, mode=_stored_mode(existing))

    bybit_account_id, mt5_account_id = _bound_accounts()
    quote = get_funding_transfer_quote()
    source_quote = (
        quote.bybit_transferable
        if request.direction == "bybit_to_mt5"
        else quote.mt5_withdrawable
    )
    if source_quote.amount is None:
        raise HTTPException(status_code=503, detail="Source transferable balance is unavailable")
    if request.amount > source_quote.amount:
        raise HTTPException(status_code=422, detail="Amount exceeds source transferable balance")

    timestamp = _now().isoformat()
    transfer_id = str(uuid4())
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM internal_capital_transfers WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if (
                existing["direction"] != request.direction
                or Decimal(existing["amount"]) != request.amount
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key is already used by a different funding transfer",
                )
            return _response(existing, mode=_stored_mode(existing))
        db.execute(
            """
            INSERT INTO internal_capital_transfers (
                id, idempotency_key, strategy_instance_id, direction, currency,
                amount, status, external_transfer_id, failure_reason,
                requested_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, ?, ?, ?)
            """,
            (
                transfer_id,
                request.idempotency_key,
                CROSS_SPREAD_INSTANCE_ID,
                request.direction,
                TRANSFER_CURRENCY,
                format(request.amount, "f"),
                requested_by,
                timestamp,
                timestamp,
            ),
        )

    if quote.mode == "assisted":
        return get_funding_transfer(transfer_id)

    if request.direction == "bybit_to_mt5":
        steps = (
            (bybit_account_id, FUNDING_BRIDGE_ACCOUNT_ID, "USDT", "USDT"),
            (FUNDING_BRIDGE_ACCOUNT_ID, mt5_account_id, "USDT", "USD"),
        )
        completed_location = "mt5"
    else:
        steps = (
            (mt5_account_id, FUNDING_BRIDGE_ACCOUNT_ID, "USD", "USDT"),
            (FUNDING_BRIDGE_ACCOUNT_ID, bybit_account_id, "USDT", "USDT"),
        )
        completed_location = "bybit_uta"

    external_ids: list[str] = []
    for step_number, (source, destination, source_currency, destination_currency) in enumerate(
        steps, start=1
    ):
        try:
            result = _runtime_transfer_step(
                idempotency_key=f"{request.idempotency_key}:step:{step_number}",
                source_account_id=source,
                destination_account_id=destination,
                source_currency=source_currency,
                destination_currency=destination_currency,
                amount=request.amount,
            )
        except httpx.HTTPStatusError as exc:
            status: TransferStatus = (
                "result_unknown" if exc.response.status_code >= 500 else "failed"
            )
            if status == "result_unknown":
                reason = (
                    f"Step {step_number} result unknown; automatic retry is disabled: "
                    f"HTTP {exc.response.status_code}"
                )
            else:
                location = (
                    "funding" if step_number == 2 else _source_location(request.direction)
                )
                reason = (
                    f"Step {step_number} failed; funds remain in {location}: "
                    f"HTTP {exc.response.status_code}"
                )
            _finish_transfer(
                transfer_id,
                status=status,
                external_transfer_id=external_ids[-1] if external_ids else None,
                failure_reason=reason,
            )
            return get_funding_transfer(transfer_id)
        except (httpx.HTTPError, ValueError) as exc:
            location = "funding" if step_number == 2 else "unknown"
            reason = f"Step {step_number} result unknown; current location {location}: {exc}"
            _finish_transfer(
                transfer_id,
                status="result_unknown",
                external_transfer_id=external_ids[-1] if external_ids else None,
                failure_reason=reason,
            )
            return get_funding_transfer(transfer_id)
        external_ids.append(str(result["externalTransferId"]))
        if result["status"] == "result_unknown":
            _finish_transfer(
                transfer_id,
                status="result_unknown",
                external_transfer_id=external_ids[-1],
                failure_reason=f"Step {step_number} result unknown; automatic retry is disabled",
            )
            return get_funding_transfer(transfer_id)

    _finish_transfer(
        transfer_id,
        status="completed",
        external_transfer_id=external_ids[-1],
        failure_reason=None,
    )
    response = get_funding_transfer(transfer_id)
    return response.model_copy(update={"current_location": completed_location})


def _source_location(direction: TransferDirection) -> str:
    return "bybit_uta" if direction == "bybit_to_mt5" else "mt5"


def _finish_transfer(
    transfer_id: str,
    *,
    status: TransferStatus,
    external_transfer_id: str | None,
    failure_reason: str | None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE internal_capital_transfers
            SET status = ?, external_transfer_id = ?, failure_reason = ?, updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (status, external_transfer_id, failure_reason, _now().isoformat(), transfer_id),
        )


def get_funding_transfer(transfer_id: str) -> InternalCapitalTransferResponse:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM internal_capital_transfers WHERE id = ?", (transfer_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Funding transfer not found")
    return _response(row, mode=_stored_mode(row))


def _stored_mode(row) -> Literal["automated", "assisted"]:
    return "automated" if row["external_transfer_id"] or row["failure_reason"] else "assisted"


def _response(row, *, mode: Literal["automated", "assisted"]) -> InternalCapitalTransferResponse:
    if row["status"] == "completed":
        location = "mt5" if row["direction"] == "bybit_to_mt5" else "bybit_uta"
    elif row["status"] == "result_unknown":
        location = "unknown"
    elif row["failure_reason"] and "funding" in row["failure_reason"].lower():
        location = "funding"
    else:
        location = _source_location(row["direction"])
    return InternalCapitalTransferResponse(
        transferId=row["id"],
        idempotencyKey=row["idempotency_key"],
        strategyInstanceId=row["strategy_instance_id"],
        direction=row["direction"],
        currency=row["currency"],
        amount=Decimal(row["amount"]),
        status=row["status"],
        externalTransferId=row["external_transfer_id"],
        failureReason=row["failure_reason"],
        requestedBy=row["requested_by"],
        mode=mode,
        officialFundingUrl=get_settings().bybit_mt5_funding_url,
        currentLocation=location,
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )
