from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

SENSITIVE_IDENTITY_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/me",
    "/api/v1/users",
)


def is_sensitive_identity_path(path: str) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in SENSITIVE_IDENTITY_PREFIXES)


class UserNoStoreMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        if is_sensitive_identity_path(request.url.path):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response
