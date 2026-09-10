from datetime import date

import pytest

from app.research_provider_errors import ResearchProviderError
from app.research_provider_shenwan import index_identities, normalize_memberships


def test_official_history_uses_latest_effective_classification_not_file_order():
    taxonomy = [
        [None, None, None, None, "电子", None, None, "270000"],
        [None, None, None, None, None, "半导体", None, "270100"],
        [None, None, None, None, None, None, "集成电路设计", "270101"],
        [None, None, None, None, "食品饮料", None, None, "340000"],
        [None, None, None, None, None, "白酒Ⅱ", None, "340100"],
    ]
    records = [
        {"股票代码": "600001", "计入日期": "2026-09-01", "行业代码": "270101"},
        {"股票代码": "600001", "计入日期": "2021-07-30", "行业代码": "340101"},
        {"股票代码": "600001", "计入日期": "2026-10-01", "行业代码": "340101"},
        {"股票代码": "600002", "计入日期": "2021-07-30", "行业代码": "340101"},
    ]
    result = normalize_memberships(
        records,
        taxonomy,
        {"电子": "801080", "食品饮料": "801120"},
        {"半导体": "801081", "白酒II": "801125"},
        version="sw-2021-fixture",
        as_of=date(2026, 9, 7),
    )
    assert result[0].sw_l2_code == "801081"
    assert result[0].effective_from == date(2026, 9, 1)
    assert result[1].sw_l2_code == "801125"


def test_unknown_taxonomy_cannot_be_published_as_an_empty_success():
    with pytest.raises(ResearchProviderError, match="shenwan_membership_empty"):
        normalize_memberships([], [], {}, {}, version="fixture", as_of=date(2026, 9, 7))
    with pytest.raises(ResearchProviderError, match="identity_missing"):
        index_identities("<html>Source unavailable</html>")
