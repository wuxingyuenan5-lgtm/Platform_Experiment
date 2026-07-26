from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.config import Settings, get_settings
from app.database import connection
from app.user_permissions import ROLE_PERMISSIONS, are_known_roles, has_permission

PUBLIC_PATHS = {"/health"}
IDENTITY_FIELDS = {
    "actor",
    "reviewer",
    "requestedBy",
    "approvedBy",
    "revokedBy",
}


@dataclass(frozen=True)
class Principal:
    user_id: str
    roles: tuple[str, ...]
    auth_method: str
    session_id: str | None = None
    credential_id: str | None = None

    def has_permission(self, permission: str) -> bool:
        return has_permission(self.roles, permission)


class AuthenticationError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def load_api_credentials(settings: Settings) -> list[dict[str, object]]:
    try:
        payload = json.loads(settings.auth_credentials_json)
    except json.JSONDecodeError as exc:
        raise AuthenticationError(
            503, "Authentication credential configuration is invalid"
        ) from exc
    if not isinstance(payload, list):
        raise AuthenticationError(503, "Authentication credential configuration must be a list")
    credentials: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise AuthenticationError(503, "Authentication credential entry is invalid")
        required = {"credentialId", "userId", "tokenSha256", "roles", "status"}
        if not required.issubset(item):
            raise AuthenticationError(503, "Authentication credential entry is incomplete")
        roles = item["roles"]
        if not isinstance(roles, list) or not are_known_roles(str(role) for role in roles):
            raise AuthenticationError(503, "Authentication credential roles are invalid")
        token_digest = str(item["tokenSha256"]).lower()
        if len(token_digest) != 64 or any(
            character not in "0123456789abcdef" for character in token_digest
        ):
            raise AuthenticationError(503, "Authentication credential token hash is invalid")
        credentials.append(item)
    return credentials


def authenticate_bearer(request: Request, settings: Settings) -> Principal:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError(401, "Bearer authentication is required")
    supplied_hash = token_hash(token)
    for credential in load_api_credentials(settings):
        if not hmac.compare_digest(str(credential["tokenSha256"]).lower(), supplied_hash):
            continue
        if credential["status"] != "active":
            raise AuthenticationError(403, "Authentication credential is inactive")
        return Principal(
            user_id=str(credential["userId"]),
            roles=tuple(str(role) for role in credential["roles"]),
            auth_method="api_key",
            credential_id=str(credential["credentialId"]),
        )
    raise AuthenticationError(401, "Authentication credential is invalid")


def authenticate_request(request: Request, settings: Settings) -> Principal:
    mode = settings.auth_mode.lower()
    if settings.environment.lower() == "live" and mode != "api_key":
        raise AuthenticationError(503, "Live environment requires api_key authentication mode")
    if mode == "api_key":
        return authenticate_bearer(request, settings)
    if mode == "development" and settings.environment.lower() != "live":
        roles = tuple(settings.development_role_list)
        if not are_known_roles(roles):
            raise AuthenticationError(503, "Development identity roles are invalid")
        return Principal(
            user_id=settings.development_user_id,
            roles=roles,
            auth_method="development",
        )
    raise AuthenticationError(503, "Authentication mode is not configured safely")


def permission_for_request(method: str, path: str) -> str:
    normalized_method = method.upper()
    if normalized_method in {"GET", "HEAD"}:
        audit_read_suffixes = (
            "/security/credential-references",
            "/security/credential-rotations",
            "/ops/audit-events",
            "/ops/production-status",
            "/ops/alerts",
            "/ops/backups",
            "/ops/restore-drills",
            "/ops/controlled-operations",
        )
        if any(path.endswith(suffix) for suffix in audit_read_suffixes):
            return "audit:read"
        return "platform:read"

    if path.endswith("/live-trading/sessions") and normalized_method == "POST":
        return "live_session:request"
    if "/live-trading/sessions/" in path and path.endswith("/approve"):
        return "live_session:approve"
    if "/live-trading/sessions/" in path and path.endswith("/revoke"):
        return "live_session:revoke"

    if path.endswith("/trading/commands") or path.endswith("/trading/execution-batches"):
        return "trade:submit"
    if path.endswith("/trading/orders") and normalized_method == "POST":
        return "trade:submit"
    if path.endswith("/trading/cross-spread/market-command"):
        return "trade:submit"

    if "/risk/kill-switches/" in path or path.endswith("/execution-risk-policy"):
        return "risk:manage"
    if "/trading/execution-batches/" in path and path.endswith("/risk-actions"):
        return "risk:manage"

    if "/venue-reconciliation/differences/" in path and path.endswith("/resolve"):
        return "reconciliation:review"
    if "/eod-reconciliation/reports/" in path and path.endswith("/review"):
        return "eod:review"
    if "/ops/alerts/" in path and (path.endswith("/acknowledge") or path.endswith("/close")):
        return "reconciliation:review"

    production_write_suffixes = (
        "/ops/alerts/scan",
        "/ops/backups",
        "/ops/restore-drills",
        "/ops/controlled-operations",
    )
    if normalized_method == "POST" and any(
        path.endswith(suffix) for suffix in production_write_suffixes
    ):
        return "operations:run"

    operations_paths = (
        "/financial-facts",
        "/financials/rebuild",
        "/ops/live-economic-events/import",
        "/ops/venue-reconciliation/runs",
        "/ops/eod-reconciliation/reports",
    )
    if any(fragment in path for fragment in operations_paths):
        return "operations:run"
    if "/strategies/instances/" in path and path.endswith("/runs"):
        return "strategy:run"
    return "admin:write"


def audit_auth_event(
    *,
    event_type: str,
    request: Request,
    principal: Principal | None,
    permission: str | None,
    result: str,
    detail: str,
    request_id: str,
) -> None:
    try:
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
                    "http_request",
                    request_id,
                    json.dumps(
                        {
                            "method": request.method,
                            "path": request.url.path,
                            "userId": principal.user_id if principal else None,
                            "roles": list(principal.roles) if principal else [],
                            "credentialId": principal.credential_id if principal else None,
                            "permission": permission,
                            "result": result,
                            "detail": detail,
                            "sourceIp": request.client.host if request.client else None,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    now_iso(),
                ),
            )
    except Exception:
        # Authentication must not fail open because audit persistence is unavailable.
        return


async def validate_body_identity(request: Request, principal: Principal) -> None:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return
    body = await request.body()
    if not body:
        return
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    for field in IDENTITY_FIELDS:
        value = payload.get(field)
        if value is not None and str(value) != principal.user_id:
            raise AuthenticationError(
                403,
                f"Request identity field '{field}' must match the authenticated user",
            )


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method.upper() == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        request_id = request.headers.get("x-request-id") or str(uuid4())
        settings = get_settings()
        permission = permission_for_request(request.method, request.url.path)
        principal: Principal | None = None
        try:
            principal = authenticate_request(request, settings)
            if not principal.has_permission(permission):
                raise AuthenticationError(403, "Authenticated identity lacks required permission")
            if settings.environment.lower() == "live" or settings.auth_mode.lower() == "api_key":
                await validate_body_identity(request, principal)
        except AuthenticationError as exc:
            audit_auth_event(
                event_type="authentication_or_authorization_denied",
                request=request,
                principal=principal,
                permission=permission,
                result="denied",
                detail=exc.detail,
                request_id=request_id,
            )
            headers = {"X-Request-ID": request_id}
            if exc.status_code == 401:
                headers["WWW-Authenticate"] = "Bearer"
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail, "requestId": request_id},
                headers=headers,
            )

        request.state.principal = principal
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Authenticated-User"] = principal.user_id
        return response


def require_principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="Authenticated principal is unavailable")
    return principal


__all__ = [
    "AuthenticationError",
    "AuthenticationMiddleware",
    "Principal",
    "ROLE_PERMISSIONS",
    "authenticate_request",
    "permission_for_request",
    "require_principal",
    "token_hash",
]
