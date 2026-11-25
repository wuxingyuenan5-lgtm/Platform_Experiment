"""Explicit, resumable Choice collection for the capital handbook research pages.

The capital scheduler runs this isolated worker at most daily. The budget counts requested
output cells, NOT the account's billable traffic. Credentials remain in the
SDK activation store. A quota rejection stops that function for the local day.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

INDUSTRIES = {
    "001": "农林牧渔",
    "003": "基础化工",
    "004": "钢铁",
    "005": "有色金属",
    "006": "电子",
    "007": "汽车",
    "008": "家用电器",
    "009": "食品饮料",
    "011": "轻工制造",
    "012": "医药生物",
    "013": "公用事业",
    "014": "交通运输",
    "015": "房地产",
    "016": "商贸零售",
    "018": "银行",
    "019": "非银金融",
    "020": "综合",
    "021": "建筑材料",
    "022": "建筑装饰",
    "024": "机械设备",
    "025": "国防军工",
    "026": "计算机",
    "027": "传媒",
    "028": "通信",
    "029": "纺织服饰",
    "030": "社会服务",
    "031": "电力设备",
    "032": "煤炭",
    "033": "石油石化",
    "034": "环保",
    "035": "美容护理",
}
HOLDINGS = "PCTBYFUND,PCTBYINSUR,PCTYINSURPRO,PCTBYQFII,PCTBYSSFUND,PCTBYCORPPENSION"
MARGIN = "RZYE,ALLFREEFLOATMV,SUMPURMONEY,AMOUNTSUM"


def build_plan(root: Path, as_of: date):
    start = date(as_of.year - 3, as_of.month, min(as_of.day, 28)).isoformat()
    quarters = [
        date(y, m, calendar.monthrange(y, m)[1]).isoformat()
        for y in range(as_of.year - 3, as_of.year + 1)
        for m in (3, 6, 9, 12)
        if start <= date(y, m, calendar.monthrange(y, m)[1]).isoformat() < as_of.isoformat()
    ]
    jobs = []

    def add(key, function, args, fields, options, cells, observed):
        jobs.append(
            dict(
                key=key,
                function=function,
                args=args,
                fields=fields,
                options=options + ",RECVtimeout=45,Ispandas=1",
                estimatedCells=cells,
                observationDate=observed,
            )
        )

    last_month = as_of.replace(day=1) - timedelta(days=1)
    month_index = as_of.year * 12 + as_of.month - 1 - 35
    market_start = date(month_index // 12, month_index % 12 + 1, 1)
    add(
        "resident-market-" + last_month.isoformat(),
        "csd",
        ["000300.SH", market_start.isoformat(), last_month.isoformat()],
        "CLOSE",
        "Period=3,AdjustFlag=1,Order=1",
        36,
        last_month.isoformat(),
    )

    for q in quarters:
        add(
            "public-fund-stocks-" + q, "ctr", "InstHolderTypeInfo",
            "MSECUCODE,SECURITYSHORTNAME,REPORTDATE,ORGTDYFPE,INT_CGJGJS,DEC_BENQICHIGU,DEC_SHANGQICHIGU,DEC_BENQISHIZHI",
            f"ReportDate={q},OrgType=1,PredictYear={q[:4]}", 36000, q,
        )
    # This aggregate report is small and has a longer history than the detailed panels.
    for y in range(2018, as_of.year + 1):
        for m in (3, 6, 9, 12):
            q = date(y, m, calendar.monthrange(y, m)[1]).isoformat()
            if q >= as_of.isoformat():
                continue
            add(
                "institutions-" + q,
                "ctr",
                "InstStatisticsInfo",
                "ORGTDYFPE,BCYZQ,DEC_BENQISHIZHI,DEC_SHANGQISHIZHI,REPORTDATE",
                "REPORTDATE=" + q,
                25 * 5,
                q,
            )
    for name, fields, options, estimate in (
        ("seasoned-issues", "MSECUCODE,DAT_SHANGSHIRIQI,SUMFINA,ATTACHNAME", "DateType=1", 4000),
        ("cash-dividends", "SECUCODE,REPORTDATE,DIVCASHPSBFTAX,DIVRTISSBASESHARES,DIVPAYDATE,DIVIMPLANNCDATE,SECURITYTYPE", "secucode=,DateType=1", 175000),
    ):
        add(f"capital-events-{name}-{last_month}", "ctr",
            "AddImplementInfo" if name == "seasoned-issues" else "DividendImplementationInfo",
            fields, f"StartDate={market_start},EndDate={last_month},{options}", estimate,
            last_month.isoformat())
    previous_plan = root / "research/capital-handbook-choice/plan.json"
    prior = json.loads(previous_plan.read_text(encoding="utf-8")) if previous_plan.exists() else {}
    issue_jobs = [j for j in prior.get("jobs", []) if j["key"].startswith("fund-issues-")
                  and (previous_plan.parent / (j["key"] + ".json")).exists()]
    issue_start = start
    if issue_jobs:
        latest = max(j["observationDate"] for j in issue_jobs)
        # One previous month plus current month allows late reports/revisions.
        issue_start = (date.fromisoformat(latest).replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()
    add(
        "fund-issues-" + as_of.isoformat(),
        "ctr",
        "FundIssueStaticsInfo",
        "ENDDATE,FIRSTRAISES,FIRSTRAISEM,TOTALNUMS,TOTALNUMM",
        f"StartDate={issue_start},EndDate={as_of.isoformat()},DATETYPE=2,CYCLE=2",
        (37 if not issue_jobs else 3) * 5,
        as_of.isoformat(),
    )
    path = root / "public/v1/macro/series/cn_margin_financing_balance.json"
    series = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    months = {}
    for row in series.get("observations", []):
        d = row["date"]
        if start <= d <= as_of.isoformat():
            months[d[:7]] = max(months.get(d[:7], d), d)
    codes = ["B_009001006" + k for k in INDUSTRIES]
    for d in sorted(months.values()):
        if d <= last_month.isoformat():
            add(f"foreign-market-cap-{d}", "cses", "B_001071", "SUMMV",
                f"IsHistory=1,TradeDate={d}", 1, d)
    for pos in range(0, len(codes), 6):
        batch = codes[pos : pos + 6]
        for q in quarters:
            add(
                f"industry-holdings-{q}-{pos}",
                "cses",
                ",".join(batch),
                HOLDINGS,
                f"IsHistory=1,ReportDate={q}",
                len(batch) * 6,
                q,
            )
        for d in sorted(months.values()):
            add(
                f"industry-margin-{d}-{pos}",
                "cses",
                ",".join(batch),
                MARGIN,
                f"IsHistory=1,TradeDate={d}",
                len(batch) * 4,
                d,
            )
    # Keep the original request for a day already collected, and all retained history.
    merged = {j["key"]: j for j in jobs}
    for job in prior.get("jobs", []):
        merged[job["key"]] = {k: v for k, v in job.items() if k != "requestHash"}
    return list(merged.values())


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--normalize-only", action="store_true")
    parser.add_argument(
        "--as-of", default=datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    )
    parser.add_argument("--max-cells", type=int, default=30000)
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--functions", default="ctr,cses,csd")
    parser.add_argument("--job-prefix", default="")
    parser.add_argument("--exclude-job-prefix", default="")
    parser.add_argument("--north-quarters", type=int, default=0)
    parser.add_argument(
        "--data-root", default=os.environ.get("HEDGE_BOARD_DATA_ROOT", "D:/自营数据库/hedge-board")
    )
    args = parser.parse_args()
    as_of, root = date.fromisoformat(args.as_of), Path(args.data_root)
    # OS lock is released on process exit, including a killed worker; no stale lease.
    if os.name == "nt":
        import msvcrt
        lock_path = root / "research/capital-handbook-choice/worker.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as worker_lock:
            if worker_lock.tell() == 0:
                worker_lock.write(b"0")
                worker_lock.flush()
            worker_lock.seek(0)
            try:
                msvcrt.locking(worker_lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise SystemExit("Capital handbook worker is already running")
            return execute(args, root, as_of)
    return execute(args, root, as_of)


def execute(args, root, as_of):
    def estimated_cells(job):
        if job["key"].startswith("public-fund-stocks-"):
            return max(job["estimatedCells"], 48000)
        return job["estimatedCells"]

    if args.normalize_only:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from app.research_capital_handbook import publish

        publish(root)
        return
    out = root / "research/capital-handbook-choice"
    out.mkdir(parents=True, exist_ok=True)
    if args.north_quarters:
        from collect_capital_sectors import collect_north, completed_quarters

        sys.path.insert(0, str(Path.home() / ".choice/EMQuantAPI_Python/python3"))
        from EmQuantAPI import c

        series = json.loads((root / "public/v1/macro/series/cn_margin_financing_balance.json").read_text(encoding="utf-8"))
        market_days = {}
        for row in series["observations"]:
            day = row["date"]
            market_days[day[:7]] = max(day, market_days.get(day[:7], day))
        if not any(quarter.isoformat()[:7] in market_days and
                   not (out / f"north-industry-{quarter}.json").exists()
                   for quarter in completed_quarters(as_of)):
            return
        login = c.start()
        if login.ErrorCode:
            raise RuntimeError(f"Choice login: {login.ErrorCode}")
        try:
            errors = collect_north(c, out, as_of, market_days, INDUSTRIES.values(), args.north_quarters)
        finally:
            c.stop()
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from app.research_capital_handbook import publish

        publish(root)
        if errors:
            raise SystemExit(2)
        return
    jobs = [j for j in build_plan(root, as_of) if j["function"] in args.functions.split(",")]
    for j in jobs:
        j["requestHash"] = hashlib.sha256(json.dumps(j, sort_keys=True).encode()).hexdigest()
    pending = []
    for job in jobs:
        cached = out / (job["key"] + ".json")
        if cached.exists():
            if (
                json.loads(cached.read_text(encoding="utf-8"))["request"]["requestHash"]
                != job["requestHash"]
            ):
                raise RuntimeError("Cached request differs; inspect before recollecting")
            recent_report = job["key"].startswith(("institutions-", "industry-holdings-", "public-fund-stocks-")) and (
                as_of - date.fromisoformat(job["observationDate"])
            ).days < 180
            stamp = json.loads(cached.read_text(encoding="utf-8")).get("fetchedAt")
            if args.incremental and recent_report and stamp and (
                datetime.now(UTC) - datetime.fromisoformat(stamp)
            ).days >= 7:
                pending.append(job)
        else:
            pending.append(job)
    if args.job_prefix:
        pending = [job for job in pending if job["key"].startswith(args.job_prefix)]
    if args.exclude_job_prefix:
        pending = [job for job in pending if not job["key"].startswith(args.exclude_job_prefix)]
    if args.incremental:
        # Old failures do not starve current observations. Every request stays in the plan.
        pending.sort(key=lambda j: (j["observationDate"], j["key"]), reverse=True)
        if args.job_prefix == "public-fund-stocks-":
            pending.sort(key=lambda j: (out / (j["key"] + ".json")).exists())
        selected, reserved = [], 0
        for job in pending:
            if reserved + estimated_cells(job) <= args.max_cells:
                selected.append(job)
                reserved += estimated_cells(job)
        pending = selected
    estimate = sum(estimated_cells(j) for j in pending)
    plan = {
        "asOf": as_of.isoformat(),
        "estimatedOutputCells": estimate,
        "budget": args.max_cells,
        "cachedRequests": len(jobs) - len(pending),
        "industryNames": {"B_009001006" + k: v for k, v in INDUSTRIES.items()},
        "jobs": jobs,
    }
    plan_tmp = out / "plan.json.tmp"
    plan_tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    plan_tmp.replace(out / "plan.json")
    print(
        json.dumps(
            {k: v for k, v in plan.items() if k not in {"jobs", "industryNames"}},
            ensure_ascii=False,
        )
    )
    if estimate > args.max_cells:
        raise SystemExit("Requested output estimate exceeds the explicit budget")
    if not args.collect:
        return
    if not pending:
        return
    import pandas as pd

    sys.path.insert(0, str(Path.home() / ".choice/EMQuantAPI_Python/python3"))
    from EmQuantAPI import c

    state_path = out / "collection-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    blocked = state.setdefault("blockedFunctions", {})
    def block_key(job):
        return f"ctr:{job['args']}" if job["function"] == "ctr" else job["function"]

    budget_key = {
        "capital-events-": "dailyEventRequestedCells",
        "public-fund-stocks-": "dailyFundRequestedCells",
    }.get(args.job_prefix, "dailyRequestedCells")
    daily = state.setdefault(budget_key, {})
    if args.incremental and daily.get(today, 0) >= args.max_cells:
        return
    allowed = [job for job in pending if blocked.get(block_key(job), {}).get("date") != today]
    previously_blocked = len(allowed) != len(pending)
    pending = allowed
    if not pending:
        raise SystemExit(2)
    had_error = previously_blocked
    used = 0
    login = c.start()
    if login.ErrorCode:
        raise RuntimeError(f"Choice login: {login.ErrorCode} {login.ErrorMsg}")
    try:
        for job in pending:
            function = job["function"]
            if blocked.get(block_key(job), {}).get("date") == today:
                continue
            cost = estimated_cells(job)
            if used + cost > args.max_cells:
                raise RuntimeError("Output cell budget exhausted")
            if args.incremental and daily.get(today, 0) + cost > args.max_cells:
                break
            # Reserve before the SDK call, including failed attempts and process interruption.
            daily[today] = daily.get(today, 0) + cost
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            if function == "csd":
                code, start, end = job["args"]
                result = c.csd(code, job["fields"], start, end, job["options"])
            else:
                result = getattr(c, function)(job["args"], job["fields"], job["options"])
            stamp = datetime.now(UTC).isoformat()
            if not isinstance(result, pd.DataFrame):
                had_error = True
                error = {
                    "date": today,
                    "error": result.ErrorCode,
                    "message": result.ErrorMsg,
                    "request": job,
                    "attemptedAt": stamp,
                }
                print(json.dumps(error, ensure_ascii=False), flush=True)
                state.setdefault("errors", {})[job["key"]] = error
                # Parameter/permission errors must be investigated before issuing
                # the same failed template hundreds of times.
                blocked[block_key(job)] = error
                state_path.write_text(
                    json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                continue
            frame = result.reset_index()
            records = json.loads(
                frame.to_json(orient="records", force_ascii=False, date_format="iso")
            )
            cells = len(result) * len(job["fields"].split(","))
            used += cells
            if not records and job["key"].startswith(("public-fund-stocks-", "foreign-market-cap-", "capital-events-")):
                had_error = True
                print(f"{job['key']} returned no observations; retaining prior data", flush=True)
                continue
            record = {
                "request": job,
                "source": "Choice EMQuantAPI",
                "fetchedAt": stamp,
                "returnedCells": cells,
                "data": records,
            }
            target = out / (job["key"] + ".json")
            temporary = target.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(target)
            print(f"{job['key']} rows={len(result)} returnedCells={cells}", flush=True)
            if used > args.max_cells:
                raise RuntimeError("Provider returned more cells than planned; stopped")
    finally:
        c.stop()
        state.update(lastAttempt=datetime.now(UTC).isoformat(), returnedCellsThisRun=used)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.research_capital_handbook import publish

    publish(root)
    if had_error:
        raise SystemExit(2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run()
