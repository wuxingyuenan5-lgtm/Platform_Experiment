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
