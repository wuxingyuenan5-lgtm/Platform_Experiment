from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth import Principal, require_permission
from app.config import get_settings
from app.member_holding_schemas import (
    FundListResponse,
    FundNavMutationResponse,
    MemberHoldingListResponse,
    MemberHoldingResponse,
    UpsertFundNavRequest,
    UpsertMemberHoldingRequest,
)
from app.member_holding_service import (
    MemberHoldingServiceError,
    get_admin_holdings,
    get_fund_catalog,
    get_self_holdings,
    put_fund_nav,
    put_member_holding,
)
from app.user_admin_service import AdminRequestContext

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["member-holdings"])


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if not isinstance(value, str) or not value:
        raise HTTPException(status_code=503, detail="Request identity is unavailable")
    return value


def _context(request: Request, principal: Principal) -> AdminRequestContext:
    if principal.auth_method != "session" or principal.session_id is None or len(principal.roles) != 1:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "human_session_required",
                "message": "Human browser session authentication is required",
            },
        )
    return AdminRequestContext(
        actor_user_id=principal.user_id,
        actor_role=principal.roles[0],
        session_id=principal.session_id,
        request_id=_request_id(request),
        ip_address=request.client.host if request.client else None,
    )


def _raise_service_error(exc: MemberHoldingServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/me/holdings", response_model=MemberHoldingListResponse)
def self_holdings(
    response: Response,
    principal: Annotated[
        Principal,
        Depends(require_permission("member.holding.read_self")),
    ],
) -> MemberHoldingListResponse:
    try:
        result = get_self_holdings(user_id=principal.user_id)
    except MemberHoldingServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.get("/users/{user_id}/holdings", response_model=MemberHoldingListResponse)
def admin_holdings(
    user_id: str,
    request: Request,
    response: Response,
    principal: Annotated[
        Principal,
        Depends(require_permission("member.holding.read_all")),
    ],
) -> MemberHoldingListResponse:
    try:
        result = get_admin_holdings(
            member_user_id=user_id,
            context=_context(request, principal),
        )
    except MemberHoldingServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.put(
    "/users/{user_id}/holdings/{fund_id}",
    response_model=MemberHoldingResponse,
)
def update_holding(
    user_id: str,
    fund_id: str,
    request_body: UpsertMemberHoldingRequest,
    request: Request,
    response: Response,
    principal: Annotated[
        Principal,
        Depends(require_permission("member.holding.update")),
    ],
) -> MemberHoldingResponse:
    try:
        result = put_member_holding(
            member_user_id=user_id,
            fund_id=fund_id,
            request=request_body,
            context=_context(request, principal),
        )
    except MemberHoldingServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.get("/funds", response_model=FundListResponse)
def fund_catalog(
    response: Response,
    _: Annotated[
        Principal,
        Depends(require_permission("member.holding.read_all")),
    ],
) -> FundListResponse:
    result = get_fund_catalog()
    _no_store(response)
    return result


@router.put("/funds/{fund_id}/nav", response_model=FundNavMutationResponse)
def update_fund_nav(
    fund_id: str,
    request_body: UpsertFundNavRequest,
    request: Request,
    response: Response,
    principal: Annotated[
        Principal,
        Depends(require_permission("member.holding.update")),
    ],
) -> FundNavMutationResponse:
    try:
        result = put_fund_nav(
            fund_id=fund_id,
            request=request_body,
            context=_context(request, principal),
        )
    except MemberHoldingServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result
