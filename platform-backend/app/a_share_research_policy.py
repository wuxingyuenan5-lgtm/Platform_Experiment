from __future__ import annotations

import math
import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.research_data_schemas import (
    AShareResearchAggregation,
    AShareTurnoverStock,
    ShenwanLevel2Aggregate,
    ShenwanMembership,
    TurnoverThresholdIndustryCount,
    TurnoverThresholdResult,
    TurnoverThresholdStock,
)

PCT_QUANT = Decimal("0.0001")
MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class ShortTermEmotionRates:
    seal_rate: Decimal | None
    break_rate: Decimal | None
    promotion_rate: Decimal | None


@dataclass
class _Sw2Bucket:
    membership: ShenwanMembership
    turnover_yuan: Decimal = Decimal("0")
    weighted_return_numerator: Decimal = Decimal("0")
    weighted_return_denominator: Decimal = Decimal("0")
    net_inflow_yuan: Decimal = Decimal("0")
    has_net_inflow: bool = False


def annualized_volatility_20(closes: Sequence[Decimal | float | int]) -> Decimal | None:
    """Return 20-session annualized log-return volatility in percent.

    The calculation requires 21 strictly positive closing prices. Suspended sessions must not be
    inserted as zero returns by callers. The newest 21 valid observations are used.
    """

    if len(closes) < 21:
        return None
    values = [float(value) for value in closes[-21:]]
    if any(not math.isfinite(value) or value <= 0 for value in values):
        return None
    log_returns = [math.log(values[index] / values[index - 1]) for index in range(1, 21)]
    volatility = statistics.stdev(log_returns) * math.sqrt(252) * 100
    return Decimal(str(volatility)).quantize(PCT_QUANT, rounding=ROUND_HALF_UP)


def classify_market_breadth(up: int, down: int) -> str:
    if up < 0 or down < 0:
        raise ValueError("up and down counts must be non-negative")
    if up < 600:
        return "冰点"
    ratio = Decimal(up) / Decimal(max(down, 1))
    if ratio < Decimal("0.7"):
        return "偏弱"
    if ratio < Decimal("1.2"):
        return "中性"
    if ratio < Decimal("2.5"):
        return "偏强"
    return "普涨"


def classify_speculation(real_limit_up: int) -> str:
    if real_limit_up < 0:
        raise ValueError("real limit-up count must be non-negative")
    if real_limit_up >= 100:
        return "亢奋"
    if real_limit_up >= 60:
        return "活跃"
    if real_limit_up >= 30:
        return "普通"
    return "冰点"


def calculate_short_term_emotion_rates(
    *,
    limit_up_count: int,
    broken_board_count: int,
    today_lianban_count: int,
    yesterday_limit_up_count: int,
) -> ShortTermEmotionRates:
    values = (limit_up_count, broken_board_count, today_lianban_count, yesterday_limit_up_count)
    if any(value < 0 for value in values):
        raise ValueError("emotion counts must be non-negative")

    attempts = limit_up_count + broken_board_count
    seal_rate = _ratio(limit_up_count, attempts)
    break_rate = _ratio(broken_board_count, attempts)
    promotion_rate = _ratio(today_lianban_count, yesterday_limit_up_count)
    return ShortTermEmotionRates(
        seal_rate=seal_rate,
        break_rate=break_rate,
        promotion_rate=promotion_rate,
    )


def aggregate_shenwan_level2(
    *,
    stocks: Sequence[AShareTurnoverStock],
    memberships: Sequence[ShenwanMembership],
    threshold_yuan: Decimal,
    top_n: int = 10,
) -> AShareResearchAggregation:
    if threshold_yuan <= 0:
        raise ValueError("turnover threshold must be positive")
    if top_n <= 0:
        raise ValueError("top_n must be positive")

    membership_by_code = {item.security_code: item for item in memberships}
    market_turnover = sum((item.turnover_yuan for item in stocks), Decimal("0"))
    buckets: dict[str, _Sw2Bucket] = {}
    threshold_stocks: list[TurnoverThresholdStock] = []
    threshold_counts: dict[str, int] = defaultdict(int)
    unmatched: list[str] = []

    for stock in stocks:
        membership = membership_by_code.get(stock.security_code)
        if membership is None:
            unmatched.append(stock.security_code)
            continue

        bucket = buckets.setdefault(
            membership.sw_l2_code,
            _Sw2Bucket(membership=membership),
        )
        bucket.turnover_yuan += stock.turnover_yuan
        if stock.return_pct is not None and stock.turnover_yuan > 0:
            bucket.weighted_return_numerator += stock.return_pct * stock.turnover_yuan
            bucket.weighted_return_denominator += stock.turnover_yuan
        if stock.net_inflow_yuan is not None:
            bucket.net_inflow_yuan += stock.net_inflow_yuan
            bucket.has_net_inflow = True

        if stock.turnover_yuan > threshold_yuan:
            threshold_counts[membership.sw_l2_code] += 1
            threshold_stocks.append(
                TurnoverThresholdStock(
                    security_code=stock.security_code,
                    security_name=stock.security_name,
                    sw_l1_code=membership.sw_l1_code,
                    sw_l1_name=membership.sw_l1_name,
                    sw_l2_code=membership.sw_l2_code,
                    sw_l2_name=membership.sw_l2_name,
                    turnover_yuan=stock.turnover_yuan.quantize(MONEY_QUANT),
                    return_pct=stock.return_pct,
                )
            )

    sorted_buckets = sorted(
        buckets.values(),
        key=lambda item: (-item.turnover_yuan, item.membership.sw_l2_code),
    )
    sw2_all: list[ShenwanLevel2Aggregate] = []
    for rank, bucket in enumerate(sorted_buckets, start=1):
        weighted_return = None
        if bucket.weighted_return_denominator > 0:
            weighted_return = (
                bucket.weighted_return_numerator / bucket.weighted_return_denominator
            ).quantize(PCT_QUANT, rounding=ROUND_HALF_UP)
        market_share = Decimal("0")
        if market_turnover > 0:
            market_share = (bucket.turnover_yuan / market_turnover * Decimal("100")).quantize(
                PCT_QUANT,
                rounding=ROUND_HALF_UP,
            )
        sw2_all.append(
            ShenwanLevel2Aggregate(
                rank=rank,
                sw_l1_code=bucket.membership.sw_l1_code,
                sw_l1_name=bucket.membership.sw_l1_name,
                sw_l2_code=bucket.membership.sw_l2_code,
                sw_l2_name=bucket.membership.sw_l2_name,
                return_pct=weighted_return,
                turnover_yuan=bucket.turnover_yuan.quantize(MONEY_QUANT),
                market_share_pct=market_share,
                net_inflow_yuan=(
                    bucket.net_inflow_yuan.quantize(MONEY_QUANT)
                    if bucket.has_net_inflow
                    else None
                ),
            )
        )

    industries = [
        TurnoverThresholdIndustryCount(
            sw_l1_code=buckets[sw_l2_code].membership.sw_l1_code,
            sw_l1_name=buckets[sw_l2_code].membership.sw_l1_name,
            sw_l2_code=sw_l2_code,
            sw_l2_name=buckets[sw_l2_code].membership.sw_l2_name,
            stock_count=count,
        )
        for sw_l2_code, count in sorted(
            threshold_counts.items(),
            key=lambda item: (-item[1], buckets[item[0]].membership.sw_l2_name),
        )
    ]
    threshold_stocks.sort(
        key=lambda item: (-item.turnover_yuan, item.security_code),
    )
    unmatched_codes = sorted(set(unmatched))

    threshold_result = TurnoverThresholdResult(
        threshold_yuan=threshold_yuan,
        industries=industries,
        stocks=threshold_stocks,
        unmatched_security_codes=unmatched_codes,
    )
    return AShareResearchAggregation(
        sw2_top=sw2_all[:top_n],
        sw2_all=sw2_all,
        threshold=threshold_result,
        unmatched_security_codes=unmatched_codes,
    )


def _ratio(numerator: int, denominator: int) -> Decimal | None:
    if denominator <= 0:
        return None
    return (Decimal(numerator) / Decimal(denominator) * Decimal("100")).quantize(
        PCT_QUANT,
        rounding=ROUND_HALF_UP,
    )
