from __future__ import annotations

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.runtime_contracts import RuntimeExecutionEventV1


class RuntimeRecoveryUnavailableError(RuntimeError):
    pass


class RuntimeRecoveryContractError(RuntimeError):
    pass


def _validated_events(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        raise RuntimeRecoveryContractError("Runtime recovery payload must be an event list")
    try:
        events = [RuntimeExecutionEventV1.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise RuntimeRecoveryContractError(
            "Runtime recovery event contract is incompatible"
        ) from exc
    return [event.model_dump(mode="json") for event in events]


def recover_and_read_runtime_events(command_id: str) -> list[dict[str, object]]:
    """Ask Runtime to reconcile venue facts, then read its persisted journal events."""

    settings = get_settings()
    base_url = settings.runtime_base_url.rstrip("/")
    try:
        recovery = httpx.post(
            f"{base_url}/commands/{command_id}/recover",
            timeout=settings.runtime_timeout_seconds,
        )
        if recovery.status_code in {404, 409}:
            return []
        recovery.raise_for_status()

        response = httpx.get(
            f"{base_url}/commands/{command_id}/events",
            timeout=settings.runtime_timeout_seconds,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeRecoveryUnavailableError("Runtime recovery is unavailable") from exc
    return _validated_events(response.json())
