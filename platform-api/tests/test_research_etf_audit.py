from datetime import UTC, datetime

from app.research_etf_audit import broad_etf_checks


def document():
    return {
        "updatedAt": "2026-11-06T02:00:00+00:00",
        "sourceDate": "2026-11-05",
        "catalogCodes": ["510300"],
        "historyDates": 100,
        "partialDates": 1,
        "missingInputs": 1,
        "members": [
            {
                "code": "510300",
                "name": "沪深300ETF",
                "expectedDate": "2026-11-05",
                "sourceDate": "2026-11-05",
                "turnoverReady": True,
                "flowReady": True,
                "missingDates": ["2025-01-02"],
            }
        ],
    }


def test_old_gap_does_not_mark_current_inputs_unavailable_and_repair_recovers():
    data = document()
    rows = broad_etf_checks(
        data, datetime(2026, 11, 6, 3, tzinfo=UTC), ["2026-11-05", "2026-11-06"]
    )
    assert rows[1]["status"] == "healthy"
    assert rows[-1]["status"] == "warning"
    assert rows[-1]["evidence"]["missingByFund"] == {"510300": ["2025-01-02"]}
    data["members"][0]["missingDates"] = []
    assert (
        broad_etf_checks(data, datetime(2026, 11, 6, 3, tzinfo=UTC), ["2026-11-05"])[-1]["status"]
        == "healthy"
    )


def test_independent_calendar_detects_stale_inputs_not_hidden_by_fresh_projection():
    data = document()
    data["updatedAt"] = "2026-11-06T09:00:00+00:00"
    rows = broad_etf_checks(
        data, datetime(2026, 11, 6, 9, tzinfo=UTC), ["2026-11-05", "2026-11-06"]
    )
    assert rows[1]["status"] == "warning"
    assert rows[1]["evidence"]["auditExpectedDate"] == "2026-11-06"
    # Missing calendar and malformed catalog cannot pass as healthy.
    assert (
        broad_etf_checks(data, datetime(2026, 11, 6, 9, tzinfo=UTC), [])[0]["status"] == "warning"
    )
    data["catalogCodes"].append("510300")
    assert (
        broad_etf_checks(data, datetime(2026, 11, 6, 9, tzinfo=UTC), ["2026-11-05"])[0]["status"]
        == "error"
    )


def test_current_zero_is_ready_but_missing_input_or_source_failure_stays_visible():
    data = document()
    member = data["members"][0]
    for field, value in [
        ("turnoverReady", False),
        ("flowReady", False),
        ("sourceError", "timeout"),
    ]:
        original = member.get(field)
        member[field] = value
        rows = broad_etf_checks(data, datetime(2026, 11, 6, 3, tzinfo=UTC), ["2026-11-05"])
        assert rows[1]["status"] == "warning"
        member[field] = original


def test_minute_audit_detects_internal_gap_even_when_latest_bar_and_timestamp_are_current():
    from app.research_etf_audit import minute_etf_check
    from app.research_etf_observation import LIVE_SYMBOLS

    doc = {
        "status": "ready",
        "observationDate": "2026-11-06",
        "observationTime": "2026-11-06 15:00:00",
        "retrievedAt": "2026-11-06T07:05:00+00:00",
        "minuteCoverage": {
            s: {"date": "2026-11-06", "through": "15:00", "missingTimes": []} for s in LIVE_SYMBOLS
        },
    }
    now = datetime(2026, 11, 6, 7, 30, tzinfo=UTC)
    assert minute_etf_check(doc, now, ["2026-11-06"])["status"] == "healthy"
    doc["minuteCoverage"]["sh512050"]["missingTimes"] = ["11:03"]
    check = minute_etf_check(doc, now, ["2026-11-06"])
    assert check["status"] == "warning" and check["evidence"]["missingByFund"] == {
        "sh512050": ["11:03"]
    }
    doc["minuteCoverage"]["sh512050"]["missingTimes"] = []
    assert minute_etf_check(doc, now, ["2026-11-06"])["status"] == "healthy"
    del doc["minuteCoverage"]["sh512050"]
    assert minute_etf_check(doc, now, ["2026-11-06"])["status"] == "warning"
