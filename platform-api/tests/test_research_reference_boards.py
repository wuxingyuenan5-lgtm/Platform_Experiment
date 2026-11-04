from decimal import Decimal
import asyncio
import pytest
from app import research_reference_boards as board

pytestmark=pytest.mark.unit


def test_driver_cross_term_and_residual_reconcile(monkeypatch):
    row={"year":2025,"peChange":"0.2","epsChange":"0.1","priceReturn":"0.35","endingPE":"30","endingEPS":"200"}
    monkeypatch.setattr(board,"read_artifact",lambda name:{"payload":{"series":[row]}} if name.endswith("sp_drivers") else {})
    r=board.read_references("stocks")["driverRows"][0]
    assert r["peContribution"]==Decimal(21)
    assert r["epsContribution"]==Decimal(11)
    assert r["residual"]==Decimal(3)
    assert sum(r[k] for k in ["peContribution","epsContribution","residual"])==r["returnPct"]


def test_missing_month_is_not_zero():
    doc={"years":[{"year":2026,"months":{"1":"0","2":None},"annual":None}]}
    assert board.validate("sp_monthly",doc)["years"][0]["months"]["2"] is None


@pytest.mark.parametrize("key,payload",[
    ("dli_regime",{"percentile5y":101,"dataAsOf":"2026-10-30"}),
    ("sp_monthly",{"years":[{"year":2026,"months":{"13":0}}]}),
    ("sp_drawdowns",{"annual":[{"year":2026,"dd":"-1.1"}]}),
    ("dli_history",{"dli":[{"date":"2026-10-30"},{"date":"2026-10-30"}]}),
    ("dli_series_tga",{"data":[{"date":"2026-10-30","value":"NaN"}]}),
])
def test_bad_source_is_rejected(key,payload):
    with pytest.raises((ValueError,KeyError)): board.validate(key,payload)


def test_failure_keeps_last_good_and_never_replaces_with_zero(monkeypatch):
    monkeypatch.setattr(board,"SOURCES",{"dli_regime":"https://example.invalid"})
    old={"payload":{"percentile5y":64,"dataAsOf":"2026-10-30"},"status":"ready"}
    monkeypatch.setattr(board,"read_artifact",lambda name:old)
    written=[]
    monkeypatch.setattr(board,"publish_artifact",lambda name,doc:written.append(doc))
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*a): pass
        async def get(self,url): raise TimeoutError()
    monkeypatch.setattr(board.httpx,"AsyncClient",lambda **kw:Client())
    assert asyncio.run(board.refresh_references(force=True))=={"dli_regime":"stale"}
    assert written[0]["payload"]==old["payload"] and written[0]["error"]=="TimeoutError"
