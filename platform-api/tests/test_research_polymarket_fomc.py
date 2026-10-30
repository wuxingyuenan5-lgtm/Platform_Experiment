import json
from datetime import UTC, datetime
from types import SimpleNamespace

from app import research_polymarket_fomc as fomc


def event(identifier="oct", end="2026-10-29T03:59:00Z", closed=False):
    return {
        "id": identifier,
        "slug": identifier,
        "startDate": "2026-10-01T00:00:00Z",
        "endDate": end,
        "closed": closed,
        "markets": [
            {
                "id": identifier + "hold",
                "groupItemTitle": "No change",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '["0.9","0.1"]',
                "clobTokenIds": '["hold","no"]',
            },
            {
                "id": identifier + "cut",
                "groupItemTitle": "25 bps decrease",
                "outcomes": ["No", "Yes"],
                "outcomePrices": ["0.999", "0.001"],
                "clobTokenIds": ["no", "cut"],
            },
        ],
    }


def test_meeting_ny_date_and_complete_low_probability_legs():
    result = fomc.meeting_from_event(event(), datetime.now(UTC))
    assert result["meetingDate"] == "2026-10-28"
    assert result["outcomes"][1]["tokenId"] == "cut"
    assert result["outcomes"][1]["probability"] == 0.1


def test_history_deduplicates_updates_without_flat_synthetic_points():
    assert fomc.merge_history([], []) == []
    assert fomc.merge_history(
        [{"observedAt": "a", "probability": 1}], [{"observedAt": "a", "probability": 2}]
    ) == [{"observedAt": "a", "probability": 2}]


def test_rollover_archives_prior_meeting_and_resolves_it(monkeypatch, tmp_path):
    monkeypatch.setattr(fomc, "hedge_board_data_root", lambda: tmp_path)

    def write(path, payload):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload))

    monkeypatch.setattr(fomc, "write_local_json", write)
    old = fomc.meeting_from_event(event(), datetime.now(UTC))
    write(fomc.ARTIFACT, {"meetings": [old]})
    calls = []

    def request(client, url, params):
        calls.append((url, params))
        if url == fomc.GAMMA:
            return (
                [event(closed=True)] if params.get("id") else [event("dec", "2026-12-10T04:59:00Z")]
            )
        return {"history": []}

    monkeypatch.setattr(fomc, "_request", request)
    assert fomc.refresh_fomc(force=True) == "ready"
    doc = json.loads((tmp_path / fomc.ARTIFACT).read_text())
    assert len(doc["meetings"]) == 2 and doc["meetings"][0]["closed"]
    assert doc["meetings"][1]["meetingDate"] == "2026-12-09"
    assert all(p["endTs"] - p["startTs"] <= 14 * 86400 for u, p in calls if u == fomc.HISTORY)
    first_count = len([1 for u, p in calls if u == fomc.HISTORY])
    calls.clear()
    fomc.refresh_fomc(force=True)
    assert len([1 for u, p in calls if u == fomc.HISTORY]) < first_count


def test_discovery_failure_retains_archive_and_marks_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(fomc, "hedge_board_data_root", lambda: tmp_path)
    old = {"meetings": [fomc.meeting_from_event(event(), datetime.now(UTC))]}
    target = tmp_path / fomc.ARTIFACT
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(old))
    monkeypatch.setattr(
        fomc, "write_local_json", lambda path, payload: target.write_text(json.dumps(payload))
    )
    monkeypatch.setattr(
        fomc, "_request", lambda *args: (_ for _ in ()).throw(ValueError("offline"))
    )
    assert fomc.refresh_fomc(force=True) == "stale"
    assert json.loads(target.read_text())["meetings"] == old["meetings"]


def test_fomc_remains_available_when_generic_feed_is_missing(monkeypatch):
    import asyncio

    from app import research_provider_macro as provider
    from app.research_provider_errors import ResearchProviderError

    now = datetime.now(UTC)
    meeting = fomc.meeting_from_event(event(), now)

    def read(path):
        if path.endswith("fomc-meetings.json"):
            return {"status": "ready", "meetings": [meeting]}
        raise ResearchProviderError("local_data_not_found:" + path)

    monkeypatch.setattr(provider, "read_local_json", read)
    result = asyncio.run(
        provider.MacroResearchProvider(
            timeout_seconds=1, user_agent="test"
        ).macro_expectation_contract()
    )
    assert result.status == "not_configured"
    assert result.fomc_status == "ready"
    assert result.fomc_meetings[0].meeting_date == "2026-10-28"


def test_capture_names_remain_unique_when_source_responses_share_timestamp(monkeypatch):
    class Fixed(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 29, 1, tzinfo=UTC)

    paths = []
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"history": []},
        url="https://example.test/history",
    )
    client = SimpleNamespace(get=lambda *args, **kwargs: response)
    monkeypatch.setattr(fomc, "datetime", Fixed)
    monkeypatch.setattr(fomc, "write_local_json", lambda path, payload: paths.append(path))
    fomc._request(client, "https://example.test/history", {})
    fomc._request(client, "https://example.test/history", {})
    assert len(set(paths)) == 2
