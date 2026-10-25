from app import research_treasury_weekly as provider
from app.research_provider_errors import ResearchProviderError


def test_reads_fixed_history_and_ignores_manifest_path(monkeypatch):
    requested = []

    def read(path):
        requested.append(path)
        if path.endswith("snapshot.json"):
            return dict(
                status="ready",
                observedAt="2026-10-25T00:00:00Z",
                sourceUrl=provider.SOURCE_URL,
                dataPath="../../private.json",
            )
        return dict(
            rows=[
                dict(
                    weekDate="2026-10-19",
                    observedAt="2026-10-25T00:00:00Z",
                    netFlowDisplay="$359.64M",
                    netBtcDisplay="4,396",
                    btcPriceDisplay="$81,942.45",
                    companies=[],
                )
            ]
        )

    monkeypatch.setattr(provider, "read_local_json", read)
    result = provider.get_snapshot()
    assert result["dataStatus"] == "ready" and len(result["weeks"]) == 1
    assert requested[-1] == "public/v1/crypto/treasury-weekly-history.json"


def test_bad_structured_history_preserves_image_status(monkeypatch):
    def read(path):
        if path.endswith("snapshot.json"):
            return dict(status="ready", dataPath="history.json")
        return dict(rows={"bad": "shape"})

    monkeypatch.setattr(provider, "read_local_json", read)
    result = provider.get_snapshot()
    assert (
        result["status"] == "ready"
        and result["dataStatus"] == "unavailable"
        and result["weeks"] == []
    )


def test_no_snapshot_is_explicit_no_data(monkeypatch):
    def absent(path):
        raise ResearchProviderError("missing")

    monkeypatch.setattr(provider, "read_local_json", absent)
    assert provider.get_snapshot()["status"] == "no_data"


def test_chart_history_does_not_require_an_image_manifest(monkeypatch):
    row = dict(
        weekDate="2026-05-04", observedAt="2026-10-25T00:00:00Z",
        netFlowUsd="-1000000", netFlowDisplay="-$1M", netBtc=None,
        netBtcDisplay="null", btcPriceUsd="80000", btcPriceDisplay="$80,000",
        companies=[dict(name="Company", value="-1000000", display="-$1M")],
    )
    def read(path):
        assert path == "public/v1/crypto/treasury-weekly-history.json"
        return {"rows": [row]}
    monkeypatch.setattr(provider, "read_local_json", read)
    result = provider.get_history()
    assert result["status"] == "ready"
    assert result["weeks"][0]["netBtc"] is None
    assert result["weeks"][0]["companies"][0]["value"] == "-1000000"


def test_chart_history_failure_is_not_zero_data(monkeypatch):
    monkeypatch.setattr(provider, "read_local_json", lambda path: {"rows": [{}]})
    assert provider.get_history()["status"] == "unavailable"
    assert provider.get_history()["weeks"] == []
