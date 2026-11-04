from datetime import date
from decimal import Decimal

import pytest

from app import research_cn_monitor
from app.research_provider_a_share import AShareResearchProvider
from app.research_provider_errors import ResearchProviderError

pytestmark = pytest.mark.unit


def test_major_index_uses_tencent_native_day_not_akshare(monkeypatch):
    provider = AShareResearchProvider(
        timeout_seconds=2,
        user_agent="test",
        akshare_loader=lambda: pytest.fail("Legacy index source must not run"),
    )

    def response(opener, url, params, headers):
        assert "newfqkline" in url and params["param"] == "sh000300,day,,,640,qfq"
        return {
            "code": 0,
            "data": {
                "sh000300": {
                    "day": [["2026-10-30", "1", "3985.50"], ["2026-11-02", "1", "4016.92"]]
                }
            },
        }

    monkeypatch.setattr(provider, "_direct_json", response)
    rows = provider._direct_index_history("000300", "sh000300")
    assert rows[-1]["date"] == date(2026, 11, 2)
    assert rows[-1]["close"] == Decimal("4016.92")
    assert rows[-1]["source"] == "tencent-index-daily"
    monkeypatch.setattr(provider, "_direct_json", lambda *a, **kw: {"code": 1, "data": {}})
    with pytest.raises(ResearchProviderError):
        provider._direct_index_history("000300", "sh000300")


def test_monitor_subset_cache_preserves_missing_and_revision(monkeypatch):
    revision = [1]
    monkeypatch.setattr("app.research_local_data.local_json_revision", lambda _: tuple(revision))
    reads = []

    def read(_):
        reads.append(1)
        return {
            "generatedAt": "now",
            "sources": {
                "dividend": {"data": [{"value": None}]},
                "industry": {"data": list(range(1000))},
            },
        }

    monkeypatch.setattr(research_cn_monitor, "read_artifact", read)
    research_cn_monitor._monitor_view.cache_clear()
    assert research_cn_monitor.read_monitor(["dividend"])["sources"] == {
        "dividend": {"data": [{"value": None}]}
    }
    research_cn_monitor.read_monitor(["industry"])
    assert len(reads) == 1
    revision[0] = 2
    research_cn_monitor.read_monitor(["dividend"])
    assert len(reads) == 2
    with pytest.raises(ValueError):
        research_cn_monitor.read_monitor(["arbitrary-file"])


def test_index_completion_requires_actual_latest_history_date():
    from app.research_a_share_refresh import _stale_index_codes
    from app.research_provider_a_share import INDEX_DEFINITIONS
    rows = [{"code": code, "history": [{"observedAt": "2026-11-02"}]} for code, _, _ in INDEX_DEFINITIONS[:8]]
    assert _stale_index_codes(rows, "2026-11-02") == []
    rows[0]["history"] = [{"observedAt": "2026-10-30"}]
    assert _stale_index_codes(rows, "2026-11-02") == [rows[0]["code"]]
    assert len(_stale_index_codes([], "2026-11-02")) == 8
