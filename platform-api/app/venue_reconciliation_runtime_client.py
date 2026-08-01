from __future__ import annotations

import httpx

from app.config import get_settings


class RuntimeQueryError(RuntimeError):
    """Raised when the Platform Execution Runtime cannot be reached for a reconciliation query."""


def get(path: str, params: dict[str, str] | None = None) -> httpx.Response:
    """Issue one configured GET request to the Platform Execution Runtime."""

    settings = get_settings()
    try:
        return httpx.get(
            f"{settings.runtime_base_url}{path}",
            params=params,
            timeout=settings.runtime_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise RuntimeQueryError("Platform Execution Runtime query failed") from exc
