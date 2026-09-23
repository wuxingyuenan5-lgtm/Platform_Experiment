from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json

import pytest

from app import research_macro_expectations_refresh as refresh
from app.research_macro_expectations_refresh import _event_from_market

pytestmark = pytest.mark.unit


def _market(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "fed-cut-2026",
        "slug": "fed-cut-2026",
        "question": "Will the Fed cut rates by December 2026?",
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["0.62", "0.38"]',
        "liquidityNum": 25_000,
        "volume24hr": 1_500,
        "endDate": "2026-12-31T00:00:00Z",
        "events": [{"slug": "fed-december-2026-rate-decision"}],
    }
    row.update(overrides)
    return row


def test_event_parser_keeps_curated_binary_macro_market() -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)

    event = _event_from_market(_market(), now)

    assert event is not None
    assert event["category"] == "monetary_policy"
    assert event["probability"] == 62.0
    assert event["label"] == "美联储将在2026年12月前降息吗？"
    assert event["originalLabel"] == "Will the Fed cut rates by December 2026?"
    assert event["sourceUrl"] == "https://polymarket.com/event/fed-december-2026-rate-decision"


def test_event_parser_falls_back_to_market_url_without_parent_event() -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    event = _event_from_market(_market(events=[]), now)

    assert event is not None
    assert event["sourceUrl"] == "https://polymarket.com/market/fed-cut-2026"


def test_category_does_not_match_fed_inside_unrelated_words() -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    row = _market(question="Will the Federation win the next parliamentary election?")

    event = _event_from_market(row, now)

    assert event is not None
    assert event["category"] == "election"


def test_election_topic_wins_over_country_keyword() -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    row = _market(
        question="Will United Russia (ER) gain the most seats in the next Russian parliamentary election?"
    )

    event = _event_from_market(row, now)

    assert event is not None
    assert event["category"] == "election"
    assert event["label"].startswith("统一俄罗斯党（ER）")


@pytest.mark.parametrize(
    "overrides",
    [
        {"outcomes": '["A", "B"]'},
        {"liquidityNum": 9999},
        {"volume24hr": 0},
        {"question": "Will Bitcoin reach a new high?"},
        {"endDate": (datetime(2025, 1, 1, tzinfo=UTC)).isoformat()},
        {"endDate": (datetime(2028, 1, 1, tzinfo=UTC)).isoformat()},
    ],
)
def test_event_parser_omits_ambiguous_or_low_quality_market(overrides: dict[str, object]) -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)

    assert _event_from_market(_market(**overrides), now) is None


def test_event_parser_accepts_one_year_expiry_boundary() -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    row = _market(endDate=(now + timedelta(days=365)).isoformat())

    assert _event_from_market(row, now) is not None


def test_refresh_marks_last_valid_feed_stale_on_upstream_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    target = tmp_path / "public" / "v1" / "macro" / "expectations.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "status": "ready",
                "source": "test",
                "updatedAt": "2026-09-01T00:00:00Z",
                "events": [{"id": "event-1"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(refresh, "hedge_board_data_root", lambda: tmp_path)
    monkeypatch.setattr(
        refresh,
        "write_local_json",
        lambda _path, payload: target.write_text(json.dumps(payload), encoding="utf-8"),
    )
    monkeypatch.setattr(
        refresh,
        "fetch_macro_expectations",
        lambda: (_ for _ in ()).throw(refresh.ResearchProviderError("upstream")),
    )

    assert refresh.refresh_macro_expectations(force=True) == "stale"
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "stale"
