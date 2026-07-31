from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from app.research_data_schemas import MacroExpectationEvent, MacroProbabilityPoint


def _now() -> datetime:
    return datetime.now(UTC)


def history_change(
    points: list[MacroProbabilityPoint],
    distance: timedelta,
) -> Decimal | None:
    if len(points) < 2:
        return None
    target = points[-1].observed_at - distance
    candidates = [point for point in points[:-1] if point.observed_at <= target]
    if not candidates:
        return None
    return points[-1].probability_pct - candidates[-1].probability_pct


class MacroProbabilityHistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        configured = os.environ.get("RESEARCH_MACRO_HISTORY_PATH")
        self._path = path or Path(
            configured or "data/research/macro_probability_history.json"
        )
        self._lock = asyncio.Lock()

    async def update(
        self,
        events: list[MacroExpectationEvent],
    ) -> list[MacroExpectationEvent]:
        async with self._lock:
            history = await asyncio.to_thread(self._read)
            observed_at = _now()
            cutoff = observed_at - timedelta(days=90)
            for event in events:
                points = history.setdefault(event.event_id, [])
                points.append(
                    {
                        "observedAt": observed_at.isoformat(),
                        "probabilityPct": str(event.current_probability_pct),
                    }
                )
                deduplicated: dict[str, dict[str, str]] = {}
                for point in points:
                    point_time = str(point.get("observedAt") or "")
                    try:
                        parsed = datetime.fromisoformat(point_time.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if parsed >= cutoff:
                        key = parsed.replace(second=0, microsecond=0).isoformat()
                        deduplicated[key] = point
                history[event.event_id] = list(deduplicated.values())
                normalized_points = [
                    MacroProbabilityPoint(
                        observed_at=datetime.fromisoformat(
                            str(point["observedAt"]).replace("Z", "+00:00")
                        ),
                        probability_pct=Decimal(str(point["probabilityPct"])),
                    )
                    for point in history[event.event_id]
                ]
                normalized_points.sort(key=lambda item: item.observed_at)
                event.history = normalized_points
                event.change_1d_pct_points = history_change(
                    normalized_points,
                    timedelta(days=1),
                )
                event.change_7d_pct_points = history_change(
                    normalized_points,
                    timedelta(days=7),
                )
            await asyncio.to_thread(self._write, history)
            return events

    def _read(self) -> dict[str, list[dict[str, str]]]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write(self, value: dict[str, list[dict[str, str]]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._path)
