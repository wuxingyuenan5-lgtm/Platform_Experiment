"""Cashflow scenarios only; no execution, SQL or venue dependencies."""

from datetime import timedelta
from decimal import ROUND_CEILING, Decimal

from app.strategy_research_schemas import Scenario
from app.strategy_research_series import exact_math

ZERO = Decimal("0")


@exact_math
def borrow_cash(profile, opened, closed):
    if profile.product == "self_funded":
        return ZERO, []
    if profile.hourlyRate is None or profile.effectiveFrom is None or profile.observedAt is None:
        return None, ["borrow_rate_unknown"]
    if profile.effectiveFrom > opened or profile.observedAt > opened:
        return None, ["borrow_rate_not_visible_at_entry"]
    balance = profile.principal
    boundary = opened.replace(minute=5, second=0, microsecond=0)
    if boundary <= opened:
        boundary += timedelta(hours=1)
    cost = ZERO
    if profile.liabilityType == "spot":
        minutes = (Decimal(str((boundary - opened).total_seconds())) / 60).to_integral_value(
            rounding=ROUND_CEILING
        )
        initial = balance * profile.hourlyRate * minutes / 60
        cost += initial
        balance += initial  # explicit unpaid-interest capitalization scenario
    while boundary < closed:
        interest = balance * profile.hourlyRate
        balance += interest
        cost += interest
        boundary += timedelta(hours=1)
    return -cost, ["constant_hourly_rate_and_unpaid_interest_scenario"]


@exact_math
def scenario(request: Scenario):
    q = request.quantity
    buy = request.direction == "buy_spread"
    price = q * (request.exitSpread - request.entrySpread) * (1 if buy else -1)
    warnings = ["touch_is_not_fill", "scenario_not_realized_performance"]
    if request.fxAssumption == "explicit_1_to_1":
        warnings.append("USD_USDT_1_to_1_assumption_not_observed_cash_fx")
    settled, indicative, low, high = ZERO, ZERO, ZERO, ZERO
    known = request.fundingCoverage != "unknown"
    normalized = []
    identities = {}
    for event in request.funding:
        if (
            not request.openedAt - timedelta(seconds=5)
            <= event.at
            <= request.closedAt + timedelta(seconds=5)
        ):
            continue
        key = event.at.isoformat()
        content = (event.rate, event.mark, event.kind)
        if key in identities:
            if identities[key] != content:
                known = False
                warnings.append("funding_revision_conflict")
            continue
        identities[key] = content
        if event.kind != "settled" and event.observedAt > request.openedAt:
            known = False
            warnings.append("future_indication_excluded")
            continue
        boundary = (
            min(
                abs((event.at - request.openedAt).total_seconds()),
                abs((event.at - request.closedAt).total_seconds()),
            )
            <= 5
        )
        if not boundary and not request.openedAt < event.at <= request.closedAt:
            continue
        normalized.append({"at": key, "rate": str(event.rate), "kind": event.kind})
        if event.mark is None:
            known = False
            warnings.append("settlement_mark_unknown_normalized_rate_only")
            continue
        cash = q * event.mark * event.rate * (-1 if buy else 1)
        if event.markQuality != "exact":
            warnings.append("funding_mark_estimated_or_scenario")
        if boundary:
            low += min(ZERO, cash)
            high += max(ZERO, cash)
            warnings.append("funding_5s_boundary_inclusion_uncertain")
        else:
            low += cash
            high += cash
        if event.kind == "settled":
            settled += cash
        else:
            indicative += cash
    funding = low if known and low == high else None
    borrow, borrow_warnings = borrow_cash(request.borrow, request.openedAt, request.closedAt)
    warnings.extend(borrow_warnings)
    swap = ZERO if request.swapCoverage in ("complete", "scenario", "not_applicable") else None
    if request.pairId == "cross-gold" and request.swapCoverage == "not_applicable":
        swap = None
        warnings.append("MT5_swap_coverage_required")
    for event in request.swap:
        if not request.openedAt < event.at <= request.closedAt:
            continue
        if event.effectiveFrom > event.at:
            swap = None
            warnings.append("swap_not_effective")
            break
        # A buy spread sells the MT5/right leg.
        rate = event.shortRate if buy else event.longRate
        if (
            rate is None
            or event.mode == "unsupported"
            or (event.mode == "points" and event.point is None)
        ):
            swap = None
            warnings.append("swap_units_or_mode_unknown")
            break
        cash = q / event.contractSize * rate * event.rolloverMultiplier
        if event.mode == "points":
            assert event.point is not None
            cash *= event.point * event.contractSize
        if swap is not None:
            swap += cash
    components = {
        "pricePnl": price,
        "fundingCash": funding,
        "settledFundingCash": settled if known else None,
        "indicativeFundingCash": indicative if known else None,
        "borrowCash": borrow,
        "swapCash": swap,
        "tradingFees": request.tradingFees,
        "additionalExecutionCost": request.additionalExecutionCost,
    }
    net = None
    breakeven = None
    net_range = None
    if all(
        v is not None for v in (borrow, swap, request.tradingFees, request.additionalExecutionCost)
    ):
        assert borrow is not None and swap is not None
        assert request.tradingFees is not None and request.additionalExecutionCost is not None
        other = borrow + swap - request.tradingFees - request.additionalExecutionCost
        if known:
            net_range = [str(price + other + low), str(price + other + high)]
        if funding is not None:
            net = price + funding + other
            breakeven = request.entrySpread - (funding + other) / q * (1 if buy else -1)
    else:
        warnings.append("cost_coverage_incomplete")
    return {
        **{k: str(v) if v is not None else None for k, v in components.items()},
        "netPnl": str(net) if net is not None else None,
        "netPnlRange": net_range,
        "breakEvenExitSpread": str(breakeven) if breakeven is not None else None,
        "returnOnOwnCapital": str(net / request.ownCapital)
        if net is not None and request.ownCapital is not None
        else None,
        "fundingRates": normalized,
        "currency": request.currency,
        "economicUnit": "oz" if request.pairId == "cross-gold" else "BTC",
        "status": "scenario" if net is not None else "incomplete",
        "warnings": sorted(set(warnings)),
        "methodVersion": "cashflow.v1",
    }


@exact_math
def matched_quantity(gross, base_fee_rate, multiplier, step):
    if min(gross, multiplier, step) <= 0 or not ZERO <= base_fee_rate < 1:
        raise ValueError("quantity/specification invalid")
    from app.strategies.adapters.funding_carry import funding_open_quantities

    net, matched, residual = funding_open_quantities(
        gross, fee_rate=base_fee_rate, perpetual_step=step * multiplier
    )
    if net != gross * (1 - base_fee_rate):
        raise ValueError("existing sizing precision exceeded; no silent research rounding")
    contracts = matched / multiplier

    return {
        "netBase": str(net),
        "contracts": str(contracts),
        "matched": str(matched),
        "residual": str(residual),
    }


@exact_math
def vwap(levels, quantity):
    remaining, value = quantity, ZERO
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    for price, size in levels:
        p, s = Decimal(price), Decimal(size)
        if not p.is_finite() or not s.is_finite() or p <= 0 or s < 0:
            return None
        take = min(remaining, s)
        value += take * p
        remaining -= take
        if remaining == 0:
            return value / quantity
    return None
