from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.a_share_research_policy import (
    aggregate_shenwan_level2,
    annualized_volatility_20,
    calculate_short_term_emotion_rates,
    classify_market_breadth,
    classify_speculation,
)
from app.research_cache import LastKnownGoodResearchCache
from app.research_data_schemas import AShareTurnoverStock, ShenwanMembership

pytestmark = pytest.mark.unit


def _stock(
    code: str,
    name: str,
    turnover: str,
    return_pct: str | None = None,
    net_inflow: str | None = None,
) -> AShareTurnoverStock:
    return AShareTurnoverStock(
        securityCode=code,
        securityName=name,
        turnoverYuan=Decimal(turnover),
        returnPct=Decimal(return_pct) if return_pct is not None else None,
        netInflowYuan=Decimal(net_inflow) if net_inflow is not None else None,
    )


def _membership(
    code: str,
    l1_code: str,
    l1_name: str,
    l2_code: str,
    l2_name: str,
) -> ShenwanMembership:
    return ShenwanMembership(
        securityCode=code,
        swL1Code=l1_code,
        swL1Name=l1_name,
        swL2Code=l2_code,
        swL2Name=l2_name,
        classificationVersion="test-version",
        effectiveFrom=date(2026, 1, 1),
    )


def test_annualized_volatility_requires_twenty_returns() -> None:
    assert annualized_volatility_20([Decimal("10")] * 20) is None
    assert annualized_volatility_20([Decimal("10")] * 21) == Decimal("0.0000")
    assert annualized_volatility_20([Decimal("10")] * 20 + [Decimal("0")]) is None


def test_market_breadth_uses_reference_thresholds() -> None:
    assert classify_market_breadth(599, 1) == "冰点"
    assert classify_market_breadth(600, 1000) == "偏弱"
    assert classify_market_breadth(700, 1000) == "中性"
    assert classify_market_breadth(1200, 1000) == "偏强"
    assert classify_market_breadth(2500, 1000) == "普涨"


def test_speculation_uses_real_limit_up_count() -> None:
    assert classify_speculation(29) == "冰点"
    assert classify_speculation(30) == "普通"
    assert classify_speculation(60) == "活跃"
    assert classify_speculation(100) == "亢奋"


def test_short_term_rates_keep_zero_denominators_unavailable() -> None:
    empty = calculate_short_term_emotion_rates(
        limit_up_count=0,
        broken_board_count=0,
        today_lianban_count=0,
        yesterday_limit_up_count=0,
    )
    assert empty.seal_rate is None
    assert empty.break_rate is None
    assert empty.promotion_rate is None

    rates = calculate_short_term_emotion_rates(
        limit_up_count=60,
        broken_board_count=40,
        today_lianban_count=15,
        yesterday_limit_up_count=50,
    )
    assert rates.seal_rate == Decimal("60.0000")
    assert rates.break_rate == Decimal("40.0000")
    assert rates.promotion_rate == Decimal("30.0000")


def test_shenwan_level2_aggregation_keeps_threshold_report_separate() -> None:
    threshold = Decimal("10000000000")
    stocks = [
        _stock("600001", "半导体甲", "12000000000", "2.0", "100000000"),
        _stock("600002", "半导体乙", "10000000000", "-1.0", "-20000000"),
        _stock("600003", "通信设备甲", "8000000000", "1.0", None),
        _stock("600004", "待匹配股票", "10000000000", "3.0", "50000000"),
    ]
    memberships = [
        _membership("600001", "801080", "电子", "801081", "半导体"),
        _membership("600002", "801080", "电子", "801081", "半导体"),
        _membership("600003", "801770", "通信", "801773", "通信设备"),
    ]

    result = aggregate_shenwan_level2(
        stocks=stocks,
        memberships=memberships,
        threshold_yuan=threshold,
        top_n=10,
    )

    assert [item.sw_l2_name for item in result.sw2_top] == ["半导体", "通信设备"]
    semi = result.sw2_top[0]
    assert semi.rank == 1
    assert semi.turnover_yuan == Decimal("22000000000.00")
    assert semi.market_share_pct == Decimal("55.0000")
    assert semi.return_pct == Decimal("0.6364")
    assert semi.net_inflow_yuan == Decimal("80000000.00")

    assert result.threshold.operator == ">"
    assert [(item.sw_l2_name, item.stock_count) for item in result.threshold.industries] == [
        ("半导体", 1)
    ]
    assert [item.security_code for item in result.threshold.stocks] == ["600001"]
    assert result.unmatched_security_codes == ["600004"]
    assert result.threshold.unmatched_security_codes == ["600004"]


def test_last_known_good_cache_rejects_empty_overwrite() -> None:
    now = datetime(2026, 7, 30, 1, 0, tzinfo=UTC)
    cache = LastKnownGoodResearchCache[list[int]](
        ttl=timedelta(minutes=5),
        is_meaningful=bool,
        now=lambda: now,
    )

    assert cache.store("market", [1, 2, 3], fetched_at=now)
    assert not cache.store("market", [], fetched_at=now + timedelta(minutes=1))
    assert cache.get("market") is not None
    assert cache.get("market").value == [1, 2, 3]  # type: ignore[union-attr]


def test_cache_requires_timezone() -> None:
    cache = LastKnownGoodResearchCache[list[int]](
        ttl=timedelta(minutes=5),
        is_meaningful=bool,
    )
    with pytest.raises(ValueError, match="timezone"):
        cache.store("market", [1], fetched_at=datetime(2026, 7, 30, 1, 0))
