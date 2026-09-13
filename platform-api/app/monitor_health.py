"""Process-local evidence for background monitors; no trading side effects."""

from datetime import UTC, datetime
from threading import Lock
from time import monotonic

_boot = monotonic()
_lock = Lock()
_states: dict[str, dict] = {}


def begin(name: str) -> None:
    with _lock:
        row = _states.setdefault(name, {})
        row.update(startedAt=datetime.now(UTC).isoformat(), started=monotonic(), running=True)


def finish(name: str, error: str | None = None) -> None:
    with _lock:
        row = _states.setdefault(name, {})
        row.update(
            completedAt=datetime.now(UTC).isoformat(),
            completed=monotonic(),
            running=False,
            error=error,
        )
        if error is None:
            row["lastSuccessAt"] = row["completedAt"]


def snapshot(name: str, *, enabled: bool, deadline: float) -> dict:
    with _lock:
        row = dict(_states.get(name, {}))
    reference = row.get("started") if row.get("running") else row.get("completed")
    age = max(0, monotonic() - (_boot if reference is None else reference))
    status = (
        "disabled"
        if not enabled
        else "stalled"
        if age > deadline
        else "starting"
        if reference is None
        else "degraded"
        if row.get("error")
        else "healthy"
    )
    return {k: v for k, v in row.items() if k not in {"started", "completed"}} | {
        "status": status,
        "ageSeconds": age,
        "deadlineSeconds": deadline,
    }


def watchdog_snapshot() -> dict:
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / ".codex/dev-platform/watchdog.json"
    try:
        row = json.loads(path.read_text(encoding="utf-8-sig"))
        age = (datetime.now(UTC) - datetime.fromisoformat(row["observedAt"])).total_seconds()
        return {
            "status": "stalled" if age > 180 else row["status"],
            "observedAt": row["observedAt"],
            "reason": row.get("reason", ""),
            "recoveries": row.get("recoveries", 0),
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "unavailable", "reason": "Local watchdog has not reported"}
