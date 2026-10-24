from copy import deepcopy
from datetime import date

import pytest

from app import research_provider_overseas as provider
from app.research_fedwatch import aggregated_probabilities
from app.research_provider_errors import ResearchProviderError

# Original contract prices in the user's CME screenshot; no fitted probabilities.
PRICES = dict(
    zip(
        [
            "OCT 26",
            "NOV 26",
            "DEC 26",
            "JAN 27",
            "FEB 27",
            "MAR 27",
            "APR 27",
            "MAY 27",
            "JUN 27",
            "JUL 27",
            "AUG 27",
            "SEP 27",
            "OCT 27",
        ],
        [
            96.115,
            96.08,
            95.92,
            95.85,
            95.765,
            95.69,
            95.595,
            95.515,
            95.455,
            95.425,
            95.405,
            95.39,
            95.38,
        ],
        strict=True,
    )
)
MEETINGS = [day for day in provider._FOMC_MEETINGS if day >= date(2026, 10, 18)]
EXPECTED = [
    {"375-400": 84.50, "400-425": 15.50},
    {"400-425": 97.54, "425-450": 2.46},
    {"400-425": 58.50, "425-450": 41.50},
    {"425-450": 92.79, "450-475": 7.21},
    {"425-450": 58.50, "450-475": 41.50},
    {"425-450": 23.36, "450-475": 76.64},
    {"425-450": 14.50, "450-475": 85.50},
]


def test_reproduces_cme_aggregated_screenshot_with_identical_quotes():
    result = aggregated_probabilities(PRICES, MEETINGS, 3.88)
    assert [row["probabilities"] for row in result] == EXPECTED
    assert result[-1]["date"] == "2027-07-28"  # No November quote: no invented Sep/Oct anchors.
    assert all(sum(row["probabilities"].values()) == 100 for row in result)


def test_anchor_cannot_propagate_forward_through_multiple_meetings():
    changed = deepcopy(PRICES)
    changed["OCT 26"] = 96.116
    a = aggregated_probabilities(PRICES, MEETINGS, 3.88)
    b = aggregated_probabilities(changed, MEETINGS, 3.88)
    assert len(a) == len(b)
    # Changing the reference affects every future meeting; it does not recursively drift.
    assert b[1]["probabilities"] == {"400-425": 97.09, "425-450": 2.91}
    assert b[3]["probabilities"] == {"425-450": 92.34, "450-475": 7.66}


def test_cuts_month_end_and_missing_initial_anchor():
    meetings = [date(2026, 10, 31), date(2026, 12, 9)]
    result = aggregated_probabilities({"OCT 26": 96.12, "NOV 26": 96.37}, meetings, 3.88)
    assert result[0]["probabilities"] == {"350-375": 100.0}
    with pytest.raises(ResearchProviderError, match="anchor_missing"):
        aggregated_probabilities({"OCT 26": 96.115}, MEETINGS, 3.88)
    invalid = deepcopy(PRICES)
    invalid["NOV 26"] = float("nan")
    with pytest.raises(ResearchProviderError, match="invalid_futures"):
        aggregated_probabilities(invalid, MEETINGS, 3.88)


def test_fetch_publishes_method_and_input_snapshot_with_missing_tail(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(provider, "_fedwatch_today", lambda: date(2026, 10, 18))
    monkeypatch.setattr(
        provider,
        "_fetch_fed_fund_settlements",
        lambda: (PRICES, "test curve", {"quoteAsOf": "2026-10-16T20:00:00+00:00"}),
    )
    monkeypatch.setattr(provider, "_fetch_fred_series", lambda _: 3.88)
    result = provider.fetch_fedwatch()
    assert result["methodology"] == "cme_aggregated_v1" and result["probabilityUnit"] == "percent"
    assert result["missingMeetings"] == ["2027-09-15", "2027-10-27"]
    assert result["meetings"][1]["probabilities"] == EXPECTED[1]
    assert list((tmp_path / "history/research/fedwatch").glob("*.json"))


def test_yahoo_source_retains_native_quote_time_and_extra_anchor_month(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "spark": {
                    "result": [
                        {
                            "symbol": "ZQV26.CBT",
                            "response": [
                                {
                                    "meta": {
                                        "regularMarketPrice": 96.115,
                                        "regularMarketTime": 1792180800,
                                    }
                                }
                            ],
                        }
                    ]
                }
            }

    def get(*args, **kwargs):
        calls.append(kwargs)
        return Response()

    monkeypatch.setattr(provider, "_get", get)
    monkeypatch.setattr(provider, "_fedwatch_today", lambda: date(2026, 10, 18))
    prices, meta = provider._fetch_yahoo_zq_settlements()
    assert len(calls[0]["params"]["symbols"].split(",")) == 14
    assert prices == {"OCT 26": 96.115}
    assert meta["quoteAsOf"] == meta["contractQuoteTimes"]["OCT 26"]

def test_display_rounded_futures_input_explains_small_cme_difference():
    # Controlled sensitivity example; the hidden raw CME quote is not available.
    prices=dict(zip(PRICES,[96.1163,96.0925,95.9425,95.8725,95.7825,95.7075,95.6125,95.5325,95.4675,95.4375,95.4125,95.3975,95.3850],strict=True))
    rounded=aggregated_probabilities(prices,MEETINGS,3.88)
    prices['OCT 26']=96.11625
    precise=aggregated_probabilities(prices,MEETINGS,3.88)
    assert rounded[0]['probabilities']['375-400']==89.46
    assert precise[0]['probabilities']['375-400']==89.48
    assert precise[1]['probabilities']['375-400']==6.82
