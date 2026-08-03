from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app import research_macro_history
from app.research_data_schemas import MacroExpectationEvent, MacroProbabilityPoint
from app.research_macro_history import MacroProbabilityHistoryStore, history_change

pytestmark = pytest.mark.unit


def _event(probability: str = "50") -> MacroExpectationEvent:
    return MacroExpectationEvent(
        event_id="fed-july",
        category="monetary_policy",
        title="Fed decision",
        outcome="Cut",
        current_probability_pct=Decimal(probability),
    )


def test_update_preserves_window_deduplication_and_change_semantics(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed_at = datetime(2026, 7, 31, 6, 0, tzinfo=UTC)
    monkeypatch.setattr(research_macro_history, "_now", lambda: observed_at)
    path = tmp_path / "macro.json"
    path.write_text(
        json.dumps(
            {
                "fed-july": [
                    {
                        "observedAt": (observed_at - timedelta(days=91)).isoformat(),
                        "probabilityPct": "10",
                    },
                    {
                        "observedAt": (observed_at - timedelta(days=8)).isoformat(),
                        "probabilityPct": "40",
                    },
                    {
                        "observedAt": (observed_at - timedelta(days=2)).isoformat(),
                        "probabilityPct": "45",
                    },
                    {
                        "observedAt": (observed_at - timedelta(days=1)).isoformat(),
                        "probabilityPct": "48",
                    },
                    {
                        "observedAt": observed_at.replace(second=30).isoformat(),
                        "probabilityPct": "49",
                    },
                    {"observedAt": "invalid", "probabilityPct": "99"},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = asyncio.run(MacroProbabilityHistoryStore(path).update([_event()]))

    event = result[0]
    assert [point.probability_pct for point in event.history] == [
        Decimal("40"),
        Decimal("45"),
        Decimal("48"),
        Decimal("50"),
    ]
    assert event.change_1d_pct_points == Decimal("2")
    assert event.change_7d_pct_points == Decimal("10")
    persisted = json.loads(path.read_text(encoding="utf-8"))["fed-july"]
    assert len(persisted) == 4
    assert persisted[-1] == {
        "observedAt": observed_at.isoformat(),
        "probabilityPct": "50",
    }
    assert not path.with_suffix(".tmp").exists()


def test_update_recovers_from_invalid_json_and_writes_atomic_payload(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed_at = datetime(2026, 7, 31, 6, 0, tzinfo=UTC)
    monkeypatch.setattr(research_macro_history, "_now", lambda: observed_at)
    path = tmp_path / "macro.json"
    path.write_text("not-json", encoding="utf-8")

    event = asyncio.run(MacroProbabilityHistoryStore(path).update([_event("35")]))[0]

    assert event.history == [
        MacroProbabilityPoint(
            observed_at=observed_at,
            probability_pct=Decimal("35"),
        )
    ]
    assert event.change_1d_pct_points is None
    assert event.change_7d_pct_points is None
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "fed-july": [
            {
                "observedAt": observed_at.isoformat(),
                "probabilityPct": "35",
            }
        ]
    }


def test_history_change_requires_a_point_at_or_before_target() -> None:
    observed_at = datetime(2026, 7, 31, 6, 0, tzinfo=UTC)
    points = [
        MacroProbabilityPoint(
            observed_at=observed_at - timedelta(hours=12),
            probability_pct=Decimal("40"),
        ),
        MacroProbabilityPoint(
            observed_at=observed_at,
            probability_pct=Decimal("50"),
        ),
    ]

    assert history_change(points, timedelta(days=1)) is None
    assert history_change(points, timedelta(hours=6)) == Decimal("10")
