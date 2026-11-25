from decimal import Decimal

import httpx
import pytest

from app import research_etf_observation as etf


def primary():
    # Provider combines an omitted interval into the next bar.
    return [
        {"day": "2026-11-06 09:31:00", "close": "1.1", "amount": "3"},
        {"day": "2026-11-06 09:33:00", "close": "1.1", "amount": "10"},
    ]


def supplement(code="512050", market=1, day="2026-11-06"):
    return {
        "data": {
            "code": code,
            "market": market,
            "trends": [
                f"{day} {slot},0,1.1,0,0,0,{amount},0"
                for slot, amount in [("09:30", "1"), ("09:31", "2"), ("09:32", "4"), ("09:33", "6")]
            ],
        }
    }


def test_recovery_selects_a_complete_original_series_without_double_counting(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))

    def transport(request):
        return httpx.Response(
            200, json=primary() if request.url.host == "quotes.sina.cn" else supplement()
        )

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        symbol, rows, checked = etf.collect_minutes(client, "sh512050", "2026-11-06T01:34:00+00:00")
    assert symbol == "sh512050" and checked["recovered"]
    assert checked["primaryMissingTimes"] == ["09:32"] and checked["missingTimes"] == []
    assert rows[0]["amount"] == "3" and rows[-1]["amount"] == "6"
    assert sum((Decimal(r["amount"]) for r in rows), Decimal(0)) == 13
    assert len(list((tmp_path / "raw/research/etf-observation/sh512050").glob("*.json"))) == 2


@pytest.mark.parametrize(
    "fault", ["identity", "market", "date", "incomplete", "duplicate", "timeout"]
)
def test_failed_recovery_retains_known_bars_and_auditable_gaps(tmp_path, monkeypatch, fault):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))

    def transport(request):
        if request.url.host == "quotes.sina.cn":
            return httpx.Response(200, json=primary())
        if fault == "timeout":
            raise httpx.ReadTimeout("fixture timeout", request=request)
        body = supplement()
        if fault == "identity":
            body["data"]["code"] = "510300"
        if fault == "market":
            body["data"]["market"] = 0
        if fault == "date":
            body = supplement(day="2026-11-05")
        if fault == "incomplete":
            body["data"]["trends"].pop(2)
        if fault == "duplicate":
            body["data"]["trends"].append(body["data"]["trends"][-1])
        return httpx.Response(200, json=body)

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        _, rows, checked = etf.collect_minutes(client, "sh512050", "2026-11-06T01:34:00+00:00")
    assert rows == primary() and checked["recovered"] is False
    assert checked["missingTimes"] == ["09:32"] and checked.get("recoveryError")


def test_complete_primary_is_reused_without_extra_requests(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    calls = []

    def transport(request):
        calls.append(str(request.url))
        return httpx.Response(200, json=primary()[:1])

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        _, rows, checked = etf.collect_minutes(client, "sh512050", "2026-11-06T01:32:00+00:00")
    assert len(calls) == 1 and rows == primary()[:1] and checked["missingTimes"] == []


def test_opening_gap_is_detected_and_auction_absence_is_not_invented_zero():
    from app.research_etf_cumulative import MINUTES

    rows = [{"day": f"2026-11-06 {t}:00"} for t in MINUTES if t not in {"09:31", "14:58", "14:59"}]
    assert etf.minute_coverage(rows)["missingTimes"] == ["09:31"]
