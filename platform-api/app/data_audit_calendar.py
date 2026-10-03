"""Independent Sina exchange-session calendar, cached by this platform only."""

import json
from datetime import UTC, date, datetime, timedelta

import httpx

from app.database_connection import connection, read_only_connection

URL = "https://finance.sina.com.cn/realstock/company/klc_td_sh.txt"


def refresh_calendar():
    with read_only_connection() as db:
        row = db.execute("SELECT fetched_at FROM data_audit_calendar WHERE market='CN'").fetchone()
    if row and datetime.now(UTC) - datetime.fromisoformat(row[0]) < timedelta(days=7):
        return
    # Use the installed provider's decoder, not its unbounded requests.get wrapper.
    from akshare.tool.trade_date_hist import hk_js_decode, py_mini_racer

    response = httpx.get(URL, timeout=8, trust_env=False)
    response.raise_for_status()
    encoded = response.text.split("=", 1)[1].split(";", 1)[0].strip().strip('"')
    with py_mini_racer.MiniRacer() as decoder:
        decoder.eval(hk_js_decode)
        values = decoder.call("d", encoded)
    days = sorted({str(value)[:10] for value in values if date.fromisoformat(str(value)[:10])})
    if len(days) < 200 or days[-1] < datetime.now(UTC).date().isoformat():
        raise ValueError("calendar does not cover current date")
    with connection() as db:
        db.execute(
            "INSERT INTO data_audit_calendar VALUES('CN',?,?,?) "
            "ON CONFLICT(market) DO UPDATE SET fetched_at=excluded.fetched_at, "
            "days_json=excluded.days_json,source=excluded.source",
            (datetime.now(UTC).isoformat(), json.dumps(days), URL),
        )


def calendar_snapshot(db, today):
    row = db.execute("SELECT * FROM data_audit_calendar WHERE market='CN'").fetchone()
    if not row:
        return None
    days = json.loads(row["days_json"])
    if not days or days[-1] < today:
        return None
    return {"days": days, "fetchedAt": row["fetched_at"], "source": row["source"]}
