from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import cast

from app.config import get_settings
from app.database import connection
from app.member_holding_decimal import (
    HoldingDecimalError,
    calculate_holding,
    canonical_decimal,
    parse_non_negative_decimal,
)
from app.member_holding_repository import (
    FundNotFoundError,
    FundRecord,
    MemberHoldingRecord,
    MemberHoldingRepositoryError,
    MemberHoldingVersionError,
    get_fund,
    get_latest_available_nav,
    insert_fund_nav,
    list_funds,
    list_member_holdings,
    update_fund_code,
    upsert_member_holding,
)
from app.member_holding_schemas import (
    FundListResponse,
    FundNavMutationResponse,
    FundSummaryResponse,
    HoldingSource,
    HoldingStatus,
    MemberHoldingListResponse,
    MemberHoldingResponse,
    NavStatus,
    UpsertFundNavRequest,
    UpsertMemberHoldingRequest,
)
from app.user_admin_policy import UserAdminPolicyError, assert_recent_reauthentication
from app.user_admin_service import AdminRequestContext
from app.user_repository import (
    SessionSummaryRecord,
    get_user_by_id,
    insert_audit_event,
    list_active_user_sessions,
)


class MemberHoldingServiceError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def _now(value: datetime | None = None) -> datetime:
    return (value or datetime.now(UTC)).astimezone(UTC)


def _fund_response(fund: FundRecord) -> FundSummaryResponse:
    return FundSummaryResponse(
        fundId=fund.id,
        fundName=fund.name,
        fundCode=fund.fund_code,
        baseCurrency=fund.base_currency,
    )


def _current_session(
    db: sqlite3.Connection,
    context: AdminRequestContext,
) -> SessionSummaryRecord | None:
    return next(
        (
            session
            for session in list_active_user_sessions(db, context.actor_user_id)
            if session.id == context.session_id
        ),
        None,
    )


def _require_recent(
    db: sqlite3.Connection,
    context: AdminRequestContext,
    current: datetime,
) -> None:
    assert_recent_reauthentication(
        session=_current_session(db, context),
        settings=get_settings(),
        now=current,
    )


def _assert_member_target(db: sqlite3.Connection, user_id: str) -> None:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise MemberHoldingServiceError(404, "user_not_found", "User does not exist")
    if user.role_code != "member" or user.lifecycle_status not in {"active", "disabled"}:
        raise MemberHoldingServiceError(
            422,
            "member_target_required",
            "持仓目标必须是已批准的会员账号",
        )


def _parse_aware(value: str, *, field: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise MemberHoldingServiceError(503, "invalid_timestamp", f"{field} lacks timezone")
    return parsed.astimezone(UTC)


def _holding_response(
    db: sqlite3.Connection,
    holding: MemberHoldingRecord,
    *,
    current: datetime,
) -> MemberHoldingResponse:
    fund = get_fund(db, holding.fund_id)
    if fund is None:
        raise MemberHoldingServiceError(503, "fund_unavailable", "Holding fund is unavailable")
    try:
        share_quantity = parse_non_negative_decimal(
            holding.share_quantity,
            field="shareQuantity",
        )
        cumulative_invested = parse_non_negative_decimal(
            holding.cumulative_invested,
            field="cumulativeInvested",
        )
    except HoldingDecimalError as exc:
        raise MemberHoldingServiceError(503, "holding_decimal_invalid", str(exc)) from exc

    nav = get_latest_available_nav(db, holding.fund_id)
    unit_nav = None
    nav_status: NavStatus = "unavailable"
    nav_valuation_time = None
    currency = fund.base_currency
    if nav is not None:
        try:
            unit_nav = parse_non_negative_decimal(nav.unit_nav, field="unitNav")
        except HoldingDecimalError as exc:
            raise MemberHoldingServiceError(503, "fund_nav_decimal_invalid", str(exc)) from exc
        nav_valuation_time = _parse_aware(nav.valuation_time, field="valuationTime")
        if nav_valuation_time > current + timedelta(minutes=5):
            raise MemberHoldingServiceError(
                503,
                "fund_nav_timestamp_invalid",
                "Fund NAV valuation time is unexpectedly in the future",
            )
        if nav.currency != fund.base_currency:
            raise MemberHoldingServiceError(
                503,
                "fund_nav_currency_mismatch",
                "Fund NAV currency does not match fund base currency",
            )
        stale_after = timedelta(hours=get_settings().fund_nav_stale_after_hours)
        nav_status = "stale" if current - nav_valuation_time > stale_after else "available"
        currency = nav.currency

    calculation = calculate_holding(
        share_quantity=share_quantity,
        cumulative_invested=cumulative_invested,
        unit_nav=unit_nav,
    )
    return MemberHoldingResponse(
        holdingId=holding.id,
        memberUserId=holding.member_user_id,
        fundId=fund.id,
        fundName=fund.name,
        fundCode=fund.fund_code,
        currency=currency,
        shareQuantity=canonical_decimal(share_quantity),
        latestUnitNav=canonical_decimal(unit_nav) if unit_nav is not None else None,
        marketValue=(
            canonical_decimal(calculation.market_value)
            if calculation.market_value is not None
            else None
        ),
        cumulativeInvested=canonical_decimal(cumulative_invested),
        cumulativeReturn=(
            canonical_decimal(calculation.cumulative_return)
            if calculation.cumulative_return is not None
            else None
        ),
        returnRate=(
            canonical_decimal(calculation.return_rate)
            if calculation.return_rate is not None
            else None
        ),
        navStatus=nav_status,
        navValuationTime=nav_valuation_time,
        confirmedAt=(
            _parse_aware(holding.confirmed_at, field="confirmedAt")
            if holding.confirmed_at is not None
            else None
        ),
        asOf=_parse_aware(holding.as_of, field="asOf"),
        source=cast(HoldingSource, holding.source),
        status=cast(HoldingStatus, holding.status),
        rowVersion=holding.row_version,
        updatedAt=_parse_aware(holding.updated_at, field="updatedAt"),
    )


def _list_response(
    db: sqlite3.Connection,
    member_user_id: str,
    *,
    current: datetime,
) -> MemberHoldingListResponse:
    records = list_member_holdings(db, member_user_id)
    return MemberHoldingListResponse(
        items=[_holding_response(db, record, current=current) for record in records]
    )


def _validate_business_times(
    request: UpsertMemberHoldingRequest,
    current: datetime,
) -> None:
    as_of = request.as_of.astimezone(UTC)
    if as_of > current + timedelta(minutes=5):
        raise MemberHoldingServiceError(422, "as_of_in_future", "数据时点不能位于未来")
    if request.confirmed_at is not None and request.confirmed_at.astimezone(UTC) > as_of:
        raise MemberHoldingServiceError(
            422,
            "confirmed_after_as_of",
            "份额确认时间不能晚于数据时点",
        )


def _map_error(exc: Exception) -> MemberHoldingServiceError:
    if isinstance(exc, MemberHoldingServiceError):
        return exc
    if isinstance(exc, UserAdminPolicyError):
        return MemberHoldingServiceError(exc.status_code, exc.code, exc.detail)
    if isinstance(exc, HoldingDecimalError):
        return MemberHoldingServiceError(422, "decimal_invalid", str(exc))
    if isinstance(exc, FundNotFoundError):
        return MemberHoldingServiceError(404, "fund_not_found", str(exc))
    if isinstance(exc, MemberHoldingVersionError):
        return MemberHoldingServiceError(409, "row_version_conflict", str(exc))
    if isinstance(exc, sqlite3.IntegrityError):
        return MemberHoldingServiceError(
            409,
            "holding_data_conflict",
            "Fund code, NAV time or holding identity conflicts with existing data",
        )
    if isinstance(exc, MemberHoldingRepositoryError):
        return MemberHoldingServiceError(503, "holding_repository_failure", str(exc))
    return MemberHoldingServiceError(500, "holding_operation_failed", "Holding operation failed")


def get_self_holdings(
    *,
    user_id: str,
    now: datetime | None = None,
) -> MemberHoldingListResponse:
    current = _now(now)
    with connection() as db:
        user = get_user_by_id(db, user_id)
        if user is None:
            raise MemberHoldingServiceError(404, "user_not_found", "User does not exist")
        if user.role_code != "member":
            return MemberHoldingListResponse(items=[])
        return _list_response(db, user_id, current=current)


def get_admin_holdings(
    *,
    member_user_id: str,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> MemberHoldingListResponse:
    current = _now(now)
    timestamp = current.isoformat()
    try:
        with connection() as db:
            _assert_member_target(db, member_user_id)
            response = _list_response(db, member_user_id, current=current)
            insert_audit_event(
                db,
                event_type="member.holdings_viewed_by_admin",
                subject_type="user",
                subject_id=member_user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={"holdingCount": len(response.items)},
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return response
    except Exception as exc:
        raise _map_error(exc) from exc


def get_fund_catalog() -> FundListResponse:
    with connection() as db:
        return FundListResponse(items=[_fund_response(fund) for fund in list_funds(db)])


def put_member_holding(
    *,
    member_user_id: str,
    fund_id: str,
    request: UpsertMemberHoldingRequest,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> MemberHoldingResponse:
    current = _now(now)
    timestamp = current.isoformat()
    try:
        _validate_business_times(request, current)
        share_quantity = parse_non_negative_decimal(
            request.share_quantity,
            field="shareQuantity",
        )
        cumulative_invested = parse_non_negative_decimal(
            request.cumulative_invested,
            field="cumulativeInvested",
        )
        with connection() as db:
            if not db.in_transaction:
                db.execute("BEGIN IMMEDIATE")
            _assert_member_target(db, member_user_id)
            if get_fund(db, fund_id) is None:
                raise FundNotFoundError("Fund does not exist")
            _require_recent(db, context, current)
            updated = upsert_member_holding(
                db,
                member_user_id=member_user_id,
                fund_id=fund_id,
                share_quantity=canonical_decimal(share_quantity),
                cumulative_invested=canonical_decimal(cumulative_invested),
                confirmed_at=(
                    request.confirmed_at.astimezone(UTC).isoformat()
                    if request.confirmed_at is not None
                    else None
                ),
                as_of=request.as_of.astimezone(UTC).isoformat(),
                source=request.source,
                status=request.status,
                expected_version=request.expected_version,
                updated_by=context.actor_user_id,
                now=timestamp,
            )
            insert_audit_event(
                db,
                event_type="member.holding_updated",
                subject_type="user",
                subject_id=member_user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={
                    "fundId": fund_id,
                    "source": request.source,
                    "status": request.status,
                    "changedFields": [
                        "share_quantity",
                        "cumulative_invested",
                        "confirmed_at",
                        "as_of",
                        "source",
                        "status",
                    ],
                },
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
            response = _holding_response(db, updated, current=current)
        return response
    except Exception as exc:
        raise _map_error(exc) from exc


def put_fund_nav(
    *,
    fund_id: str,
    request: UpsertFundNavRequest,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> FundNavMutationResponse:
    current = _now(now)
    timestamp = current.isoformat()
    try:
        valuation_time = request.valuation_time.astimezone(UTC)
        if valuation_time > current + timedelta(minutes=5):
            raise MemberHoldingServiceError(
                422,
                "valuation_time_in_future",
                "净值估值时间不能位于未来",
            )
        unit_nav = parse_non_negative_decimal(request.unit_nav, field="unitNav")
        with connection() as db:
            if not db.in_transaction:
                db.execute("BEGIN IMMEDIATE")
            fund = get_fund(db, fund_id)
            if fund is None:
                raise FundNotFoundError("Fund does not exist")
            if request.currency != fund.base_currency:
                raise MemberHoldingServiceError(
                    422,
                    "fund_nav_currency_mismatch",
                    "净值币种必须与基金基础币种一致",
                )
            _require_recent(db, context, current)
            if request.fund_code is not None and request.fund_code != fund.fund_code:
                fund = update_fund_code(
                    db,
                    fund_id=fund_id,
                    fund_code=request.fund_code,
                )
            nav = insert_fund_nav(
                db,
                fund_id=fund_id,
                valuation_time=valuation_time.isoformat(),
                unit_nav=canonical_decimal(unit_nav),
                currency=request.currency,
                source=request.source,
                now=timestamp,
            )
            insert_audit_event(
                db,
                event_type="fund.nav_updated",
                subject_type="fund",
                subject_id=fund_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={
                    "valuationTime": valuation_time.isoformat(),
                    "currency": request.currency,
                    "source": request.source,
                    "fundCodeChanged": request.fund_code is not None,
                    "changedFields": ["unit_nav", "valuation_time", "currency", "source"],
                },
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return FundNavMutationResponse(
            fund=_fund_response(fund),
            unitNav=nav.unit_nav,
            valuationTime=valuation_time,
            currency=nav.currency,
            source=cast(HoldingSource, nav.source),
        )
    except Exception as exc:
        raise _map_error(exc) from exc
