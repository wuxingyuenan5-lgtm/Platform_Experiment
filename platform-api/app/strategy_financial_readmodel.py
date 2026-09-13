"""Read-only management projection from owned fills and immutable venue events.

Operational fills own execution quantities. Venue events own native fees and cash
settlements. Account-wide PnL is never assigned to a strategy by account binding.
This projection does not write accounting facts or manufacture historical FX.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.database import connection
from app.position_math import calculate_position_update
from app.schemas import (
    CrossSpreadAbnormalOrderResponse,
    CrossSpreadPositionOverviewResponse,
    CrossSpreadPositionPnlResponse,
    CrossSpreadSnapshotResponse,
    CrossSpreadUnattributedPositionResponse,
)
from app.strategies.domain import ExecutionPlan, ExecutionPlanLeg
from app.venue_identity_repository import (
    OrderIdentities,
    VenueIdentityConflict,
    canonical_operational_rows,
    load_order_execution_links,
    load_order_identities,
)
from app.venue_reconciliation_repository import effective_venue_event

ZERO = Decimal("0")
FIELDS = ("realizedPnl", "tradingPnl", "fees", "fundingPnl", "swapPnl")


def _amount(value: Any) -> Decimal:
    result = Decimal(str(value or "0"))
    if not result.is_finite():
        raise ValueError("Non-finite financial amount")
    return result


def _bucket(currency: str, account: str = "") -> dict[str, Any]:
    return {"currency": currency, "accountId": account, **dict.fromkeys(FIELDS, ZERO)}


def _finish(row: dict[str, Any]) -> dict[str, Any]:
    row["netPnl"] = (
        row["realizedPnl"] + row["tradingPnl"] - row["fees"] + row["fundingPnl"] + row["swapPnl"]
    )
    return {key: str(value) if isinstance(value, Decimal) else value for key, value in row.items()}


def position_notional(
    *,
    mark: dict[str, Any],
    quantity: Decimal,
    price: Decimal | None,
    multiplier: str | None,
) -> Decimal | None:
    """Position notional for one leg, in the instrument quote currency.

    The venue report wins while it still describes the projected quantity;
    otherwise the notional is rebuilt from mark price and contract multiplier so
    the value always matches the quantity this projection reports. A leg whose
    contract multiplier is unknown stays unvalued rather than guessed.
    """

    reported = mark.get("positionValue")
    if reported is not None:
        venue_quantity = mark.get("netQuantity")
        if venue_quantity is None or quantity == _amount(venue_quantity):
            return abs(_amount(reported))
    if price is None or multiplier is None:
        return None
    return abs(quantity * _amount(price) * _amount(multiplier))


def position_exposure(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """Gross and net position notional for one projection scope.

    Returns nulls when no leg carries a value, or when legs are valued in more
    than one currency. This projection never mixes currencies or invents FX.
    """

    gross = ZERO
    net = ZERO
    currency: str | None = None
    for position in positions:
        raw = position.get("positionValue")
        if raw is None:
            continue
        leg_currency = position.get("positionValueCurrency")
        if currency is None:
            currency = leg_currency
        elif leg_currency != currency:
            return _empty_exposure()
        amount = _amount(raw)
        sign = Decimal("-1") if _amount(position.get("netQuantity")) < 0 else Decimal("1")
        gross += amount
        net += amount * sign
    if currency is None:
        return _empty_exposure()
    return {
        "positionValue": str(gross),
        "positionValueNet": str(abs(net)),
        "positionValueCurrency": currency,
    }


def _empty_exposure() -> dict[str, Any]:
    return {"positionValue": None, "positionValueNet": None, "positionValueCurrency": None}


def canonical_fills(rows: list[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        grouped[row["order_id"]].append(row)
    result = []
    for order_rows in grouped.values():
        maximum = _amount(order_rows[0]["requested_quantity"])
        origins = {dict(row).get("origin", "legacy") for row in order_rows}
        if "legacy" not in origins:
            total = sum((_amount(row["quantity"]) for row in order_rows), ZERO)
            if (
                len(origins) != 1
                or total > maximum
                or any(_amount(row["quantity"]) <= ZERO for row in order_rows)
            ):
                raise VenueIdentityConflict(
                    "Operational fill provenance or quantity is inconsistent"
                )
            result.extend(dict(row) for row in order_rows)
            continue
        # Unclassified historical rows are never relabeled from their quantity.
        # Keep their former bounded projection until native receipts cover it.
        aggregate = next((row for row in order_rows if _amount(row["quantity"]) == maximum), None)
        accepted = ZERO
        for row in [aggregate] if aggregate is not None else order_rows:
            quantity = _amount(row["quantity"])
            if quantity > 0 and accepted + quantity <= maximum:
                result.append(dict(row))
                accepted += quantity
    return sorted(result, key=lambda row: (row["occurred_at"], row["fill_id"]))


def get_cross_spread_position_overview(
    snapshot: CrossSpreadSnapshotResponse,
    *,
    strategy_instance_id: str,
    bybit_account_id: str,
    mt5_account_id: str,
) -> CrossSpreadPositionOverviewResponse:
    """Value remaining logical groups; never allocate a shared net position's PnL.

    Called by the display GET only, outside the execution/exit-monitor hot path.
    The existing financial fill selector owns native/confirmation deduplication.
    """
    with connection() as db:
        db.execute("BEGIN")
        plans = db.execute(
            "SELECT p.*,s.execution_plan_json,EXISTS(SELECT 1 FROM audit_events a "
            "WHERE a.event_type='execution_batch_restored' AND a.subject_id=p.open_batch_id) "
            "AS incident_origin,EXISTS("
            "SELECT 1 FROM execution_batches b JOIN strategy_runs r ON r.execution_batch_id=b.id "
            "WHERE b.id=p.close_batch_id AND b.status='failed' AND r.status='rejected' "
            "AND r.strategy_instance_id=p.strategy_instance_id AND r.action='close' "
            "AND json_extract(r.requested_parameters_json,'$.mt5PositionId')=p.mt5_position_id "
            "AND 2=(SELECT COUNT(*) FROM execution_batch_legs l WHERE l.batch_id=b.id) "
            "AND NOT EXISTS(SELECT 1 FROM execution_batch_legs l LEFT JOIN trade_commands c "
            "ON c.idempotency_key=b.idempotency_key || ':' || l.role WHERE l.batch_id=b.id "
            "AND (l.order_id IS NOT NULL OR l.status!='pending' OR c.id IS NOT NULL))"
            ") AS close_unsubmitted FROM cross_spread_exit_plans p "
            "LEFT JOIN strategy_runs s ON s.execution_batch_id=p.open_batch_id "
            "AND s.strategy_instance_id=p.strategy_instance_id "
            "WHERE p.strategy_instance_id=? AND p.status IN ('active','manual_intervention') "
            "ORDER BY p.created_at DESC,p.id",
            (strategy_instance_id,),
        ).fetchall()
        batch_ids = [row["open_batch_id"] for row in plans]
        batch_ids += [row["close_batch_id"] for row in plans if row["close_batch_id"]]
        incomplete = db.execute(
            "SELECT b.* FROM execution_batches b JOIN strategy_runs s "
            "ON s.execution_batch_id=b.id WHERE b.strategy_instance_id=? "
            "AND s.action='open' AND b.status IN ('manual_intervention','failed') "
            "AND NOT EXISTS(SELECT 1 FROM execution_batch_risk r WHERE r.batch_id=b.id "
            "AND r.risk_status='resolved') "
            "AND EXISTS(SELECT 1 FROM execution_batch_legs l WHERE l.batch_id=b.id "
            "AND l.order_id IS NOT NULL)",
            (strategy_instance_id,),
        ).fetchall()
        batch_ids += [row["id"] for row in incomplete]
        batch_ids = list(set(batch_ids))
        placeholders = ",".join("?" for _ in batch_ids) or "NULL"
        batch_rows = {
            r["id"]: dict(r)
            for r in db.execute(
                f"SELECT * FROM execution_batches WHERE id IN ({placeholders})",
                batch_ids,
            )
        }
        leg_rows = [
            dict(r)
            for r in db.execute(
                "SELECT l.*,EXISTS(SELECT 1 FROM trade_commands c JOIN execution_batches b "
                "ON b.id=l.batch_id LEFT JOIN orders o ON o.command_id=c.id "
                "WHERE l.order_id IS NULL AND c.idempotency_key=b.idempotency_key || ':' || l.role "
                "AND (c.status!='rejected' OR o.id IS NOT NULL)) AS unlinked_command "
                f"FROM execution_batch_legs l WHERE l.batch_id IN ({placeholders})",
                batch_ids,
            )
        ]
        orders = db.execute(
            "SELECT o.*,l.batch_id,l.role,l.quantity AS leg_quantity,"
            "tc.strategy_instance_id FROM execution_batch_legs l "
            "JOIN orders o ON o.id=l.order_id JOIN trade_commands tc ON tc.id=o.command_id "
            f"WHERE l.batch_id IN ({placeholders})",
            batch_ids,
        ).fetchall()
        order_map = {row["id"]: dict(row) for row in orders}
        identities = load_order_identities(db)
        aliases = [key for key, owner in identities.canonical.items() if owner in order_map]
        placeholders = ",".join("?" for _ in aliases) or "NULL"
        fills = db.execute(
            "SELECT f.*,f.id AS fill_id,o.quantity AS requested_quantity FROM fills f "
            f"JOIN orders o ON o.id=f.order_id WHERE f.order_id IN ({placeholders})",
            aliases,
        ).fetchall()
        native_rows = _native_fills_for_orders(db, set(order_map))

    raw_fills: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in native_rows or []:
        raw_fills[row["id"]].append(json.loads(row["payload_json"]))
    fills_by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for order_id, order in order_map.items():
        try:
            executions, _ = select_management_executions(
                {order_id: order}, fills, raw_fills, identities
            )
            fills_by_order[order_id] = executions
        except (VenueIdentityConflict, ValueError, ArithmeticError):
            # This group's entry remains unavailable; other groups stay readable.
            fills_by_order[order_id] = []
    now = datetime.now(UTC)
    groups = [
        _cross_group_pnl(
            plan,
            orders=order_map,
            fills=fills_by_order,
            snapshot=snapshot,
            bybit_account_id=bybit_account_id,
            mt5_account_id=mt5_account_id,
            now=now,
        )
        for plan in plans
    ]
    abnormal, remaining_bybit = _cross_abnormal_orders(
        plans,
        incomplete,
        batch_rows,
        leg_rows,
        order_map,
        fills_by_order,
    )
    abnormal_plan_ids = {row.planId for row in abnormal}
    normal_groups = [group for group in groups if group.planId not in abnormal_plan_ids]

    def complete_sum(field: str) -> Decimal | None:
        values = [getattr(group, field) for group in normal_groups]
        return sum(values, ZERO) if all(value is not None for value in values) else None

    tickets = {plan["mt5_position_id"] for plan in plans}
    unattributed = [
        CrossSpreadUnattributedPositionResponse(venue="mt5", **position.model_dump(by_alias=True))
        for position in snapshot.mt5.positions
        if position.account_id == mt5_account_id
        and position.external_id not in tickets
        and position.quantity != ZERO
    ]
    if snapshot.bybit.status == "available" and all(
        position.account_id == bybit_account_id for position in snapshot.bybit.positions
    ):
        native_net = sum(
            (
                position.quantity
                for position in snapshot.bybit.positions
                if position.account_id == bybit_account_id
            ),
            ZERO,
        )
        group_net = sum(
            (
                remaining_bybit.get(plan["id"], Decimal(plan["quantity_oz"]))
                * (1 if plan["direction"] == "LONG_SPREAD" else -1)
                for plan in plans
            ),
            ZERO,
        )
        group_net += sum(
            (row.bybitRemainingQuantity or ZERO) * (1 if row.direction == "LONG_SPREAD" else -1)
            for row in abnormal
            if row.planId is None
        )
        difference = native_net - group_net
        if difference:
            unattributed.append(
                CrossSpreadUnattributedPositionResponse(
                    venue="bybit",
                    symbol=snapshot.bybit.symbol,
                    accountId=bybit_account_id,
                    side="buy" if difference > ZERO else "sell",
                    quantity=difference,
                    asOf=snapshot.bybit.as_of,
                )
            )
    return CrossSpreadPositionOverviewResponse(
        groups=groups,
        abnormalOrders=abnormal,
        unattributedPositions=unattributed,
        bybitPnlUsdt=complete_sum("bybitPnlUsdt"),
        mt5PnlUsdt=complete_sum("mt5PnlUsdt"),
        totalPnlUsdt=complete_sum("totalPnlUsdt"),
        dataQualityState=(
            "complete"
            if all(group.dataQualityState == "complete" for group in normal_groups)
            else "partial"
            if any(group.dataQualityState != "unavailable" for group in normal_groups)
            else "unavailable"
        ),
        asOf=snapshot.as_of,
    )


def _cross_abnormal_orders(plans, incomplete, batches, legs, orders, fills):
    """Project anomalies from the existing plan/batch/fill facts, without new state."""
    by_batch = defaultdict(dict)
    for leg in legs:
        by_batch[leg["batch_id"]][leg["role"]] = leg

    def filled(leg):
        if leg and leg.get("unlinked_command"):
            return None
        if leg is None or leg["order_id"] is None:
            return ZERO
        oid = leg["order_id"]
        if oid not in orders or (leg["status"] == "filled" and not fills.get(oid)):
            return None
        return sum((_amount(f["quantity"]) for f in fills.get(oid, [])), ZERO)

    result, remaining = [], {}
    for plan in plans:
        if plan["status"] != "manual_intervention" and not plan["incident_origin"]:
            continue
        close = batches.get(plan["close_batch_id"], {})
        close_legs = by_batch[plan["close_batch_id"]]
        bybit_leg, mt5_leg = close_legs.get("bybit_leg"), close_legs.get("mt5_leg")
        # A completed partial close is already reflected in plan.quantity_oz.
        bc = filled(bybit_leg) if plan["status"] == "manual_intervention" else ZERO
        mc = filled(mt5_leg) if plan["status"] == "manual_intervention" else ZERO
        opened = by_batch[plan["open_batch_id"]]
        by_open, mt_open = opened.get("bybit_leg"), opened.get("mt5_leg")
        multiplier = (
            _amount(by_open["quantity"]) / _amount(mt_open["quantity"])
            if by_open and mt_open and _amount(mt_open["quantity"]) > ZERO
            else None
        )
        br = max(ZERO, _amount(plan["quantity_oz"]) - bc) if bc is not None else None
        mr = (
            max(ZERO, _amount(plan["quantity_oz"]) / multiplier - mc)
            if multiplier and mc is not None
            else None
        )
        if br is not None:
            remaining[plan["id"]] = br
        partial = bc is not None and bc > ZERO and mc == ZERO
        action = "reconcile"
        if (
            partial
            and mt5_leg
            and mt5_leg["order_id"] is None
            and mt5_leg["status"] in {"failed", "blocked", "rejected"}
        ):
            action = "finish_mt5"
        elif (
            bc == ZERO
            and mc == ZERO
            and not any(leg["order_id"] is not None for leg in close_legs.values())
        ):
            action = "close_group"
        result.append(
            CrossSpreadAbnormalOrderResponse(
                batchId=plan["close_batch_id"] or plan["open_batch_id"],
                planId=plan["id"],
                label="平仓仅完成一腿"
                if partial
                else "误下双腿组合"
                if plan["incident_origin"]
                else "平仓受阻",
                direction=plan["direction"],
                bybitRemainingQuantity=br,
                mt5RemainingQuantity=mr,
                bybitCloseFilledQuantity=bc or ZERO,
                mt5CloseFilledQuantity=mc or ZERO,
                mt5PositionId=plan["mt5_position_id"],
                closeQuantityOz=bc if partial else plan["quantity_oz"],
                mt5PendingCloseQuantity=mt5_leg["quantity"] if partial and mt5_leg else None,
                recoveryIdempotencyKey=str(close.get("idempotency_key", "")).removeprefix(
                    "instruction:"
                )
                if partial
                else None,
                action=action,
                reason=close.get("failure_reason"),
            )
        )
    represented = {p["open_batch_id"] for p in plans}
    for batch in incomplete:
        if batch["id"] in represented:
            continue
        current = by_batch[batch["id"]]
        bybit, mt5 = current.get("bybit_leg"), current.get("mt5_leg")
        bq, mq = filled(bybit), filled(mt5)
        if bq == ZERO and mq == ZERO:
            continue
        result.append(
            CrossSpreadAbnormalOrderResponse(
                batchId=batch["id"],
                label="开仓异常 / 持仓待核对",
                direction="LONG_SPREAD" if bybit and bybit["side"] == "buy" else "SHORT_SPREAD",
                bybitRemainingQuantity=bq,
                mt5RemainingQuantity=mq,
                action=(
                    "flatten_open"
                    if bq is not None
                    and bq > ZERO
                    and mq == ZERO
                    and mt5
                    and mt5["order_id"] is None
                    and mt5["status"] in {"failed", "rejected", "blocked", "canceled", "pending"}
                    and bybit
                    and bybit["status"] == "filled"
                    else "reconcile"
                ),
                reason=batch["failure_reason"],
            )
        )
    return result, remaining


def _cross_group_pnl(
    plan: Any,
    *,
    orders: dict[str, Any],
    fills: dict[str, list[dict[str, Any]]],
    snapshot: CrossSpreadSnapshotResponse,
    bybit_account_id: str,
    mt5_account_id: str,
    now: datetime,
) -> CrossSpreadPositionPnlResponse:
    row = CrossSpreadPositionPnlResponse(
        planId=plan["id"],
        planUpdatedAt=plan["updated_at"],
        quantityOz=plan["quantity_oz"],
        direction=plan["direction"],
        mt5PositionId=plan["mt5_position_id"],
        openTime=plan["created_at"],
        dataQualityState="unavailable",
    )
    try:
        frozen = ExecutionPlan.model_validate_json(plan["execution_plan_json"] or "{}")
        legs = {leg.role: leg for leg in frozen.legs}
        bybit, mt5 = legs["bybit_leg"], legs["mt5_leg"]
        if (
            bybit.account_id != bybit_account_id
            or mt5.account_id != mt5_account_id
            or bybit.external_symbol.upper() != snapshot.bybit.symbol.upper()
            or mt5.external_symbol.upper() != snapshot.mt5.symbol.upper()
            or bybit.side != ("buy" if plan["direction"] == "LONG_SPREAD" else "sell")
            or mt5.side == bybit.side
            or row.quantityOz <= ZERO
            or row.quantityOz > bybit.maximum_quantity * bybit.contract_multiplier
            or bybit.maximum_quantity * bybit.contract_multiplier
            != mt5.maximum_quantity * mt5.contract_multiplier
        ):
            raise ValueError("Group identities or quantities do not match its opening plan")
        entries: dict[str, Decimal] = {}
        for leg in (bybit, mt5):
            owned_orders = [
                order
                for order in orders.values()
                if order["batch_id"] == plan["open_batch_id"] and order["role"] == leg.role
            ]
            if len(owned_orders) != 1:
                raise ValueError("Opening leg has no unique owned order")
            order = owned_orders[0]
            if (
                order["strategy_instance_id"] != plan["strategy_instance_id"]
                or order["account_id"] != leg.account_id
                or order["instrument_id"] != leg.instrument_id
                or order["side"] != leg.side
                or _amount(order["quantity"]) != leg.maximum_quantity
                or _amount(order["leg_quantity"]) != leg.maximum_quantity
            ):
                raise ValueError("Opening order identity differs from the plan")
            entries[leg.role] = _cross_entry_price(leg, fills.get(order["id"], []))
        row.bybitEntryPrice = entries["bybit_leg"]
        row.mt5EntryPrice = entries["mt5_leg"]
        row.bybitQuantity = row.quantityOz / bybit.contract_multiplier
        row.mt5Quantity = row.quantityOz / mt5.contract_multiplier
    except (KeyError, TypeError, ValueError, ArithmeticError):
        row.reason = "开仓成交记录不完整，请核对该组合"
        return row

    if plan["status"] != "active" and not plan["close_unsubmitted"]:
        row.reason = "持仓数量待核对"
        return row

    reasons = []
    quote = snapshot.bybit.quote
    if (
        snapshot.bybit.status == "available"
        and quote is not None
        and _cross_recent(snapshot.bybit.as_of, now)
        and quote.bid.is_finite()
        and quote.ask.is_finite()
        and ZERO < quote.bid <= quote.ask
    ):
        close_price = quote.bid if bybit.side == "buy" else quote.ask
        sign = Decimal(1) if bybit.side == "buy" else Decimal(-1)
        row.bybitPnlUsdt = _cross_pnl_usdt(
            sign * row.quantityOz * (close_price - entries["bybit_leg"]),
            quote.currency,
            snapshot.metrics.usdt_usd,
        )
    if row.bybitPnlUsdt is None:
        reasons.append("Bybit 报价或换汇数据暂不可用")

    positions = [
        position
        for position in snapshot.mt5.positions
        if position.external_id == plan["mt5_position_id"]
        and position.account_id == mt5_account_id
        and position.symbol.upper() == mt5.external_symbol.upper()
    ]
    position = positions[0] if len(positions) == 1 else None
    expected_quantity = row.quantityOz / mt5.contract_multiplier
    if mt5.side == "sell":
        expected_quantity = -expected_quantity
    if (
        snapshot.mt5.status == "available"
        and position is not None
        and position.quantity == expected_quantity
        and position.average_price == row.mt5EntryPrice
        and position.unrealized_pnl is not None
        and _cross_recent(position.as_of, now)
    ):
        row.mt5PnlUsdt = _cross_pnl_usdt(
            position.unrealized_pnl, position.currency, snapshot.metrics.usdt_usd
        )
    if row.mt5PnlUsdt is None:
        reasons.append("MT5 持仓数量、盈亏或换汇数据待核对")
    if row.bybitPnlUsdt is not None and row.mt5PnlUsdt is not None:
        row.totalPnlUsdt = row.bybitPnlUsdt + row.mt5PnlUsdt
        row.dataQualityState = "complete"
    elif row.bybitPnlUsdt is not None or row.mt5PnlUsdt is not None:
        row.dataQualityState = "partial"
    row.reason = "；".join(reasons) or None
    return row


def _cross_entry_price(leg: ExecutionPlanLeg, fills: list[dict[str, Any]]) -> Decimal:
    quantity = ZERO
    notional = ZERO
    for fill in fills:
        size, price = _amount(fill["quantity"]), _amount(fill["price"])
        if (
            fill["account_id"] != leg.account_id
            or fill["instrument_id"] != leg.instrument_id
            or fill["side"] != leg.side
            or size <= ZERO
            or price <= ZERO
        ):
            raise ValueError("Opening fill identity or amounts are inconsistent")
        quantity += size
        notional += size * price
    if quantity != leg.maximum_quantity:
        raise ValueError("Opening fills do not exactly cover the planned quantity")
    return notional / quantity


def _cross_recent(as_of: datetime | None, now: datetime) -> bool:
    return (
        as_of is not None and as_of.tzinfo is not None and -5 <= (now - as_of).total_seconds() <= 30
    )


def _cross_pnl_usdt(
    value: Decimal, currency: str | None, usdt_usd: Decimal | None
) -> Decimal | None:
    if not value.is_finite():
        return None
    if currency == "USDT":
        return value
    if currency == "USD" and usdt_usd is not None and usdt_usd.is_finite() and usdt_usd > ZERO:
        return value / usdt_usd
    return None


def select_management_executions(
    order_map: dict[str, Any],
    fill_rows: list[Any],
    raw_fills: dict[str, list[dict[str, Any]]],
    identities: OrderIdentities,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Choose native executions or their confirmation, never add both together."""
    operational: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in canonical_operational_rows(
        [row for row in fill_rows if identities.canonical.get(row["order_id"]) in order_map],
        identities,
    ):
        operational[row["order_id"]].append(row)
    enriched = []
    issues: set[str] = set()
    for order_id, order in order_map.items():
        candidates = operational.get(order_id, [])
        owned = identities.rows[order_id]["strategy_instance_id"]
        # An external monitor order synthesized from its first fill has no
        # business quantity ceiling. Its native executions retain their full sum.
        confirmed = (
            candidates
            if not owned and all(row.get("origin") == "venue_execution" for row in candidates)
            else canonical_fills(candidates)
        )
        confirmed_quantity = sum((_amount(row["quantity"]) for row in confirmed), ZERO)
        raw = raw_fills.get(order_id, [])
        raw_total = sum((_amount(fill["quantity"]) for fill in raw), ZERO)
        if raw and raw_total >= confirmed_quantity:
            if raw_total > _amount(order["quantity"]) and owned:
                issues.add("venue_fill_quantity_exceeds_order")
            for fill in raw:
                enriched.append(
                    {
                        "order_id": order_id,
                        "account_id": order["account_id"],
                        "instrument_id": order["instrument_id"],
                        "side": fill["side"],
                        "quantity": fill["quantity"],
                        "price": fill["price"],
                        "occurred_at": fill["occurredAt"],
                        "native": fill,
                    }
                )
        else:
            enriched.extend({**row, "order_id": order_id} for row in confirmed)
            if any(row.get("origin", "legacy") == "legacy" for row in confirmed):
                issues.add("legacy_fill_provenance_pending")
            if raw or confirmed:
                issues.add("fill_details_pending")

    return enriched, issues


def get_strategy_financials(
    strategy_instance_id: str, *, account_id: str | None = None, account_scope: bool = False
) -> dict[str, Any]:
    with connection() as db:
        instance = db.execute(
            "SELECT base_currency FROM strategy_instances WHERE id=?", (strategy_instance_id,)
        ).fetchone()
        base_currency = str(instance["base_currency"])
        where = "o.account_id=?" if account_scope else "tc.strategy_instance_id=?"
        params: list[Any] = [account_id if account_scope else strategy_instance_id]
        if account_id and not account_scope:
            where += " AND o.account_id=?"
            params.append(account_id)
        orders = db.execute(
            "SELECT o.*, i.settle_currency, i.instrument_type, "
            "i.base_currency AS base_asset, i.quote_currency, "
            "COALESCE(cs.contract_multiplier,'1') AS multiplier "
            "FROM orders o LEFT JOIN trade_commands tc ON tc.id=o.command_id "
            "LEFT JOIN instruments i ON i.id=o.instrument_id "
            "LEFT JOIN contract_specifications cs ON cs.instrument_id=i.id WHERE " + where,
            params,
        ).fetchall()
        accounts = (
            [account_id]
            if account_id
            else [
                row[0]
                for row in db.execute(
                    "SELECT DISTINCT account_id FROM strategy_account_bindings "
                    "WHERE strategy_instance_id=? AND status='active' AND role!='local_test'",
                    (strategy_instance_id,),
                )
            ]
        )
        accounts = sorted(set(accounts) | {row["account_id"] for row in orders})
        placeholders = ",".join("?" for _ in accounts) or "NULL"
        fill_rows = db.execute(
            "SELECT f.*, f.id AS fill_id, o.quantity AS requested_quantity "
            "FROM fills f JOIN orders o ON o.id=f.order_id "
            f"WHERE o.account_id IN ({placeholders}) ORDER BY f.occurred_at,f.id",
            accounts,
        ).fetchall()
        events = db.execute(
            f"SELECT * FROM venue_account_events WHERE account_id IN ({placeholders}) "
            "ORDER BY occurred_at,external_id",
            accounts,
        ).fetchall()
        events = [
            {
                **dict(event),
                "payload_json": json.dumps(
                    effective_venue_event(
                        db,
                        event["account_id"],
                        event["event_type"],
                        json.loads(event["payload_json"]),
                    )
                ),
            }
            for event in events
        ]
        snapshots = db.execute(
            f"SELECT * FROM account_venue_snapshots WHERE account_id IN ({placeholders})",
            accounts,
        ).fetchall()
        identities = load_order_identities(db)
        assignments: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
        for row in db.execute(
            "SELECT account_id, instrument_id, source, external_id, fact_type, "
            "strategy_instance_id, payload_json FROM financial_facts"
        ):
            assignments[(
                row["account_id"],
                identities.instrument(row["account_id"], row["instrument_id"]),
                row["source"],
                row["external_id"],
                row["fact_type"],
            )].append(dict(row))
        execution_links = load_order_execution_links(db)

    mt5_currencies = {
        row["account_id"]: payload.get("accountRisk", {}).get("currency")
        for row in snapshots
        if (payload := json.loads(row["payload_json"])).get("venue") == "mt5"
    }
    orders = [dict(row) for row in orders if identities.canonical[row["id"]] == row["id"]]
    for order in orders:
        if order["account_id"] in mt5_currencies and mt5_currencies[order["account_id"]]:
            # MT5 profits settle in the account's reported currency. XAUUSD in
            # the instrument name does not turn a USDT cash account into USD.
            order["settle_currency"] = mt5_currencies[order["account_id"]]
    order_map = {row["id"]: row for row in orders}
    components: dict[tuple[str, str], dict[str, Any]] = {}
    issues: set[str] = set()
    positions: dict[tuple[str, str, str], tuple[Decimal, Decimal | None]] = {}
    timeline = []
    raw_fills: dict[str, list[dict[str, Any]]] = defaultdict(list)
    economic = []
    unattributed = []
    unassigned_candidates = []
    settlement_links: dict[str, dict[str, str]] = {}

    def component(account: str, currency: str) -> dict[str, Any]:
        key = (account, currency)
        if key not in components:
            components[key] = _bucket(currency, account)
        return components[key]

    for event in events:
        payload = json.loads(event["payload_json"])
        try:
            order_id = identities.resolve(event["account_id"], payload)
        except VenueIdentityConflict:
            issues.add("venue_order_identity_conflict")
            continue
        if event["event_type"] == "trade_fill":
            if account_scope or order_id in order_map:
                raw_fills[str(order_id)].append(payload)
            continue
        assignments_for_event = assignments.get((
            event["account_id"],
            identities.instrument(event["account_id"], event["instrument_id"]),
            event["source"],
            event["external_id"],
            event["event_type"],
        ), [])
        assigned_owners = {row["strategy_instance_id"] for row in assignments_for_event}
        explicit = assigned_owners == {strategy_instance_id}
        owner = identities.rows[order_id]["strategy_instance_id"] if order_id else None
        if not account_scope and owner and owner != strategy_instance_id:
            continue
        if not account_scope and assigned_owners and strategy_instance_id not in assigned_owners:
            continue
        if not account_scope and len(assigned_owners) > 1:
            issues.add("conflicting_settlement_ownership")
            unassigned_candidates.append(payload)
            continue
        if explicit:
            assignment = json.loads(assignments_for_event[0]["payload_json"])
            settlement_links[event["external_id"]] = {
                key: assignment[key] for key in ("batchId", "instructionId") if assignment.get(key)
            }
        if account_scope or order_id in order_map or explicit:
            economic.append((event, payload, order_id))
        elif orders and event["event_type"] in {"funding", "swap"}:
            unassigned_candidates.append(payload)

    enriched, execution_issues = select_management_executions(
        order_map, fill_rows, raw_fills, identities
    )
    issues.update(execution_issues)

    for event in unassigned_candidates:
        # An unrelated symbol or settlement before/after this strategy's native
        # exposure must not invalidate its funding totals merely by account.
        at = datetime.fromisoformat(event["occurredAt"].replace("Z", "+00:00"))
        exposure = sum(
            (
                _amount(fill["quantity"]) * (1 if fill["side"] == "buy" else -1)
                for fill in enriched
                if fill["account_id"] == event["accountId"]
                and fill["instrument_id"] == identities.instrument(
                    event["accountId"], event.get("instrumentId")
                )
                and datetime.fromisoformat(fill["occurred_at"].replace("Z", "+00:00")) <= at
            ), ZERO,
        )
        if exposure:
            unattributed.append(event)

    for row in sorted(enriched, key=lambda value: value["occurred_at"]):
        order = order_map[row["order_id"]]
        account, instrument = row["account_id"], row["instrument_id"]
        native = row.get("native", {})
        if order["settle_currency"] is None:
            # Monitor-only symbols need no trading specification. Keep their native
            # fees/realized receipts; never invent a multiplier or opening cost.
            if native.get("realizedPnl") is not None and native.get("currency"):
                currency = str(native["currency"])
                realized = _amount(native["realizedPnl"])
                component(account, currency)["realizedPnl"] += realized
                timeline.append(
                    {
                        "asOf": row["occurred_at"],
                        "accountId": account,
                        "currency": currency,
                        "realizedPnl": str(realized),
                    }
                )
            else:
                issues.add("opening_cost_basis_unavailable")
            continue
        currency = order["settle_currency"]
        bucket = component(account, currency)
        quantity = _amount(row["quantity"])
        position_id = str(native.get("positionId") or "")
        old, average = positions.get((account, instrument, position_id), (ZERO, None))
        new, average, realized = calculate_position_update(
            old_quantity=old,
            old_average=average,
            signed_fill=quantity if row["side"] == "buy" else -quantity,
            fill_price=_amount(row["price"]),
        )
        positions[account, instrument, position_id] = (new, average)
        if native.get("realizedPnl") is not None:
            realized = _amount(native["realizedPnl"])
        elif account_scope or (
            order["instrument_type"] == "mt5_cfd" and currency != order["quote_currency"]
        ):
            # A bounded account history cannot establish the opening cost basis.
            realized = ZERO
            if order["instrument_type"] == "crypto_spot" or not any(
                event["event_type"] == "realized_pnl" for event, _, _ in economic
            ):
                issues.add("opening_cost_basis_unavailable")
        else:
            realized *= _amount(order["multiplier"])
        bucket["realizedPnl"] += realized
        timeline.append(
            {
                "asOf": row["occurred_at"],
                "accountId": account,
                "currency": currency,
                "realizedPnl": str(realized),
            }
        )

    # Fees come from executions whenever available. Transaction-log fee/swap
    # records for those same deals are retained for audit, but never added twice.
    for order_id, fills in raw_fills.items():
        order = order_map.get(order_id)
        for fill in fills:
            account, currency = fill["accountId"], str(fill.get("currency") or "UNKNOWN")
            if fill.get("fee") is None:
                issues.add("fill_details_pending")
                continue
            fee = _amount(fill.get("fee"))
            if currency == "UNKNOWN":
                issues.add("fee_currency_unavailable")
            component(account, currency)["fees"] += fee
            if fill.get("swap") is not None:
                settlement = (order["settle_currency"] if order else None) or currency
                component(account, settlement)["swapPnl"] += _amount(fill["swap"])
    for event, _payload, order_id in economic:
        kind = event["event_type"]
        if kind in {"fee", "swap"} and raw_fills.get(str(order_id)):
            continue
        if kind == "realized_pnl" and not account_scope:
            continue  # Strategy cost basis above already recognizes realized PnL.
        if kind == "realized_pnl" and any(
            fill.get("realizedPnl") is not None for fill in raw_fills.get(str(order_id), [])
        ):
            continue
        field = {
            "fee": "fees",
            "funding": "fundingPnl",
            "swap": "swapPnl",
            "realized_pnl": "realizedPnl",
        }.get(kind)
        if field:
            component(event["account_id"], event["currency"])[field] += (
                -_amount(event["amount"]) if kind == "fee" else _amount(event["amount"])
            )
            if kind == "realized_pnl":
                timeline.append(
                    {
                        "asOf": event["occurred_at"],
                        "accountId": event["account_id"],
                        "currency": event["currency"],
                        "realizedPnl": str(event["amount"]),
                    }
                )

    mark_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    coins_by_account: dict[str, dict[str, Any]] = {}
    missing_marks: set[tuple[str, str]] = set()
    coverage = []
    for snapshot in snapshots:
        payload = json.loads(snapshot["payload_json"])
        age = (
            datetime.now(UTC) - datetime.fromisoformat(snapshot["as_of"].replace("Z", "+00:00"))
        ).total_seconds()
        if age > 90:
            issues.add("stale_account_snapshot")
        if payload.get("economicEventsQuality") != "complete":
            issues.add("economic_events_pending")
        coverage.append(
            {
                "accountId": snapshot["account_id"],
                "historyStart": payload.get("historyStart"),
                "historyEnd": payload.get("historyEnd"),
                "asOf": snapshot["as_of"],
            }
        )
        coins_by_account[snapshot["account_id"]] = {
            row["currency"]: row for row in payload.get("balances", [])
        }
        for position in payload.get("positions", []):
            position_id = (
                str(position.get("externalPositionId") or "")
                if payload.get("venue") == "mt5"
                else ""
            )
            key = snapshot["account_id"], position["instrumentId"], position_id
            mark_rows[key] = position
            if account_scope and position.get("unrealizedPnl") is not None:
                component(key[0], str(position.get("currency") or base_currency))["tradingPnl"] += (
                    _amount(position["unrealizedPnl"])
                )

    projected_positions = []
    for (account, instrument, position_id), (quantity, average) in positions.items():
        if quantity == 0:
            continue
        order = next(
            row
            for row in orders
            if row["account_id"] == account and row["instrument_id"] == instrument
        )
        mark = mark_rows.get((account, instrument, position_id), {})
        price = mark.get("markPrice") or mark.get("currentPrice")
        if price is None and order["instrument_type"] == "crypto_spot":
            coins = coins_by_account.get(account, {})
            base = coins.get(order["base_asset"], {})
            quote = coins.get(order["quote_currency"], {})
            if all(
                _amount(row.get("equity")) > 0 and _amount(row.get("usdValue")) > 0
                for row in (base, quote)
            ):
                price = (_amount(base["usdValue"]) / _amount(base["equity"])) / (
                    _amount(quote["usdValue"]) / _amount(quote["equity"])
                )
        unrealized = None
        currency_differs = (
            order["instrument_type"] == "mt5_cfd"
            and order["settle_currency"] != order["quote_currency"]
        )
        if (
            mark.get("unrealizedPnl") is not None
            and position_id
            and quantity == _amount(mark.get("netQuantity"))
        ):
            unrealized = _amount(mark["unrealizedPnl"])
        elif price is not None and average is not None and not currency_differs:
            unrealized = quantity * (_amount(price) - average) * _amount(order["multiplier"])
        if unrealized is not None and not account_scope:
            component(account, order["settle_currency"])["tradingPnl"] += unrealized
        elif unrealized is None and not account_scope:
            issues.add("mark_price_unavailable")
            missing_marks.add((account, order["settle_currency"]))
        position_value = position_notional(
            mark=mark,
            quantity=quantity,
            price=price,
            multiplier=order["multiplier"],
        )
        projected_positions.append(
            {
                "accountId": account,
                "instrumentId": instrument,
                "externalPositionId": position_id or None,
                "symbol": order["symbol"],
                "currentPrice": str(price) if price is not None else None,
                "netQuantity": str(quantity),
                "averagePrice": str(average) if average is not None else None,
                "unrealizedPnl": str(unrealized) if unrealized is not None else None,
                "currency": order["settle_currency"],
                "positionValue": str(position_value) if position_value is not None else None,
                "positionValueCurrency": (
                    order["quote_currency"] if position_value is not None else None
                ),
            }
        )

    by_currency: dict[str, dict[str, Any]] = {}
    for (_, currency), row in components.items():
        aggregate = by_currency.setdefault(currency, _bucket(currency))
        for field in FIELDS:
            aggregate[field] += row[field]
    nonzero_foreign = any(
        currency != base_currency and any(row[field] != 0 for field in FIELDS)
        for currency, row in by_currency.items()
    )
    if nonzero_foreign:
        issues.add("historical_fx_unavailable")
    if account_scope and len(by_currency) == 1:
        base_currency = next(iter(by_currency))
        nonzero_foreign = False
        issues.discard("historical_fx_unavailable")
    totals = _finish(by_currency.get(base_currency, _bucket(base_currency)))
    if not orders and not snapshots:
        issues.add("waiting_initial_sync")
        totals.update(dict.fromkeys((*FIELDS, "netPnl")))
    if nonzero_foreign:
        for field in FIELDS:
            if any(
                currency != base_currency and row[field] != 0
                for currency, row in by_currency.items()
            ):
                totals[field] = None
        totals["netPnl"] = None
    if "mark_price_unavailable" in issues:
        totals.update(tradingPnl=None, netPnl=None)
    if unattributed:
        issues.add("unattributed_economic_events")
        if any(row.get("eventType") == "funding" for row in unattributed):
            totals.update(fundingPnl=None, netPnl=None)
        if any(row.get("eventType") == "swap" for row in unattributed):
            totals.update(swapPnl=None, netPnl=None)
    if "opening_cost_basis_unavailable" in issues:
        totals.update(realizedPnl=None, netPnl=None)
    by_account = [_finish(row) for row in components.values()]
    currency_rows = [_finish(row) for row in by_currency.values()]
    for row in by_account:
        if (row["accountId"], row["currency"]) in missing_marks:
            row.update(tradingPnl=None, netPnl=None)
    for row in currency_rows:
        if any(currency == row["currency"] for _, currency in missing_marks):
            row.update(tradingPnl=None, netPnl=None)
    for row in [totals, *by_account, *currency_rows]:
        if "venue_order_identity_conflict" in issues:
            row.update(realizedPnl=None, fees=None, fundingPnl=None, swapPnl=None, netPnl=None)
        if "fill_details_pending" in issues or "fee_currency_unavailable" in issues:
            row.update(fees=None, netPnl=None)
        if "economic_events_pending" in issues:
            row.update(fundingPnl=None, swapPnl=None, netPnl=None)
        if "opening_cost_basis_unavailable" in issues:
            row.update(realizedPnl=None, netPnl=None)
        if unattributed:
            if any(event.get("eventType") == "funding" for event in unattributed):
                row.update(fundingPnl=None, netPnl=None)
            if any(event.get("eventType") == "swap" for event in unattributed):
                row.update(swapPnl=None, netPnl=None)
    cumulative: dict[str, Decimal] = defaultdict(lambda: ZERO)
    timeline.sort(key=lambda row: row["asOf"])
    for point in timeline:
        cumulative[point["currency"]] += _amount(point["realizedPnl"])
        point["realizedPnl"] = str(cumulative[point["currency"]])
    if "opening_cost_basis_unavailable" in issues:
        timeline = []
    return {
        **totals,
        "strategyInstanceId": strategy_instance_id,
        "dataQualityState": "partial" if issues else "complete",
        "issues": sorted(issues),
        "byCurrency": currency_rows,
        "byAccount": by_account,
        "positions": projected_positions,
        "exposure": position_exposure(projected_positions),
        "timeline": timeline[-1000:],
        "coverage": coverage,
        "unattributedEvents": unattributed[-200:],
        "economicEvents": [
            {
                **payload,
                "orderId": order_id,
                "externalOrderId": identities.rows[order_id]["external_order_id"]
                if order_id
                else payload.get("externalOrderId"),
                **execution_links.get(str(order_id), {}),
                **settlement_links.get(str(payload.get("externalEventId")), {}),
            }
            for _, payload, order_id in economic
        ][-200:],
        "scope": "account" if account_scope else "strategy",
    }


def _native_fills_for_orders(db, order_ids: set[str]) -> list[dict[str, Any]] | None:
    if not order_ids:
        return []
    placeholders = ",".join("?" for _ in order_ids)
    orders = {
        row["id"]: dict(row)
        for row in db.execute(
            "SELECT o.id,o.account_id,i.base_currency,i.quote_currency "
            "FROM orders o LEFT JOIN instruments i ON i.id=o.instrument_id "
            f"WHERE o.id IN ({placeholders})",
            list(order_ids),
        )
    }
    identities = load_order_identities(db)
    if any(identities.canonical.get(order_id) != order_id for order_id in order_ids):
        return None
    accounts = sorted({row["account_id"] for row in orders.values()})
    placeholders = ",".join("?" for _ in accounts) or "NULL"
    result = []
    for event in db.execute(
        "SELECT account_id,payload_json FROM venue_account_events "
        f"WHERE event_type='trade_fill' AND account_id IN ({placeholders})",
        accounts,
    ):
        try:
            payload = effective_venue_event(
                db, event["account_id"], "trade_fill", json.loads(event["payload_json"])
            )
            order_id = identities.resolve(event["account_id"], payload)
        except VenueIdentityConflict:
            return None
        if order_id in orders:
            result.append({**orders[order_id], "payload_json": json.dumps(payload)})
    return result


def batch_fee_totals(batch_id: str) -> tuple[Decimal | None, Decimal | None]:
    with connection() as db:
        order_ids = {
            order_id
            for order_id, link in load_order_execution_links(db).items()
            if link["batchId"] == batch_id
        }
        rows = _native_fills_for_orders(db, order_ids)
        facts = db.execute(
            "SELECT amount, currency FROM financial_facts WHERE fact_type='funding' "
            "AND json_extract(payload_json,'$.batchId')=?",
            (batch_id,),
        ).fetchall()
    if rows is None:
        return None, None
    fees = ZERO
    for row in rows:
        fill = json.loads(row["payload_json"])
        if fill.get("fee") is None:
            return None, None
        fee = _amount(fill.get("fee"))
        currency = str(fill.get("currency") or "")
        if currency == "USDT" or fee == 0:
            fees += fee
        elif str(fill.get("symbol") or "") == currency + "USDT":
            fees += fee * _amount(fill["price"])
        else:
            return None, None
    funding = (
        sum((_amount(row["amount"]) for row in facts), ZERO)
        if facts and all(row["currency"] == "USDT" for row in facts)
        else None
    )
    return funding, fees if rows or not order_ids else None


def funding_spot_cash(batch_id: str, gross_quantity: Decimal) -> Decimal | None:
    """Native assets actually acquired, after fees charged in the base coin."""
    with connection() as db:
        order_ids = {
            row[0]
            for row in db.execute(
                "SELECT order_id FROM funding_spot_release_commands WHERE batch_id=?",
                (batch_id,),
            )
            if row[0]
        }
        rows = _native_fills_for_orders(db, order_ids)
    if rows is None:
        return None
    observed = ZERO
    base_fees = ZERO
    for row in rows:
        fill = json.loads(row["payload_json"])
        observed += _amount(fill["quantity"])
        if fill.get("fee") is None:
            return None
        fee = _amount(fill.get("fee"))
        if fee and (
            fill.get("currency") in {None, "UNKNOWN"}
            or fill.get("feeCurrencyQuality") == "unavailable"
        ):
            return None
        if fill.get("currency") == row["base_currency"]:
            base_fees += fee
    if observed != gross_quantity or not rows:
        return None
    return max(ZERO, observed - base_fees)
