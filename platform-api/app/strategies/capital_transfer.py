from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import IntegrityError
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import execution_risk_repository as risk_repository
from app.config import get_settings
from app.database import connection

CROSS_SPREAD_INSTANCE_ID = "strategy_cross_venue_spread_instance_default"
FUNDING_BRIDGE_ACCOUNT_ID = "fake:bybit-funding"
TRANSFER_CURRENCY = "USDT"
ASSISTED_BALANCE_TOLERANCE = Decimal("0.01")

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
    mode: Literal["automated", "unavailable"]
    readiness_reason: str | None = Field(default=None, alias="readinessReason")
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


def _runtime_transfer_readiness(
    source_account_id: str,
    destination_account_id: str,
) -> dict[str, object]:
    settings = get_settings()
    try:
        with httpx.Client(trust_env=False, timeout=settings.runtime_timeout_seconds) as client:
            response = client.get(
                f"{settings.runtime_base_url}/venue/internal-capital-transfers/readiness",
                params={
                    "sourceAccountId": source_account_id,
                    "destinationAccountId": destination_account_id,
                    "currency": TRANSFER_CURRENCY,
                },
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Runtime transfer readiness response is malformed")
        return payload
    except (httpx.HTTPError, ValueError) as exc:
        return {"ready": False, "reason": str(exc) or "Runtime transfer readiness failed"}


def _readiness_balance(payload: dict[str, object]) -> FundingBalanceQuote:
    ready = payload.get("ready") is True
    raw_amount = payload.get("transferableBalance")
    if not ready or raw_amount in (None, ""):
        return FundingBalanceQuote(
            amount=None,
            currency=TRANSFER_CURRENCY,
            dataQualityState="unavailable",
            asOf=None,
            reason=str(payload.get("reason") or "Automated transfer is unavailable"),
        )
    try:
        amount = Decimal(str(raw_amount))
        as_of = datetime.fromisoformat(str(payload["checkedAt"]).replace("Z", "+00:00"))
    except (KeyError, ValueError, ArithmeticError) as exc:
        return FundingBalanceQuote(
            amount=None,
            currency=TRANSFER_CURRENCY,
            dataQualityState="unavailable",
            asOf=None,
            reason=f"Invalid Runtime transfer readiness: {exc}",
        )
    return FundingBalanceQuote(
        amount=amount,
        currency=TRANSFER_CURRENCY,
        dataQualityState="complete",
        asOf=as_of,
    )


def get_funding_transfer_quote() -> FundingTransferQuoteResponse:
    bybit_account_id, mt5_account_id = _bound_accounts()
    forward = _runtime_transfer_readiness(bybit_account_id, mt5_account_id)
    reverse = _runtime_transfer_readiness(mt5_account_id, bybit_account_id)
    bybit = _readiness_balance(forward)
    mt5 = _readiness_balance(reverse)
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
    mode: Literal["automated", "unavailable"] = (
        "automated"
        if forward.get("ready") is True and reverse.get("ready") is True
        else "unavailable"
    )
    readiness_reason = None
    if mode == "unavailable":
        readiness_reason = str(
            forward.get("reason") or reverse.get("reason") or "Automated transfer is unavailable"
        )
    return FundingTransferQuoteResponse(
        strategyInstanceId=CROSS_SPREAD_INSTANCE_ID,
        bybitTransferable=bybit,
        mt5Withdrawable=mt5,
        suggestedDirection=direction,
        suggestedAmount=amount,
        mode=mode,
        readinessReason=readiness_reason,
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


def _runtime_transfer_status(row) -> dict[str, object]:
    settings = get_settings()
    source_account_id = str(row["source_account_id"])
    destination_account_id = str(row["destination_account_id"])
    with httpx.Client(trust_env=False, timeout=settings.runtime_timeout_seconds) as client:
        response = client.get(
            (
                f"{settings.runtime_base_url}/venue/internal-capital-transfers/"
                f"{row['external_transfer_id']}"
            ),
            params={
                "idempotencyKey": f"{row['idempotency_key']}:step:1",
                "sourceAccountId": source_account_id,
                "destinationAccountId": destination_account_id,
                "sourceCurrency": TRANSFER_CURRENCY,
                "destinationCurrency": TRANSFER_CURRENCY,
                "amount": str(row["amount"]),
            },
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or payload.get("status") not in {
        "completed",
        "result_unknown",
    }:
        raise ValueError("Runtime transfer status response is malformed")
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
    if quote.mode != "automated":
        raise HTTPException(
            status_code=423,
            detail=quote.readiness_reason or "Automated MT5/TradFi transfer is unavailable",
        )
    source_quote = (
        quote.bybit_transferable
        if request.direction == "bybit_to_mt5"
        else quote.mt5_withdrawable
    )
    destination_quote = (
        quote.mt5_withdrawable
        if request.direction == "bybit_to_mt5"
        else quote.bybit_transferable
    )
    if source_quote.amount is None:
        raise HTTPException(status_code=503, detail="Source transferable balance is unavailable")
    if destination_quote.amount is None:
        raise HTTPException(
            status_code=503,
            detail="Destination transferable balance is unavailable",
        )
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
        for account_id in (bybit_account_id, mt5_account_id):
            if (
                risk_repository.active_non_account_claim_for_account(account_id, db=db)
                is not None
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Active execution resource claim blocks funding transfer "
                        f"for {account_id}"
                    ),
                )
        source_account_id = (
            bybit_account_id
            if request.direction == "bybit_to_mt5"
            else mt5_account_id
        )
        active_reserved = risk_repository.active_reserved_amount(
            source_account_id,
            TRANSFER_CURRENCY,
            db=db,
        )
        if active_reserved + request.amount > source_quote.amount:
            raise HTTPException(
                status_code=409,
                detail="Available balance reservation is insufficient for funding transfer",
            )
        for account_id in (bybit_account_id, mt5_account_id):
            venue_row = db.execute(
                "SELECT venue_id FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            assert venue_row is not None
            resource_key = f"{account_id}|{venue_row['venue_id']}|account|*"
            blocking_claim = risk_repository.active_claim_for_resource(
                resource_key,
                account_id=account_id,
                db=db,
            )
            if blocking_claim is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Active execution resource claim blocks funding transfer "
                        f"for {account_id}"
                    ),
                )
            try:
                db.execute(
                    """
                    INSERT INTO execution_resource_claims (
                        id, resource_key, owner_type, owner_id, account_id, venue_id,
                        resource_category, symbol, status, created_at, updated_at
                    ) VALUES (?, ?, 'transfer', ?, ?, ?, 'account', '*', 'active', ?, ?)
                    """,
                    (
                        str(uuid4()),
                        resource_key,
                        transfer_id,
                        account_id,
                        str(venue_row["venue_id"]),
                        timestamp,
                        timestamp,
                    ),
                )
            except IntegrityError as exc:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Active execution resource claim blocks funding transfer "
                        f"for {account_id}"
                    ),
                ) from exc
        db.execute(
            """
            INSERT INTO execution_balance_reservations (
                id, owner_type, owner_id, account_id, strategy_instance_id, instruction_id,
                currency, reserved_amount, status, created_at, updated_at
            ) VALUES (?, 'transfer', ?, ?, ?, NULL, ?, ?, 'active', ?, ?)
            """,
            (
                str(uuid4()),
                transfer_id,
                source_account_id,
                CROSS_SPREAD_INSTANCE_ID,
                TRANSFER_CURRENCY,
                format(request.amount, "f"),
                timestamp,
                timestamp,
            ),
        )
        db.execute(
            """
            INSERT INTO internal_capital_transfers (
                id, idempotency_key, strategy_instance_id, direction, currency,
                amount, status, external_transfer_id, failure_reason,
                requested_by, created_at, updated_at, mode,
                source_account_id, destination_account_id,
                source_balance_before, destination_balance_before
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
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
                quote.mode,
                source_account_id,
                mt5_account_id
                if request.direction == "bybit_to_mt5"
                else bybit_account_id,
                format(source_quote.amount, "f"),
                format(destination_quote.amount, "f"),
            ),
        )

    direction_readiness = _runtime_transfer_readiness(
        source_account_id,
        mt5_account_id if request.direction == "bybit_to_mt5" else bybit_account_id,
    )
    is_simulation = direction_readiness.get("fromAccountType") == "simulation"
    if not is_simulation:
        steps = (
            (
                source_account_id,
                mt5_account_id if request.direction == "bybit_to_mt5" else bybit_account_id,
                "USDT",
                "USDT",
            ),
        )
        completed_location = "mt5" if request.direction == "bybit_to_mt5" else "bybit_uta"
    elif request.direction == "bybit_to_mt5":
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


def _source_location(direction: TransferDirection) -> Literal["bybit_uta", "mt5"]:
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
            WHERE id = ? AND status IN ('pending', 'result_unknown')
            """,
            (status, external_transfer_id, failure_reason, _now().isoformat(), transfer_id),
        )
        if status in {"completed", "failed"}:
            risk_repository.release_claims_for_owner("transfer", transfer_id, db=db)
            risk_repository.release_reservations_for_owner("transfer", transfer_id, db=db)


def get_funding_transfer(transfer_id: str) -> InternalCapitalTransferResponse:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM internal_capital_transfers WHERE id = ?", (transfer_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Funding transfer not found")
    mode = _stored_mode(row)
    if (
        row["status"] in {"pending", "result_unknown"}
        and mode == "automated"
        and row["external_transfer_id"]
    ):
        _reconcile_automated_transfer(row)
        with connection() as db:
            row = db.execute(
                "SELECT * FROM internal_capital_transfers WHERE id = ?", (transfer_id,)
            ).fetchone()
        assert row is not None
    elif row["status"] == "pending" and mode == "assisted":
        _reconcile_assisted_transfer(row)
        with connection() as db:
            row = db.execute(
                "SELECT * FROM internal_capital_transfers WHERE id = ?", (transfer_id,)
            ).fetchone()
        assert row is not None
    return _response(row, mode=_stored_mode(row))


def _reconcile_automated_transfer(row) -> None:
    try:
        result = _runtime_transfer_status(row)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            _finish_transfer(
                str(row["id"]),
                status="failed",
                external_transfer_id=str(row["external_transfer_id"]),
                failure_reason="Bybit authoritatively reported the transfer as failed",
            )
        return
    except (httpx.HTTPError, ValueError):
        return
    if result["status"] == "completed":
        _finish_transfer(
            str(row["id"]),
            status="completed",
            external_transfer_id=str(row["external_transfer_id"]),
            failure_reason=None,
        )


def cancel_funding_transfer(
    transfer_id: str,
    *,
    requested_by: str,
) -> InternalCapitalTransferResponse:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM internal_capital_transfers WHERE id = ?", (transfer_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Funding transfer not found")
    if _stored_mode(row) != "assisted":
        raise HTTPException(status_code=409, detail="Only assisted transfers can be cancelled")
    if row["status"] != "pending":
        if row["status"] == "failed" and row["failure_reason"] == "Assisted transfer cancelled":
            return _response(row, mode="assisted")
        raise HTTPException(status_code=409, detail="Funding transfer is no longer pending")
    if not _has_assisted_baseline(row):
        raise HTTPException(
            status_code=409,
            detail="Legacy assisted transfer requires manual balance review before release",
        )
    source, _ = _balance_quote(str(row["source_account_id"]))
    destination, _ = _balance_quote(str(row["destination_account_id"]))
    if source.amount is None or destination.amount is None:
        raise HTTPException(status_code=503, detail="Current balances are unavailable")
    source_before = Decimal(str(row["source_balance_before"]))
    destination_before = Decimal(str(row["destination_balance_before"]))
    if (
        abs(source.amount - source_before) > ASSISTED_BALANCE_TOLERANCE
        or abs(destination.amount - destination_before) > ASSISTED_BALANCE_TOLERANCE
    ):
        raise HTTPException(
            status_code=409,
            detail="Account balances changed; reconcile the assisted transfer before cancellation",
        )
    _finish_transfer(
        transfer_id,
        status="failed",
        external_transfer_id=None,
        failure_reason="Assisted transfer cancelled",
    )
    risk_repository.audit(
        "assisted_capital_transfer_cancelled",
        "internal_capital_transfer",
        transfer_id,
        {"requestedBy": requested_by},
    )
    return get_funding_transfer(transfer_id)


def _has_assisted_baseline(row) -> bool:
    return all(
        row[key] not in (None, "")
        for key in (
            "source_account_id",
            "destination_account_id",
            "source_balance_before",
            "destination_balance_before",
        )
    )


def _reconcile_assisted_transfer(row) -> None:
    if not _has_assisted_baseline(row):
        return
    source, _ = _balance_quote(str(row["source_account_id"]))
    destination, _ = _balance_quote(str(row["destination_account_id"]))
    if source.amount is None or destination.amount is None:
        return
    amount = Decimal(str(row["amount"]))
    expected_source = Decimal(str(row["source_balance_before"])) - amount
    expected_destination = Decimal(str(row["destination_balance_before"])) + amount
    if (
        source.amount <= expected_source + ASSISTED_BALANCE_TOLERANCE
        and destination.amount >= expected_destination - ASSISTED_BALANCE_TOLERANCE
    ):
        _finish_transfer(
            str(row["id"]),
            status="completed",
            external_transfer_id=None,
            failure_reason=None,
        )
        risk_repository.audit(
            "assisted_capital_transfer_reconciled",
            "internal_capital_transfer",
            str(row["id"]),
            {"direction": row["direction"], "amount": row["amount"]},
        )


def _stored_mode(row) -> Literal["automated", "assisted"]:
    if "mode" in row.keys() and row["mode"] in {"automated", "assisted"}:
        return row["mode"]
    return "automated" if row["external_transfer_id"] or row["failure_reason"] else "assisted"


def _response(row, *, mode: Literal["automated", "assisted"]) -> InternalCapitalTransferResponse:
    location: Literal["bybit_uta", "funding", "mt5", "unknown"]
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
