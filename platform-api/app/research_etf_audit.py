"""Read the producer's compact ETF evidence, without fetching or scanning history."""

from datetime import datetime, time
from zoneinfo import ZoneInfo


def broad_etf_checks(document, now, sessions):
    from app.data_audit import check, freshness

    group = "ETF数据"
    codes = document.get("catalogCodes", [])
    members = document.get("members", [])
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    today = local.date().isoformat()
    due = [
        day for day in sessions if day < today or (day == today and local.time() >= time(15, 10))
    ]
    expected = max(due, default=None)
    valid_catalog = (
        bool(codes)
        and len(codes) == len(set(codes))
        and sorted(codes) == sorted(m["code"] for m in members)
        and not document.get("missingRegisteredCodes")
    )
    result = [
        freshness(
            "etf.broad.producer",
            "宽基ETF生产与目录",
            group,
            document.get("updatedAt"),
            6,
            now,
            sourceDate=document.get("sourceDate"),
            expectedDate=expected,
            members=len(codes),
            missingRegisteredCodes=document.get("missingRegisteredCodes", []),
        )
    ]
    if not valid_catalog:
        result[0].update(status="error", message="宽基目录与成员证据不一致或为空")
    elif expected is None:
        result[0].update(status="warning", message="交易日历不可用，无法验证ETF应更新日期")
    for member in members:
        ready = (
            expected is not None
            and member.get("expectedDate") == expected
            and member.get("turnoverReady")
            and member.get("flowReady")
            and not member.get("sourceError")
        )
        result.append(
            check(
                "etf.broad.member." + member["code"],
                member["code"] + " · " + member["name"],
                group,
                "healthy" if ready else "warning",
                "当日成交额与净申购输入齐备" if ready else "成员输入缺失、滞后或采集异常",
                **{k: v for k, v in member.items() if k not in {"missingDates", "name"}},
                auditExpectedDate=expected,
                lastSuccessAt=member.get("sourceRetrievedAt"),
            )
        )
    gaps = {m["code"]: m["missingDates"] for m in members if m.get("missingDates")}
    result.append(
        check(
            "etf.broad.history",
            "宽基ETF历史完整性",
            group,
            "warning" if gaps else "healthy",
            "历史缺失成员需维护" if gaps else "已登记历史的应交易成员成交额齐备",
            sourceDate=document.get("sourceDate"),
            rows=document.get("historyDates"),
            partialDates=document.get("partialDates"),
            missingInputs=document.get("missingInputs"),
            missingByFund=gaps,
        )
    )
    return result


def minute_etf_check(document, now, sessions):
    from app.data_audit import check
    from app.research_etf_observation import LIVE_SYMBOLS

    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    today = local.date().isoformat()
    due = [d for d in sessions if d < today or (d == today and local.time() >= time(9, 35))]
    expected = max(due, default=None)
    coverage = document.get("minuteCoverage", {})
    gaps = {s: c["missingTimes"] for s, c in coverage.items() if c.get("missingTimes")}
    ready = (
        expected is not None
        and document.get("status") == "ready"
        and document.get("observationDate") == expected
        and set(coverage) == set(LIVE_SYMBOLS)
        and not gaps
        and all(c.get("date") == expected for c in coverage.values())
    )
    stamp = document.get("observationTime")
    age = None
    try:
        observed = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=local.tzinfo)
        age = (local - observed).total_seconds()
        trading = today in sessions and (
            time(9, 35) <= local.time() <= time(11, 35)
            or time(13, 5) <= local.time() <= time(15, 10)
        )
        if (trading and age > 300) or age < -300:
            ready = False
    except (ValueError, TypeError):
        ready = False
    if expected and (expected < today or local.time() >= time(15, 10)):
        ready = ready and all(c.get("through") == "15:00" for c in coverage.values())
    return check(
        "etf.minutes",
        "25只ETF分钟与累计成交额",
        "ETF数据",
        "healthy" if ready else "warning",
        "分钟输入齐备" if ready else "分钟输入有缺口、日期滞后或采集异常",
        sourceDate=document.get("observationDate"),
        expectedDate=expected,
        lastSuccessAt=document.get("retrievedAt"),
        observationTime=stamp,
        ageSeconds=age,
        missingByFund=gaps,
        members=len(coverage),
        recoveredFunds=[s for s, c in coverage.items() if c.get("recovered")],
    )
