import asyncio
import importlib.util
import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from app import research_capital_public as public


def test_sse_uses_observation_month_not_snapshot_month():
    rows = public.parse_residents({"result": [
        {"TERM": "2026.01", "MDATE": "202602", "A_PERSON": "10", "A_ORG": "1"},
        {"TERM": "2026.03", "MDATE": "202602", "A_PERSON": "0", "A_ORG": "0"},
        {"TERM": "2026年合计", "MDATE": "202602", "A_PERSON": "10", "A_ORG": "1"},
    ]})
    assert rows == [{"date": "2026-01-01", "personal": "10", "institutional": "1"}]


def test_social_return_does_not_use_realized_return():
    row = public.parse_social("2025年末，基金资产总额38,083.73亿元。投资收益率13.22%。已实现收益率7.01%。")[0]
    assert row["assets"] == "38083.73"
    assert row["returnPct"] == "13.22"
    assert row["domestic"] is None


def test_bank_units_and_published_rounding():
    text = "存续规模33.66万亿元。投资资产合计36.00万亿元。投向债券类、非标准化债权类2资产、权益类资产余额分别为18.06万亿元、1.82万亿元、0.67万亿元，分别占总投资资产的50.17%、5.06%、1.86%。"
    row = public.parse_bank(text, "中国银行业理财市场半年报告（2026年上）")[0]
    assert row["date"] == "2026-06-30"
    assert row["equity"] == "0.67"
    assert row["equityPct"] == "1.86"
    with pytest.raises(ValueError, match="requires_table_review"):
        public.parse_bank("存续规模33.66万亿元。投资资产合计36.00万亿元", "2026年上半年")


def test_public_errors_preserve_history_and_retry_cadence(tmp_path, monkeypatch):
    path = tmp_path / "research/capital-handbook-choice/public-supplement.json"
    stamp = "2026-11-07T00:00:00+00:00"
    public.save(path, {"foreign": [{"date": "2026-06-30", "equities": "46555.39"}],
                       "sources": {"foreign": {"fetchedAt": stamp}}})
    calls = []

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            calls.append(url)
            return httpx.Response(403, request=httpx.Request("GET", url))

    monkeypatch.setattr(public.httpx, "AsyncClient", Client)
    annuity_calls = []
    monkeypatch.setattr(public, "fetch_annuity", lambda *args: (
        annuity_calls.append(args) or ([], {"discovered": [], "errors": []})
    ))
    now = datetime(2026, 11, 8, tzinfo=UTC)
    first = asyncio.run(public.collect_public(tmp_path, now=now))
    assert first["foreign"][0]["equities"] == "46555.39"
    assert first["sources"]["foreign"]["fetchedAt"] == stamp
    assert first["sources"]["foreign"]["status"] == "error"
    assert len(calls) == 4 and len(annuity_calls) == 1
    asyncio.run(public.collect_public(tmp_path, now=now))
    assert len(calls) == 4 and len(annuity_calls) == 1


def test_official_annuity_types_and_return_windows():
    row = public.parse_pension("积累基金（亿元）45,605.462.建立计划 近三年累计收益率（%）16.374.待遇", "2026年二季度")
    assert row == {"date": "2026-06-30", "assets": "45605.46", "threeYearReturnPct": "16.37"}
    row = public.parse_pension("积累基金（亿元）32,856.47 本季度加权平均收益率（%）0.96", "2024年一季度")
    assert row["periodReturnPct"] == "0.96" and "threeYearReturnPct" not in row
    assert public.parse_occupational_pension(
        "全国31个省和中央单位职业年金基金投资运营规模3.78万亿元。",
        "2025年全国职业年金基金市场化投资运营情况",
    ) == {"date": "2025-12-31", "assets": "37800.00"}
    with pytest.raises(ValueError, match="outside_expected_units"):
        public.parse_pension("积累基金（亿元）45.60", "2026年二季度")


def test_incremental_choice_plan_retains_history_and_limits_issue_window(tmp_path):
    spec = importlib.util.spec_from_file_location("capital_worker", Path(__file__).parents[1] / "scripts/collect_capital_handbook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    work = tmp_path / "research/capital-handbook-choice"
    old = {"key": "fund-issues-2026-11-08", "function": "ctr", "args": "FundIssueStaticsInfo",
           "fields": "X", "options": "StartDate=2023-11-08,EndDate=2026-11-08", "estimatedCells": 185,
           "observationDate": "2026-11-08", "requestHash": "old"}
    public.save(work / "plan.json", {"jobs": [old]})
    public.save(work / (old["key"] + ".json"), {"data": []})
    plan = module.build_plan(tmp_path, date(2026, 11, 9))
    new = next(j for j in plan if j["key"] == "fund-issues-2026-11-09")
    assert "StartDate=2026-10-01" in new["options"]
    assert new["estimatedCells"] == 15
    retained = next(j for j in plan if j["key"] == old["key"])
    assert retained["options"] == old["options"]


def test_foreign_blank_months_are_not_zero():
    header = "".join(f"<td>2026.{m:02d}</td>" for m in range(1, 13))
    body = "<p>Unit: 100 Million Yuan</p><table><tr><td>Item</td>" + header + "</tr><tr><td>股票 Equities</td><td>40738.05</td>" + "<td></td>" * 11 + "</tr></table>"
    assert public.parse_foreign_html(body.encode()) == [{"date": "2026-01-31", "equities": "40738.05"}]


def test_choice_rejection_charges_reserved_budget_and_cannot_repeat(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from app import research_capital_handbook

    spec = importlib.util.spec_from_file_location("capital_worker_budget", Path(__file__).parents[1] / "scripts/collect_capital_handbook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "build_plan", lambda root, day: [{
        "key": "budget-test", "function": "ctr", "args": "report", "fields": "X",
        "options": "", "estimatedCells": 5, "observationDate": "2026-11-08",
    }])
    calls = []
    sdk = SimpleNamespace(
        start=lambda: (calls.append("login") or SimpleNamespace(ErrorCode=0)),
        stop=lambda: None,
        ctr=lambda *args: (calls.append("request") or SimpleNamespace(ErrorCode=10001029, ErrorMsg="quota")),
    )
    monkeypatch.setitem(sys.modules, "EmQuantAPI", SimpleNamespace(c=sdk))
    monkeypatch.setattr(research_capital_handbook, "publish", lambda root: None)
    monkeypatch.setattr(sys, "argv", ["worker", "--collect", "--incremental", "--max-cells", "5", "--data-root", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        module.run()
    assert exc.value.code == 2
    module.run()
    assert calls == ["login", "request"]
    state = public.read(tmp_path / "research/capital-handbook-choice/collection-state.json")
    assert sum(state["dailyRequestedCells"].values()) == 5
