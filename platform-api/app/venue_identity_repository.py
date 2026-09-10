"""Exact venue identities shared by snapshot ingestion and management reads.

Legacy rows and raw receipts remain immutable. Aliases are resolved from the
account, instrument (including market category), and native order identity;
only a TradeCommand establishes strategy ownership.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any


class VenueIdentityConflict(ValueError):
    pass


def scoped_identity(kind: str, *parts: str) -> str:
    payload = json.dumps(parts, ensure_ascii=True, separators=(",", ":"))
    return f"venue-{kind}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


class OrderIdentities:
    def __init__(
        self,
        rows: Iterable[Any],
        instrument_aliases: Mapping[tuple[str, str], str | None] | None = None,
    ):
        self.instrument_aliases = instrument_aliases or {}
        self.rows = {
            str(row["id"]): {
                **dict(row),
                "instrument_id": self.instrument(row["account_id"], row["instrument_id"]),
            }
            for row in rows
        }
        grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in self.rows.values():
            if row.get("external_order_id"):
                grouped[self.key(row)].append(row)
        self.native: dict[tuple[str, str, str], str | None] = {}
        self.canonical: dict[str, str | None] = {identity: identity for identity in self.rows}
        for key, aliases in grouped.items():
            owned = [row for row in aliases if row.get("strategy_instance_id")]
            canonical = (
                None
                if len(owned) > 1
                else min(owned or aliases, key=lambda row: (row["created_at"], row["id"]))["id"]
            )
            self.native[key] = canonical
            for row in aliases:
                self.canonical[row["id"]] = canonical

    @staticmethod
    def key(row: Mapping[str, Any]) -> tuple[str, str, str]:
        return row["account_id"], row["instrument_id"], row["external_order_id"]

    def instrument(self, account_id: str, instrument_id: Any) -> Any:
        if str(instrument_id).startswith("monitor:bybit:") and not str(instrument_id).startswith(
            f"monitor:bybit:{account_id}:"
        ):
            raise VenueIdentityConflict("Monitoring instrument belongs to a different account")
        result = self.instrument_aliases.get((account_id, instrument_id), instrument_id)
        if result is None:
            raise VenueIdentityConflict("Monitoring instrument has multiple catalog mappings")
        return result

    def resolve(self, account_id: str, payload: Mapping[str, Any]) -> str | None:
        if payload.get("accountId", account_id) != account_id:
            raise VenueIdentityConflict("Venue receipt account identity mismatch")
        instrument = self.instrument(account_id, payload.get("instrumentId"))
        detail = payload.get("payload") or {}
        external = payload.get("externalOrderId") or detail.get("orderId")
        direct = self.rows.get(str(payload.get("platformOrderId") or ""))
        if direct is not None:
            if direct["account_id"] != account_id or (
                instrument and direct["instrument_id"] != instrument
            ):
                # Old external:<ticket> aliases were not globally scoped. They
                # cannot identify a different account's actual platform order.
                if direct.get("strategy_instance_id") or not direct["id"].startswith("external:"):
                    raise VenueIdentityConflict("Venue order identity conflicts with ownership")
                direct = None
            elif (
                external and direct["external_order_id"] and external != direct["external_order_id"]
            ):
                raise VenueIdentityConflict("Venue order identity conflicts with native order")
        if direct is not None:
            instrument = instrument or direct["instrument_id"]
            external = external or direct["external_order_id"]
        key = (account_id, str(instrument or ""), str(external or ""))
        if key in self.native:
            result = self.native[key]
            if result is None:
                raise VenueIdentityConflict("Native order has multiple command owners")
        else:
            result = self.canonical[direct["id"]] if direct else None
        if result and payload.get("side") and self.rows[result]["side"] != payload["side"]:
            raise VenueIdentityConflict("Venue order side conflicts with existing order")
        return result


def load_order_identities(db: sqlite3.Connection) -> OrderIdentities:
    aliases: dict[tuple[str, str], str | None] = {}
    for row in db.execute(
        "SELECT a.id AS account_id,i.id,i.instrument_type,i.settle_currency,m.external_symbol "
        "FROM accounts a JOIN instrument_mappings m ON m.venue_id=a.venue_id "
        "JOIN instruments i ON i.id=m.instrument_id WHERE m.status='active' "
        "AND i.instrument_type IN ('crypto_spot','crypto_perp')"
    ):
        category = (
            "spot"
            if row["instrument_type"] == "crypto_spot"
            else "linear"
            if row["settle_currency"] in {"USDT", "USDC"}
            else "inverse"
        )
        alias = f"monitor:bybit:{row['account_id']}:{category}:{row['external_symbol'].upper()}"
        key = (row["account_id"], alias)
        aliases[key] = row["id"] if key not in aliases or aliases[key] == row["id"] else None
    return OrderIdentities(
        db.execute(
            "SELECT o.id,o.command_id,o.account_id,o.instrument_id,o.external_order_id,"
            "o.side,o.quantity,o.created_at,tc.strategy_instance_id "
            "FROM orders o LEFT JOIN trade_commands tc ON tc.id=o.command_id"
        ).fetchall(),
        aliases,
    )


def load_order_execution_links(db: sqlite3.Connection) -> dict[str, dict[str, str | None]]:
    """Include every attempt, release and owned risk-reduction command."""
    links: dict[str, dict[str, str | None]] = {}
    sources = (
        "SELECT order_id,batch_id FROM execution_batch_legs "
        "UNION SELECT order_id,batch_id FROM funding_perpetual_attempts "
        "UNION SELECT order_id,batch_id FROM funding_spot_release_commands "
    )
    # Risk tables are created lazily by the existing risk repository. A plan
    # rejected before risk admission has no risk actions to link.
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='execution_risk_actions'").fetchone():
        sources += (
            "UNION SELECT j.value,a.batch_id FROM execution_risk_actions a,"
            "json_each(a.generated_order_ids_json) j "
            "UNION SELECT o.id,a.batch_id FROM execution_risk_actions a "
            "JOIN execution_batch_legs l ON l.batch_id=a.batch_id "
            "JOIN trade_commands c ON c.idempotency_key=a.idempotency_key || ':' || l.role "
            "JOIN orders o ON o.command_id=c.id "
            "UNION SELECT o.id,a.batch_id FROM execution_risk_actions a "
            "JOIN trade_commands c ON c.idempotency_key=a.idempotency_key || ':replacement' "
            "JOIN orders o ON o.command_id=c.id"
        )
    for row in db.execute(
        "SELECT x.order_id,b.id AS batch_id,b.strategy_instruction_id AS instruction_id "
        f"FROM ({sources}) x "
        "JOIN execution_batches b ON b.id=x.batch_id WHERE x.order_id IS NOT NULL"
    ):
        link = {"batchId": row["batch_id"], "instructionId": row["instruction_id"]}
        if row["order_id"] in links and links[row["order_id"]] != link:
            raise VenueIdentityConflict("Order has conflicting execution batch owners")
        links[row["order_id"]] = link
    return links


def resolve_snapshot_order(
    db: sqlite3.Connection,
    account_id: str,
    payload: Mapping[str, Any],
    *,
    identities: OrderIdentities | None = None,
) -> str:
    identities = identities if identities is not None else load_order_identities(db)
    existing = identities.resolve(account_id, payload)
    if existing is not None:
        return existing
    external = str(payload.get("externalOrderId") or "")
    instrument = str(payload.get("instrumentId") or "")
    if not external or not instrument:
        raise VenueIdentityConflict("Venue order lacks authoritative identity")
    return scoped_identity("order", account_id, instrument, external)


def canonical_operational_rows(
    rows: Iterable[Any], identities: OrderIdentities
) -> list[dict[str, Any]]:
    """Select one persisted order projection for each exact native order.

    Prefer the command-owned projection. Legacy alias rows remain stored, but
    must not be added to an execution confirmation for the same native order.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        canonical = identities.canonical.get(row["order_id"])
        if canonical is None:
            raise VenueIdentityConflict("Operational order identity is ambiguous")
        grouped[canonical].append(dict(row))
    result = []
    for order_id, candidates in grouped.items():
        source_order = (
            order_id
            if any(row["order_id"] == order_id for row in candidates)
            else (min(candidates, key=lambda row: (row["occurred_at"], row["fill_id"]))["order_id"])
        )
        result.extend(
            {**row, "order_id": order_id} for row in candidates if row["order_id"] == source_order
        )
    return result


def order_execution_evidence(
    db: sqlite3.Connection,
    order_id: str,
    *,
    identities: OrderIdentities | None = None,
) -> tuple[Decimal, Decimal | None, bool, list[str]]:
    """Read one order's executions without adding confirmations to native fills.

    Unclassified legacy rows cannot prove a risk closure. Native executions must
    cover the requested quantity before they supersede such ambiguous history.
    Actual excess executions are retained and make the evidence incomplete.
    """
    identities = identities or load_order_identities(db)
    if identities.canonical.get(order_id) != order_id:
        raise VenueIdentityConflict("Risk order does not have a unique command owner")
    order = identities.rows[order_id]
    rows = [dict(row) for row in db.execute("SELECT * FROM fills WHERE order_id=?", (order_id,))]
    native: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}
    confirmations: list[tuple[Decimal, Decimal, str]] = []
    legacy: list[tuple[Decimal, Decimal, str]] = []

    def amounts(quantity: Any, price: Any) -> tuple[Decimal, Decimal]:
        q, p = Decimal(str(quantity)), Decimal(str(price))
        if not q.is_finite() or not p.is_finite() or q <= 0 or p <= 0:
            raise VenueIdentityConflict("Execution quantity or price is invalid")
        return q, p

    def add_native(source: str, identity: str, quantity: Any, price: Any) -> None:
        if not source or not identity:
            raise VenueIdentityConflict("Native execution lacks provenance")
        value = amounts(quantity, price)
        key = (source, identity)
        if key in native and native[key] != value:
            raise VenueIdentityConflict("Native execution identity has conflicting amounts")
        native[key] = value

    for row in rows:
        if any(row[key] != order[key] for key in ("account_id", "instrument_id", "side")):
            raise VenueIdentityConflict("Execution identity conflicts with its order")
        if row["origin"] == "venue_execution":
            add_native(row["source"], row["external_fill_id"], row["quantity"], row["price"])
        elif row["origin"] in {"runtime_confirmation", "legacy"}:
            target = confirmations if row["origin"] == "runtime_confirmation" else legacy
            target.append((*amounts(row["quantity"], row["price"]), row["id"]))
        else:
            raise VenueIdentityConflict("Unknown execution provenance")

    for event in db.execute(
        "SELECT source,external_id,payload_json FROM venue_account_events "
        "WHERE account_id=? AND instrument_id=? AND event_type='trade_fill'",
        (order["account_id"], order["instrument_id"]),
    ):
        payload = json.loads(event["payload_json"])
        # Unrelated orders in a shared account cannot become this order's evidence.
        if payload.get("externalOrderId") != order["external_order_id"]:
            continue
        if (
            not order["external_order_id"]
            or identities.resolve(order["account_id"], payload) != order_id
        ):
            raise VenueIdentityConflict("Native execution order identity is ambiguous")
        add_native(event["source"], event["external_id"], payload["quantity"], payload["price"])

    requested = Decimal(order["quantity"])
    confirmed = sum((q for q, _, _ in confirmations), Decimal(0))
    native_quantity = sum((q for q, _ in native.values()), Decimal(0))
    if native and native_quantity >= confirmed and (not legacy or native_quantity >= requested):
        return (
            native_quantity,
            max(p for _, p in native.values()),
            native_quantity <= requested and confirmed <= requested,
            [f"{source}:{identity}" for source, identity in sorted(native)],
        )
    if confirmations and not legacy:
        return (
            confirmed,
            max(p for _, p, _ in confirmations),
            confirmed <= requested and native_quantity <= requested,
            [identity for _, _, identity in confirmations],
        )
    if legacy:
        # Only a lower bound is known; never guess which legacy rows overlap.
        return (
            max(native_quantity, max(q for q, _, _ in legacy)),
            max([p for _, p, _ in legacy] + [p for _, p in native.values()]),
            False,
            [identity for _, _, identity in legacy],
        )
    return Decimal(0), None, True, []
