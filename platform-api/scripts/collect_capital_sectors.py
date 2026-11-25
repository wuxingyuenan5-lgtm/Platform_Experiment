"""Choice sector snapshots for the capital handbook worker."""

import calendar
import json
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal


def completed_quarters(as_of):
    return [day for year in range(as_of.year - 3, as_of.year + 1) for month in (3, 6, 9, 12)
            if (day := date(year, month, calendar.monthrange(year, month)[1]))
            >= date(as_of.year - 3, as_of.month, min(as_of.day, 28))
            and day + timedelta(days=14) <= as_of][::-1]


def checked_frame(result):
    import pandas as pd

    if not isinstance(result, pd.DataFrame):
        raise ValueError(f"Choice {result.ErrorCode}: {result.ErrorMsg}")
    if not result.index.is_unique:
        raise ValueError("duplicate_choice_codes")
    return result


def rows(result):
    return json.loads(checked_frame(result).reset_index().to_json(
        orient="records", force_ascii=False, double_precision=15), parse_float=Decimal)


def batched(c, codes, fields, options):
    for left in range(0, len(codes), 500):
        batch = codes[left:left + 500]
        data = rows(c.css(",".join(batch), fields, options + ",RECVtimeout=35,Ispandas=1"))
        if {r["CODES"] for r in data} != set(batch):
            raise ValueError("choice_snapshot_coverage_changed")
        yield from data


def north_snapshot(c, quarter, trade_day, allowed_industries, work):
    membership = rows(c.sector("001047", trade_day, "RECVtimeout=35,Ispandas=1"))
    codes = sorted(r["SECUCODE"] for r in membership if re.fullmatch(r"\d{6}\.(SH|SZ)", r["SECUCODE"]))
    if len(codes) < 1800 or len(set(codes)) != len(codes):
        raise ValueError("northbound_universe_incomplete")
    fields = "SHAREHDNUM,CLOSE,HISSW2021"
    options = f"TradeDate={trade_day},EndDate={trade_day},Classification=1,AdjustFlag=1"
    data = list(batched(c, codes, fields, options))
    report = aggregate_north(data, quarter, trade_day, allowed_industries)
    stamp = datetime.now(UTC).isoformat()
    report["fetchedAt"] = stamp
    path = work / f"north-sector-raw-{quarter}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"quarter": quarter, "tradeDate": trade_day, "fields": fields,
                              "options": options, "fetchedAt": stamp, "data": data},
                             ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)
    return report


def aggregate_north(data, quarter, trade_day, allowed_industries):
    totals = {}
    positive, joined = 0, 0
    explicit, exclusions = 0, []
    for row in data:
        if str(row["DATES"])[:10].replace("/", "-") != trade_day:
            raise ValueError("northbound_wrong_trading_date")
        raw = row["SHAREHDNUM"]
        if raw is None:
            continue
        explicit += 1
        shares = Decimal(str(raw))
        if shares < 0:
            raise ValueError("northbound_negative_shares")
        if shares == 0:
            continue
        positive += 1
        industry = row["HISSW2021"]
        price = Decimal(str(row["CLOSE"])) if row["CLOSE"] is not None else None
        if price is None or price <= 0 or industry not in allowed_industries:
            exclusions.append(row["CODES"])
            continue
        joined += 1
        amount, count = totals.get(industry, (Decimal(0), 0))
        totals[industry] = (amount + shares * price, count + 1)
    if positive < len(data) * 0.70 or joined < positive * 0.99 or len(totals) < 25:
        raise ValueError(f"northbound_incomplete expected={len(data)} explicit={explicit} positive={positive} joined={joined} industries={len(totals)}")
    denominator = sum(v for v, _ in totals.values())
    return {
        "date": quarter, "tradeDate": trade_day, "eligibleCount": len(data), "reportedCount": explicit,
        "coveredCount": joined, "excludedCodes": exclusions,
        "rows": [{"name": name, "valueYi": str(value / 100_000_000), "stocks": count,
                   "weightPct": str(value / denominator * 100)}
                 for name, (value, count) in sorted(totals.items(), key=lambda row: (-row[1][0], row[0]))],
    }


def collect_north(c, work, as_of, market_days, industries, limit):
    reports = 0
    errors = []
    for quarter in completed_quarters(as_of):
        day = quarter.isoformat()
        target = work / f"north-industry-{day}.json"
        trade_day = market_days.get(day[:7])
        if target.exists() or not trade_day or reports >= limit:
            continue
        reports += 1
        try:
            result = north_snapshot(c, day, trade_day, set(industries), work)
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            temporary.replace(target)
            print(f"north-industry {day}: {result['coveredCount']}/{result['eligibleCount']}", flush=True)
        except ValueError as exc:
            errors.append(f"{day}: {exc}")
            print(errors[-1], flush=True)
            if "10001029" in str(exc):
                break
    return errors
