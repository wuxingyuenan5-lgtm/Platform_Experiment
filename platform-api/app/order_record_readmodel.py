"""Read-only intent and clock provenance for management records."""

import json
from datetime import datetime, timedelta
from decimal import Decimal

from app.strategy_financial_readmodel import canonical_fills
from app.venue_identity_repository import load_order_execution_links, load_order_identities


def mt5_entry_action(payload):
    # MetaTrader5 DEAL_ENTRY_IN / OUT / INOUT / OUT_BY, not buy/sell direction.
    entry = payload.get("entryType")
    if isinstance(entry, bool):
        return None
    return {0: "open", 1: "close", 2: "reverse", 3: "close"}.get(entry)


def order_record_links(db, *, accounts, identities=None):
    links = load_order_execution_links(db)
    batches = {
        row["id"]: dict(row)
        for row in db.execute(
            "SELECT b.id,b.direction,r.action FROM execution_batches b "
            "LEFT JOIN strategy_runs r ON r.id=b.strategy_instruction_id"
        )
    }
    risk_orders = set()
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='execution_risk_actions'").fetchone():
        risk_orders = {
            row[0]
            for row in db.execute(
                "SELECT j.value FROM execution_risk_actions a,"
                "json_each(a.generated_order_ids_json) j "
                "UNION SELECT o.id FROM execution_risk_actions a JOIN trade_commands c "
                "ON c.idempotency_key=a.idempotency_key || ':replacement' "
                "JOIN orders o ON o.command_id=c.id "
                "UNION SELECT o.id FROM execution_risk_actions a "
                "JOIN execution_batch_legs l ON l.batch_id=a.batch_id "
                "JOIN trade_commands c ON c.idempotency_key=a.idempotency_key || ':' || l.role "
                "JOIN orders o ON o.command_id=c.id"
            )
        }
    for order_id, link in links.items():
        batch = batches[link["batchId"]]
        direction = batch["direction"]
        action = batch["action"]
        if not action:
            verb = direction.lower().split("_")[0]
            action = verb if verb in {"open", "close"} else None
        link.update(
            action="risk_reduction" if order_id in risk_orders else action,
            direction=direction,
        )
    for row in db.execute("SELECT id,venue_payload_json FROM orders"):
        venue = json.loads(row["venue_payload_json"] or "{}")
        if venue.get("reduceOnly") is True:
            links.setdefault(row["id"], {})["action"] = "close"
    if not accounts:
        return links
    identities = identities or load_order_identities(db)
    native_actions = {}
    for event in db.execute(
        "SELECT account_id,payload_json FROM venue_account_events "
        "WHERE event_type='trade_fill' AND source='mt5_live' "
        f"AND account_id IN ({','.join('?' for _ in accounts)})",
        sorted(accounts),
    ):
        payload = json.loads(event["payload_json"])
        owner = identities.resolve(event["account_id"], payload)
        if owner and links.get(owner, {}).get("action") in {None, "risk_reduction"}:
            native_actions.setdefault(owner, set()).add(mt5_entry_action(payload))
    for owner, actions in native_actions.items():
        if None not in actions:
            links.setdefault(owner, {})["action"] = (
                next(iter(actions)) if len(actions) == 1 else "reverse"
            )
    return links


def fill_clock_metadata(selected, operational, identities):
    """An aggregate order confirmation is never an individual deal timestamp.

    Only a confirmation covering all selected executions can bound their source
    clock. Never infer a broker offset, mutate source epochs, or use read time.
    """
    confirmations = {}
    for row in operational:
        owner = identities.canonical.get(row["order_id"])
        if owner == row["order_id"] and row["origin"] == "runtime_confirmation":
            confirmations.setdefault(owner, []).append(dict(row))
    totals = {}
    for row in selected:
        totals[row["order_id"]] = totals.get(row["order_id"], Decimal(0)) + Decimal(row["quantity"])
    clocks = {}
    for owner, rows in confirmations.items():
        rows = canonical_fills(rows)
        confirmed_quantity = sum((Decimal(row["quantity"]) for row in rows), Decimal(0))
        if confirmed_quantity >= totals.get(owner, Decimal(0)):
            clocks[owner] = max(datetime.fromisoformat(row["occurred_at"]) for row in rows)
    result = []
    for row in selected:
        confirmed = clocks.get(row["order_id"])
        source_time = datetime.fromisoformat(str(row["occurred_at"]).replace("Z", "+00:00"))
        native = row.get("native") or {}
        origin = "venue_execution" if native else row.get("origin", "legacy")
        source = native.get("source") or row.get("source") or ""
        quality = "venue_time" if origin == "venue_execution" else origin
        if (
            origin == "venue_execution"
            and confirmed
            and source_time > confirmed + timedelta(seconds=60)
        ):
            quality = "source_clock_conflict"
        elif origin == "venue_execution" and source == "mt5_live" and not confirmed:
            quality = "source_clock_unverified"
        result.append({"orderConfirmedAt": confirmed, "timeQuality": quality})
    return result
