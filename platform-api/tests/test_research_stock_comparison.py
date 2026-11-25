import json
import sqlite3

from app.research_stock_comparison import add_industry_comparisons


def test_only_same_window_complete_unambiguous_industry_is_compared():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE data_audit_calendar(market,days_json,fetched_at,source);
        CREATE TABLE research_a_share_dataset_snapshots(dataset,payload_json);
        CREATE TABLE research_a_share_price_history(
            instrument_code,trade_date,close,quality_status);
        CREATE TABLE research_a_share_history(dataset,entity_code,observed_at,payload_json);
    """)
    days = ["2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03", "2026-11-04"]
    db.execute("INSERT INTO data_audit_calendar VALUES('CN',?,'','test')", (json.dumps(days),))
    member = {
        "securityCode": "000001",
        "swL2Code": "800001",
        "swL2Name": "行业",
        "effectiveFrom": days[0],
        "effectiveTo": None,
    }
    db.execute(
        "INSERT INTO research_a_share_dataset_snapshots VALUES('memberships',?)",
        (json.dumps([member]),),
    )
    for i, day in enumerate(days):
        db.execute(
            "INSERT INTO research_a_share_price_history VALUES('800001.SWI',?,?,'ready')",
            (day, str(100 + i)),
        )
        db.execute(
            "INSERT INTO research_a_share_history VALUES('stock','000001',?,?)",
            (day, json.dumps({"close": 100 + 2 * i})),
        )

    def result():
        row = {"code": "000001", "history_date": days[-1]}
        add_industry_comparisons(db, [row], days[-1])
        return row

    assert result()["relative_5d_pp"] == 5
    assert len(result()["industryComparison"]["points"]) == 6
    db.execute(
        "INSERT INTO research_a_share_price_history VALUES('800001.SWI',?,'1','conflict')",
        (days[2],),
    )
    assert "relative_5d_pp" not in result()
