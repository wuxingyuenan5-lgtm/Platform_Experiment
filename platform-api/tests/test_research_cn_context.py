import asyncio
from decimal import Decimal

import pytest

from app import research_cn_context as context


def test_same_day_duplicates_preserve_consensus_and_quarantine_conflicts():
    rows = context.parse_context("below_all", [
        {"date": "2020-02-21", "belowNetAsset": 358, "totalCompany": 3793, "close": 3039},
        {"date": "2020-02-21", "belowNetAsset": 358, "totalCompany": 3794, "close": 3039},
        {"date": "2020-02-20", "belowNetAsset": 0, "totalCompany": 3793}])
    assert len(rows) == 2
    assert rows[0]["value"] == 0
    assert rows[1]["count"] == 358
    assert rows[1]["total"] is None
    assert rows[1]["value"] is None
    assert rows[1]["close"] == 3039
    assert rows[1]["conflictFields"] == "total"


def test_below_ratio_and_bad_denominator():
    assert context.parse_context("below_all", [{"date":"2026-10-30", "belowNetAsset":540, "totalCompany":5223}])[0]["value"] == Decimal(540) / 5223 * 100
    with pytest.raises(ValueError, match="below_total_mismatch"):
        context.parse_context("below_all", [{"date":"2026-10-30", "belowNetAsset":5, "totalCompany":4}])
    with pytest.raises(ValueError, match="count_invalid"):
        context.parse_context("below_all", [{"date":"2026-10-30", "belowNetAsset":1.5, "totalCompany":4}])


def test_marketcap_gdp_units_and_conflicting_price_are_independent():
    raw={"data":[{"date":"2026-10-30", "marketCap":1148975.43, "gdp":1401879, "close":3985},
                  {"date":"2026-10-30", "marketCap":1148975.43, "gdp":1401879, "close":3986}]}
    row=context.parse_context("buffett",raw)[0]
    assert row["value"] == Decimal('1148975.43') / Decimal('1401879') * 100
    assert row["close"] is None
    with pytest.raises(ValueError, match="denominator_invalid"):
        context.parse_context("buffett", {"data":[{"date":"2026-10-30","marketCap":1,"gdp":0}]})


def test_breadth_missing_is_not_zero_and_net_is_not_a_return():
    rows=context.parse_context("highlow", {"data":[{"date":"2026-10-09","high20":0,"low20":2},{"date":"2026-10-30","close":3599}]})
    assert rows[0]["net20"] == -2
    assert rows[1]["high20"] is None and rows[1]["net20"] is None
    with pytest.raises(ValueError, match="ma_percent_invalid"):
        context.parse_context("ma", {"data":[{"date":"2026-10-09","value20":101}]})


def test_risk_pe_conventions_exact_date_join_and_no_fill():
    rows=context.risk_history([
        {"date":"2026-10-28","peLyr":20,"pe":10},
        {"date":"2026-10-29","peLyr":20,"pe":10},
        {"date":"2026-10-30","peLyr":0,"pe":-5}],
        [{"date":"2026-10-28","value":"1.65"},{"date":"2026-10-30","value":"1.65"}])
    assert rows[0]["erpLyr"] == Decimal('3.35')
    assert rows[0]["erpTtm"] == Decimal('8.35')
    assert rows[1]["erpLyr"] is None
    assert rows[2]["earningsLyr"] is None and rows[2]["erpTtm"] is None


def test_failed_source_does_not_erase_history_or_block_other_sources(monkeypatch):
    old={"sources":{"ma":{"status":"ready","data":[{"date":"2026-10-09","ma5":"53"}]}},"generatedAt":None}
    monkeypatch.setattr(context,"read_context",lambda group: old if group=='breadth' else {"sources":{},"generatedAt":None})
    writes=[]
    monkeypatch.setattr(context,"publish_artifact",lambda key,doc:writes.append((key,doc)))
    monkeypatch.setattr(context,"archive",lambda *args:'hash')
    class Response:
        def __init__(self,content): self.content=content
        def raise_for_status(self): pass
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,url,**kwargs):
            if '/api/' not in url and 'statistics-data' not in url:
                return Response(b'<meta name="_csrf" content="public">')
            if 'get-marketcap-gdp' in url:
                return Response(b'{"data":[{"date":"2026-10-30","marketCap":100,"gdp":200}]}')
            raise TimeoutError('public source unavailable')
    monkeypatch.setattr(context.httpx,'AsyncClient',Client)
    async def no_delay(*args): pass
    monkeypatch.setattr(context.asyncio, 'sleep', no_delay)
    result=asyncio.run(context.collect_context(force=True))
    assert result['breadth']['sources']['ma']['status']=='error'
    assert result['breadth']['sources']['ma']['data']==[{"date":"2026-10-09","ma5":"53"}]
    assert result['macroValue']['sources']['buffett']['status']=='ready'
    assert writes


def test_public_pe_six_conventions_missing_conflicts_and_no_rank_copy():
    raw = {"data": [
        {"date": "2026-09-30", "addLyrPe": 13, "addTtmPe": 12, "lyrPe": 32, "ttmPe": 28,
         "middleLyrPe": 19, "middleTtmPe": 17, "close": 4000, "middleTtmPeQuantile": .99},
        {"date": "2026-10-30", "addTtmPe": -1, "ttmPe": 0, "middleTtmPe": 17},
        {"date": "2026-10-30", "addTtmPe": -1, "ttmPe": 0, "middleTtmPe": 18}]}
    rows = context.parse_context("pe_000300", raw)
    assert [rows[0][k] for k in context.PE_FIELDS] == list(map(Decimal, [13, 12, 32, 28, 19, 17]))
    assert "middleTtmPeQuantile" not in rows[0]
    assert rows[1]["addTtmPe"] is None and rows[1]["ttmPe"] is None
    assert rows[1]["middleTtmPe"] is None
    assert rows[1]["conflictFields"] == "middleTtmPe"
    with pytest.raises(ValueError, match="public_pe_empty"):
        context.parse_context("pe_000300", {"data": [{"date": "2026-10-30", "close": 4000}]})
    missing_price = context.parse_context("pe_000300", {"data": [{"date": "2026-10-30", "addTtmPe": 12, "close": 0}]})[0]
    assert missing_price["close"] is None and missing_price["addTtmPe"] == 12
    assert missing_price["invalidFields"] == "close"
