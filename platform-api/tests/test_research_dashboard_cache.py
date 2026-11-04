import asyncio
import importlib
from datetime import date
from decimal import Decimal

import pytest

from app.research_provider_errors import ResearchProviderError

pytestmark = pytest.mark.unit


def test_market_snapshot_cache_coalesces_and_invalidates(monkeypatch):
    from app import research_a_share_repository as repository
    from app.research_provider_market_detail import MarketDetailProvider

    state = {"revision": "first", "calls": 0, "value": "1.234500"}
    monkeypatch.setattr(
        repository,
        "read_dataset_metadata",
        lambda _: {
            "fetched_at": state["revision"],
            "observed_at": "2026-10-26",
            "status": "ready",
            "source": "test",
        },
    )

    def read(_):
        state["calls"] += 1
        return {
            "marketId": "us",
            "status": "ready",
            "rows": [
                {
                    "id": "spy",
                    "name": "SPY",
                    "symbol": "SPY",
                    "status": "ready",
                    "unit": "price",
                    "changeUnit": "percent",
                    "frequency": "daily",
                    "timezone": "UTC",
                    "source": "test",
                    "methodologyVersion": "test-v1",
                    "close": state["value"],
                }
            ],
        }

    monkeypatch.setattr(repository, "read_dataset", read)
    provider = MarketDetailProvider(timeout_seconds=1, user_agent="test")

    async def run():
        results = await asyncio.gather(*(provider.get("us") for _ in range(5)))
        assert state["calls"] == 1
        assert all(str(r.rows[0].close) == "1.234500" for r in results)
        assert results[0].status == "stale"  # missing retrieval timestamp remains stale
        state.update(revision="second", value="2.345600")
        result = await provider.get("us")
        assert state["calls"] == 2 and str(result.rows[0].close) == "2.345600"

    asyncio.run(run())


@pytest.mark.parametrize("domain", ["macro", "commodity", "crypto"])
def test_artifact_cache_coalesces_reads_invalidates_and_preserves_failure(domain, monkeypatch):
    module = importlib.import_module(f"app.research_provider_{domain}_dashboard")
    provider = getattr(module, f"{domain.title()}DashboardProvider")(
        timeout_seconds=1, user_agent="test"
    )
    state = {"revision": ("root/file", 1, 1, 1), "value": "1.234500", "calls": 0}

    def read(_):
        state["calls"] += 1
        if state["value"] is None:
            raise ResearchProviderError("local_data_unavailable")
        return {
            "schemaVersion": "1.0",
            "status": "ready",
            "asOf": date.today().isoformat(),
            "groups": {
                "g": [
                    {
                        "seriesId": "s",
                        "label": "s",
                        "status": "ready",
                        "unit": "percent",
                        "frequency": "daily",
                        "timezone": "UTC",
                        "source": "official",
                        "observationDate": date.today().isoformat(),
                        "methodologyVersion": "v1",
                        "observations": [
                            {"date": date.today().isoformat(), "value": state["value"]}
                        ],
                    }
                ]
            },
        }

    monkeypatch.setattr(module, "read_local_json", read)
    monkeypatch.setattr(module, "local_json_revision", lambda _: state["revision"])

    async def run():
        first, second = await asyncio.gather(provider.get(), provider.get())
        assert state["calls"] == 1
        assert first is second
        assert str(first.groups["g"][0].observations[0].value) == "1.234500"
        state.update(revision=("root/file", 2, 1, 2), value="2.3400")
        revised = await provider.get()
        assert state["calls"] == 2
        assert revised.groups["g"][0].observations[0].value == Decimal("2.3400")
        state.update(revision=None, value=None)
        failed = await provider.get()
        assert failed.status == "stale" and failed.groups["g"][0].is_stale
        assert failed.groups["g"][0].observations[0].value == Decimal("2.3400")
        assert revised.status == "ready"  # Failure flags do not corrupt the valid snapshot.

    asyncio.run(run())


def test_narrative_cache_tracks_inputs_and_calculation_day(monkeypatch):
    from app import research_macro_narratives as module

    calls = []
    monkeypatch.setattr(
        module, "build", lambda sources, day: calls.append((sources, day)) or sources
    )
    module._cached_build.cache_clear()
    try:
        module._cached_build('{"value":1}', date(2026, 10, 27))
        module._cached_build('{"value":1}', date(2026, 10, 27))
        assert len(calls) == 1
        module._cached_build('{"value":2}', date(2026, 10, 27))
        module._cached_build('{"value":2}', date(2026, 10, 28))
        assert len(calls) == 3
    finally:
        module._cached_build.cache_clear()


@pytest.mark.parametrize("domain", ["macro", "commodity", "crypto"])
def test_corrupt_revision_does_not_poison_cache_and_same_revision_can_recover(domain, monkeypatch):
    import copy

    module = importlib.import_module(f"app.research_provider_{domain}_dashboard")
    provider = getattr(module, f"{domain.title()}DashboardProvider")(
        timeout_seconds=1, user_agent="test"
    )
    today = date.today().isoformat()
    document = {
        "schemaVersion": "1.0", "status": "ready", "asOf": today,
        "groups": {"g": [{
            "seriesId": "s", "label": "s", "status": "ready", "unit": "USD",
            "frequency": "daily", "timezone": "UTC", "source": "official",
            "observationDate": today, "methodologyVersion": "v1",
            "observations": [{"date": today, "value": "123.4567890123456789"}],
        }]},
    }
    state = {"revision": 1, "valid": True, "reads": 0}

    def read(_):
        state["reads"] += 1
        result = copy.deepcopy(document)
        if not state["valid"]:
            result["groups"]["g"][0]["observations"][0]["value"] = "corrupt"
        return result

    monkeypatch.setattr(module, "local_json_revision", lambda _: ("file", state["revision"], 1, 1))
    monkeypatch.setattr(module, "read_local_json", read)

    async def run():
        good = await provider.get()
        baseline = good.model_dump()
        state.update(revision=2, valid=False)
        stale = await provider.get()
        assert stale.status == "stale"
        assert stale.groups["g"][0].is_stale
        assert stale.groups["g"][0].observations[0].value == Decimal("123.4567890123456789")
        assert good.model_dump() == baseline
        # The failed revision must not be marked successfully loaded.
        state["valid"] = True
        recovered = await provider.get()
        assert state["reads"] == 3
        assert recovered.status == "ready"
        assert not recovered.groups["g"][0].is_stale
        assert recovered.model_dump() == baseline
        assert await provider.get() is recovered
        assert state["reads"] == 3

    asyncio.run(run())


def test_unchanged_macro_artifact_is_reaged_on_cache_hit(monkeypatch):
    from datetime import UTC, datetime

    from app import research_provider_macro_dashboard as module

    class Clock(datetime):
        instant = datetime(2026, 11, 3, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.instant

    reads = []
    document = {
        "schemaVersion": "1.0", "status": "ready", "asOf": "2026-11-03",
        "groups": {"g": [{
            "seriesId": "s", "label": "s", "status": "ready", "unit": "USD",
            "frequency": "daily", "timezone": "UTC", "source": "official",
            "observationDate": "2026-11-03", "methodologyVersion": "v1",
            "retrievedAt": "2026-11-03T00:00:00Z",
            "observations": [{"date": "2026-11-03", "value": "1.234500"}],
        }]},
    }
    monkeypatch.setattr(module, "datetime", Clock)
    monkeypatch.setattr(module, "local_json_revision", lambda _: ("file", 1, 1, 1))
    monkeypatch.setattr(module, "read_local_json", lambda path: reads.append(path) or document)
    provider = module.MacroDashboardProvider(timeout_seconds=1, user_agent="test")

    async def run():
        assert (await provider.get()).status == "ready"
        Clock.instant = datetime(2026, 11, 11, tzinfo=UTC)
        result = await provider.get()
        assert len(reads) == 1
        assert result.status == "partial"
        series = result.groups["g"][0]
        assert series.status == "stale" and series.is_stale
        assert series.quality_flags == ["stale_latest_observation"]
        assert series.retrieved_at == datetime(2026, 11, 3, tzinfo=UTC)
        assert str(series.observations[0].value) == "1.234500"

    asyncio.run(run())


@pytest.mark.parametrize("selected", ["a", "a,b", "missing"])
def test_group_projection_keeps_original_values_and_provider_cache(selected):
    from app.research_provider_macro_dashboard import MacroDashboardResponse
    raw = {"schemaVersion": "1.0", "status": "partial", "asOf": "2026-11-02", "groups": {}}
    for key in ("a", "b"):
        raw["groups"][key] = [{"seriesId": key, "label": key, "status": "stale", "unit": "usd",
            "frequency": "daily", "timezone": "UTC", "source": "test", "methodologyVersion": "v1",
            "qualityFlags": ["source_gap"], "observations": [{"date": "2026-10-30", "value": "1.234500"},
                {"date": "2026-11-02", "value": None}]}]
    raw["optionDistribution"] = {"rows": [{"strike": 123}]}
    source = MacroDashboardResponse.model_validate(raw)
    projected = source.select_groups(selected)
    assert set(projected.groups) == set(selected.split(",")) & {"a", "b"}
    assert projected.option_distribution == {}
    assert projected.status == "partial"
    for group in projected.groups.values():
        assert str(group[0].observations[0].value) == "1.234500"
        assert group[0].observations[1].value is None
        assert group[0].quality_flags == ["source_gap"]
    assert set(source.groups) == {"a", "b"} and source.option_distribution["rows"]
    assert source.select_groups(None) is source
    assert source.select_groups("optionDistribution").option_distribution == source.option_distribution
