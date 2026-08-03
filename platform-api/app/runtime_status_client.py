from __future__ import annotations

import httpx


def read_runtime_status(base_url: str, timeout_seconds: float) -> str:
    try:
        response = httpx.get(f"{base_url}/status", timeout=timeout_seconds)
        response.raise_for_status()
    except httpx.HTTPError:
        return "not_connected"

    payload = response.json()
    status = payload.get("status") if isinstance(payload, dict) else None
    return status if isinstance(status, str) else "unknown"
