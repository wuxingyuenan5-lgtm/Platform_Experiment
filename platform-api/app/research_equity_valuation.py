"""Index valuation charts built from separately attributed source series."""

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.research_equity_metrics import number

US_INDICES = [
    ("sp500", "标普500", "^GSPC"),
    ("ndx", "纳斯达克100", "^NDX"),
    ("dow", "道琼斯工业指数", "^DJI"),
    ("rut", "罗素2000", "^RUT"),
]
CN_CHARTS = [
    ("000300", "沪深300"),
    ("000016", "上证50"),
    ("399006", "创业板指"),
    ("000688", "科创50"),
]


def valuation_specs():
    result = [
        dict(
            id="us_price_" + key,
            name=name,
            url="https://query1.finance.yahoo.com/v8/finance/chart/" + symbol,
            kind="yahoo",
            params={"range": "10y", "interval": "1d"},
        )
        for key, name, symbol in US_INDICES
    ]
    for metric, path in [
        ("pb", "s-p-500-price-to-book/table/by-quarter"),
        ("cape", "shiller-pe/table/by-month"),
        ("ps", "s-p-500-price-to-sales/table/by-quarter"),
        ("dividend", "s-p-500-dividend-yield/table/by-month"),
    ]:
        result.append(
            dict(
                id="us_sp500_" + metric,
                name="Multpl / S&P 500 " + metric.upper(),
                url="https://www.multpl.com/" + path,
                kind="multpl",
            )
        )
    for metric in ["pe-trailing", "pe-forward", "pb", "cape", "dividend-yield"]:
        result.append(
            dict(
                id="us_ndx_" + metric,
                name="Siblis / Nasdaq 100 " + metric,
                url="https://siblisresearch.com/api/v1/NDX/" + metric,
                kind="index_metric",
                ticker="NDX",
            )
        )
    result.append(
        dict(
            id="us_rut_valuation",
            name="Siblis / Russell 2000",
            kind="siblis_table",
            url="https://siblisresearch.com/data/nasdaq-100-pe-ratio/",
        )
    )
    result.append(
        dict(
            id="us_ndx_valuation",
            name="Siblis / Nasdaq 100",
            kind="siblis_table",
            ticker="NASDAQ 100",
            url="https://siblisresearch.com/data/nasdaq-100-pe-ratio/",
        )
    )
    for key, ticker in [("dow", "dia"), ("sp500", "spy")]:
        slug = (
            "dow-jones-industrial-average-etf-trust-dia"
            if ticker == "dia"
            else "sp-500-etf-trust-spy"
        )
        result.append(
            dict(
                id="us_" + key + "_official",
                name="State Street / 指数特征",
                kind="ssga_index",
                url="https://www.ssga.com/us/en/individual/etfs/state-street-spdr-" + slug,
            )
        )
    result.append(
        dict(
            id="hk_hsiii",
            name="恒生互联网科技业指数 · 新浪财经",
            kind="sina_hk",
            url="https://finance.sina.com.cn/stock/hkstock/HSIII/klc2_kl.js",
        )
    )
    return result


def parse_index_metric(content, ticker):
    d = json.loads(content)
    if d.get("ticker") != ticker:
        raise ValueError("valuation_index_mismatch")
    return [{"date": r["trading_day (EOD)"], "value": number(r["value"])} for r in d["data"]]


def parse_ssga(content):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(content, "html.parser")
    section = next(
        (
            s
            for s in soup.select("section")
            if s.find("h2") and "Index Characteristics" in s.find("h2").get_text()
        ),
        None,
    )
    if section is None:
        raise ValueError("index_characteristics_missing")
    stamp = section.select_one("h2 .date").get_text(" ", strip=True).replace("as of ", "")
    day = datetime.strptime(stamp, "%b %d %Y").date().isoformat()
    fields = {
        "Price/Earnings": "pe",
        "Price/Earnings Ratio FY1": "forwardFy1",
        "Price/Cash Flow": "pcf",
    }
    row = {"date": day}
    for tr in section.select("tr"):
        cells = tr.select("th,td")
        if len(cells) == 2 and cells[0].get_text(" ", strip=True) in fields:
            row[fields[cells[0].get_text(" ", strip=True)]] = number(cells[1].get_text(strip=True))
    if not row.get("pe"):
        raise ValueError("index_pe_missing")
    return [row]


def parse_russell(content, target="Russell 2000"):
    import re

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(content, "html.parser")
    match = re.search(r"Data through\s+(\d{1,2} [A-Za-z]+ \d{4})", soup.get_text(" ", strip=True))
    if not match:
        raise ValueError("valuation_date_missing")
    day = datetime.strptime(match[1], "%d %B %Y").date().isoformat()
    current = None
    history = {}
    for table in soup.select("table"):
        trs = table.select("tr")
        for tr in trs:
            cells = [c.get_text(" ", strip=True) for c in tr.select("th,td")]
            if cells and cells[0] == target and len(cells) >= 5:
                current = dict(
                    date=day,
                    pe=number(cells[1]),
                    forward=number(cells[2]),
                    cape=number(cells[4]),
                    value=number(cells[1]),
                )
        if not trs:
            continue
        header = [c.get_text(" ", strip=True) for c in trs[0].select("th,td")]
        if not header or header[0] != "Month" or target not in header:
            continue
        column = header.index(target)
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.select("th,td")]
            if len(cells) <= column:
                continue
            # Only year-end observations have a separately unambiguous date.
            year = re.fullmatch(r"(\d{4}) Dec", cells[0])
            if year:
                value = number(cells[column])
                if value is not None:
                    history[year[1] + "-12-31"] = dict(
                        date=year[1] + "-12-31", pe=value, value=value
                    )
    if current is None:
        raise ValueError("index_row_missing")
    history[day] = current
    return [history[d] for d in sorted(history)]


CHOICE_CHILD = r"""
import json,sys,pandas as pd
from EmQuantAPI import c
try:
    login=c.start()
    if login.ErrorCode: raise RuntimeError('Choice login:'+str(login.ErrorCode))
    result=c.csd(
        '000300.SH,000016.SH,399006.SZ,000688.SH',
        'CLOSE,PETTM,PBMRQ,PSTTM,PCFTTM,DIVIDENDYIELDTTM',sys.argv[1],sys.argv[2],
        'Period=1,AdjustFlag=1,Order=1,Market=CNSESH,FillData=0,'
        'DelType=1,RowIndex=2,RECVtimeout=60,Ispandas=1')
    if not isinstance(result,pd.DataFrame): raise RuntimeError('Choice csd:'+str(result.ErrorCode))
    records=[]
    fields={'CLOSE':'close','PETTM':'pe','PBMRQ':'pb','PSTTM':'ps','PCFTTM':'pcf','DIVIDENDYIELDTTM':'dividend'}
    for column in fields: result[column]=pd.to_numeric(result[column],errors='coerce')
    for day,row in result.iterrows():
        record={'date':str(day)[:10].replace('/','-'),'code':row['CODES']}
        record.update({field:None if pd.isna(row[col]) else str(row[col])
                       for col,field in fields.items()})
        records.append(record)
    print(json.dumps({'ok':True,'records':records},allow_nan=False))
finally:c.stop()
"""


def collect_choice_indices():
    from app.research_equity_sources import archive, publish_artifact, read_artifact

    now = datetime.now(UTC)
    keys = ["choice_index_" + code for code, _ in CN_CHARTS]
    old = {key: read_artifact("sources/" + key) for key in keys}
    if all(
        d.get("fetchedAt") and now - datetime.fromisoformat(d["fetchedAt"]) < timedelta(hours=20)
        for d in old.values()
    ):
        return old
    local_now = datetime.now(ZoneInfo("Asia/Shanghai"))
    end = local_now.date()
    if (local_now.hour, local_now.minute) < (16, 15):
        end -= timedelta(days=1)
    # Clamp the anniversary for a leap-day observation.
    import calendar

    start = end.replace(
        year=end.year - 3, day=min(end.day, calendar.monthrange(end.year - 3, end.month)[1])
    )
    start += timedelta(days=1)
    try:
        child = subprocess.run(
            [
                str(Path(sys.base_prefix) / "python.exe"),
                "-c",
                CHOICE_CHILD,
                start.isoformat(),
                end.isoformat(),
            ],
            cwd=Path.home() / ".choice/EMQuantAPI_Python/python3",
            capture_output=True,
            text=True,
            encoding="utf8",
            errors="replace",
            timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        payload = next(
            json.loads(line) for line in child.stdout.splitlines() if line.startswith('{"ok": true')
        )
        digest = archive("choice_index_valuation", json.dumps(payload).encode(), now.isoformat())
        for code, name in CN_CHARTS:
            rows = [
                {k: v for k, v in r.items() if k != "code"}
                for r in payload["records"]
                if r["code"].split(".")[0] == code and r["close"] is not None
            ]
            if not rows:
                raise ValueError("Choice index history empty")
            key = "choice_index_" + code
            merged = {r["date"]: r for r in old[key].get("rows", [])}
            merged.update({r["date"]: r for r in rows})
            rows = [merged[d] for d in sorted(merged)]
            old[key] = dict(
                id=key,
                name="Choice / " + name,
                url="https://quantapi.eastmoney.com/",
                rows=rows,
                status="ready",
                fetchedAt=now.isoformat(),
                observationDate=rows[-1]["date"],
                rawSha256=digest,
            )
    except Exception as exc:
        for d in old.values():
            d.update(
                status="stale" if d.get("rows") else "error",
                attemptedAt=now.isoformat(),
                error=type(exc).__name__,
            )
    for key, d in old.items():
        publish_artifact("sources/" + key, d)
    return old


def build_valuation_charts(sources, market):
    charts = []

    def metric(doc, key, label, field="value", unit="倍"):
        rows = [
            dict(date=r["date"], value=r.get(field))
            for r in doc.get("rows", [])
            if number(r.get(field)) is not None
        ]
        return dict(
            id=key,
            label=label,
            unit=unit,
            history=rows,
            source=doc.get("name"),
            sourceUrl=doc.get("url"),
            status=doc.get("status", "no_data"),
        )

    if market == "cn":
        for code, name in CN_CHARTS:
            official = sources.get("csi_history_" + code, {})
            choice = sources.get("choice_index_" + code, {})
            primary = official if official.get("rows") else choice
            metrics = [metric(primary, "pe", "历史 PE TTM", "pe")]
            metrics += [
                metric(choice, k, label, k, "%" if k == "dividend" else "倍")
                for k, label in [
                    ("pb", "PB MRQ"),
                    ("ps", "PS TTM"),
                    ("pcf", "PCF TTM"),
                    ("dividend", "股息率 TTM"),
                ]
            ]
            prices = [
                dict(date=r["date"], value=r.get("close"))
                for r in primary.get("rows", [])
                if r.get("close") is not None
            ]
            charts.append(dict(id=code, name=name, prices=prices, metrics=metrics))
    else:
        for key, name, _ in US_INDICES:
            metrics = []
            if key == "sp500":
                metrics = [metric(sources.get("us_pe", {}), "pe", "历史 PE TTM", "pe")]
                metrics += [
                    metric(
                        sources.get("us_sp500_" + k, {}),
                        k,
                        label,
                        "pe",
                        "%" if k == "dividend" else "倍",
                    )
                    for k, label in [
                        ("pb", "PB"),
                        ("ps", "PS"),
                        ("cape", "CAPE"),
                        ("dividend", "股息率"),
                    ]
                ]
                metrics.append(
                    metric(
                        sources.get("us_sp500_official", {}),
                        "forwardFy1",
                        "前瞻 PE FY1",
                        "forwardFy1",
                    )
                )
            elif key == "ndx":
                metrics = [
                    metric(sources.get("us_ndx_" + k, {}), k, label)
                    for k, label in [
                        ("pe-trailing", "历史 PE TTM"),
                        ("pe-forward", "前瞻 PE NTM"),
                        ("pb", "PB"),
                        ("cape", "CAPE"),
                    ]
                ]
                public = sources.get("us_ndx_valuation", {})
                for m, field in zip(
                    [metrics[0], metrics[1], metrics[3]], ["pe", "forward", "cape"], strict=True
                ):
                    merged = {r["date"]: r for r in m["history"]}
                    merged.update(
                        {
                            r["date"]: dict(date=r["date"], value=r[field])
                            for r in public.get("rows", [])
                            if number(r.get(field)) is not None
                        }
                    )
                    m["history"] = [merged[d] for d in sorted(merged)]
                    if merged:
                        m.update(
                            status="ready", source=public.get("name"), sourceUrl=public.get("url")
                        )

            elif key == "rut":
                metrics = [
                    metric(sources.get("us_rut_valuation", {}), k, label, k)
                    for k, label in [
                        ("pe", "历史 PE TTM"),
                        ("forward", "前瞻 PE NTM"),
                        ("cape", "CAPE"),
                    ]
                ]
            else:
                metrics = [
                    metric(sources.get("us_dow_official", {}), k, label, k)
                    for k, label in [
                        ("pe", "历史 PE"),
                        ("forwardFy1", "前瞻 PE FY1"),
                        ("pcf", "PCF"),
                    ]
                ]
            charts.append(
                dict(
                    id=key,
                    name=name,
                    prices=sources.get("us_price_" + key, {}).get("rows", []),
                    metrics=metrics,
                )
            )
    return charts
