import asyncio
from decimal import Decimal

import pandas as pd
import pytest

from app import research_cn_institutions as institution


def public_text(legacy=False):
    prefix = "开放式基金\n其中：" if legacy else ""
    return f"""份额（亿份） 净值（亿元）
    （2026/9/30） （2026/8/31）
    {prefix}股票基金 10 12.30 25.60 9 11.30 23.60
    其中：混合基金 3 6.30 7.10 3 6.10 6.90
    债券基金 4 5.00 8.00 4 4.00 7.00
    {"货币基金" if legacy else "货币市场基金"} 5 9 10 5 9 10
    {"合计" if legacy else "全部"} 22 32.60 50.70 21 30.40 47.50
    """


def test_public_dated_columns_and_classification_boundary():
    rows = institution.parse_public(public_text())
    assert rows[0]["date"] == "2026-09-30"
    assert rows[1]["stockAssets"] == "23.60"
    assert rows[0]["stockShares"] == "12.30"
    assert rows[0]["basis"] == "all"
    assert institution.parse_public(public_text(True))[0]["basis"] == "open"
    with pytest.raises(ValueError, match="units_changed"):
        institution.parse_public(public_text().replace("亿份", "万份"))
    with pytest.raises(ValueError, match="columns_changed"):
        institution.parse_public(public_text().replace("25.60", "--"))


def test_private_stock_not_registration_or_manager_counts():
    text = """（2026 年 9 月）私募证券投资基金管理人 7,172 家。
    （一）私募基金产品月度备案情况
    私募证券投资基金 3\n1,058只，新备案规模245.97亿元；
    （二）私募基金存续情况
    存续私募证券投资基金84,293只，存续规模9.13万亿元；"""
    row = institution.parse_private(text)[0]
    assert row["securitiesCount"] == 84293
    assert Decimal(row["securitiesAssets"]) == Decimal("91300")
    assert row["newRegistered"] == "245.97"
    assert row["date"] == "2026-09-30"
    with pytest.raises(ValueError, match="stock_missing"):
        institution.parse_private(text.replace("9.13万亿元", "--万亿元"))


def test_insurance_ratio_uses_group_total_and_keeps_funds_separate(monkeypatch):
    frame = pd.DataFrame(
        [
            ["2026年二季度保险公司资金运用情况表", "单位：亿元，%", None],
            [" 保险公司", "资金运用余额", 400],
            ["其中：财产险公司", "资金运用余额", 100],
            [None, "   股票", 10],
            [None, "证券投资基金", 20],
            [None, "长期股权投资", 5],
            [" 人身险公司", "资金运用余额", 250],
            [None, "股票", 30],
            [None, "证券投资基金", 40],
            [None, "长期股权投资", 50],
        ]
    )
    monkeypatch.setattr(institution.pd, "read_excel", lambda *a, **kw: frame)
    row = institution.parse_insurance(b"test")[0]
    assert row["date"] == "2026-06-30"
    assert Decimal(row["lifeStockPct"]) == 12
    assert Decimal(row["propertyStockPct"]) == 10
    assert Decimal(row["lifeFunds"]) == 40
    assert Decimal(row["totalAssets"]) == 400  # Not property + life.
    frame.iloc[8, 1] = "未分类"
    with pytest.raises(ValueError, match="fields_missing"):
        institution.parse_insurance(b"test")


def test_failed_collection_preserves_previous_rows(monkeypatch):
    old = {
        "sources": {
            key: {
                "rows": [{"date": "2026-09-30", "basis": "all", "stockAssets": "1.25"}],
                "fetchedAt": "2026-10-01T00:00:00+00:00",
            }
            for key in institution.SOURCES
        }
    }
    monkeypatch.setattr(institution, "read_artifact", lambda *a: old)
    published = []
    monkeypatch.setattr(institution, "publish_artifact", lambda name, doc: published.append(doc))

    class BrokenClient:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            raise OSError("source unavailable")

    monkeypatch.setattr(institution.httpx, "AsyncClient", BrokenClient)
    result = asyncio.run(institution.collect(force=True))
    assert len(published) == len(institution.SOURCES)
    for source in result["sources"].values():
        assert source["status"] == "error"
        assert source["rows"][0]["stockAssets"] == "1.25"
        assert source["fetchedAt"] == "2026-10-01T00:00:00+00:00"


def test_read_is_local_and_reports_stale_collection(monkeypatch):
    monkeypatch.setattr(
        institution,
        "read_artifact",
        lambda *a: {
            "sources": {
                "public": {"status": "ready", "fetchedAt": "2020-01-01T00:00:00+00:00", "rows": []}
            }
        },
    )
    result = institution.read_institutions()
    assert result["public"]["isStale"]
    assert result["insurance"]["status"] == "unavailable"
    assert result["insurance"]["rows"] == []
