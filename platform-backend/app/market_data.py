from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.database import connection
from app.schemas import CrossSpreadHistoryPointResponse, CrossSpreadSnapshotResponse


def save_cross_spread_market_snapshot(
    snapshot: CrossSpreadSnapshotResponse,
    *,
    strategy_key: str,
    strategy_instance_id: str,
) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO market_spread_snapshots (
                id, strategy_key, strategy_instance_id,
                left_venue_code, left_symbol, right_venue_code, right_symbol,
                status, left_bid, left_ask, left_mid, right_bid, right_ask, right_mid,
                long_spread, short_spread, funding_rate, usdt_usd,
                buyer_inventory_fee, seller_inventory_fee,
                payload_json, observed_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                strategy_key,
                strategy_instance_id,
                snapshot.bybit.venue,
                snapshot.bybit.symbol,
                snapshot.mt5.venue,
                snapshot.mt5.symbol,
                snapshot.status,
                _decimal_text(snapshot.bybit.quote.bid if snapshot.bybit.quote else None),
                _decimal_text(snapshot.bybit.quote.ask if snapshot.bybit.quote else None),
                _decimal_text(snapshot.bybit.quote.mid if snapshot.bybit.quote else None),
                _decimal_text(snapshot.mt5.quote.bid if snapshot.mt5.quote else None),
                _decimal_text(snapshot.mt5.quote.ask if snapshot.mt5.quote else None),
                _decimal_text(snapshot.mt5.quote.mid if snapshot.mt5.quote else None),
                _decimal_text(snapshot.long_spread),
                _decimal_text(snapshot.short_spread),
                _decimal_text(snapshot.metrics.funding_rate),
                _decimal_text(snapshot.metrics.usdt_usd),
                _decimal_text(snapshot.metrics.buyer_inventory_fee),
                _decimal_text(snapshot.metrics.seller_inventory_fee),
                snapshot.model_dump_json(by_alias=True),
                snapshot.as_of.isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )


def list_cross_spread_market_history(
    *,
    strategy_key: str,
    limit: int = 200,
) -> list[CrossSpreadHistoryPointResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT observed_at, long_spread, short_spread, left_mid, right_mid
            FROM market_spread_snapshots
            WHERE strategy_key = ?
            ORDER BY observed_at DESC, created_at DESC
            LIMIT ?
            """,
            (strategy_key, limit),
        ).fetchall()
    return [
        CrossSpreadHistoryPointResponse(
            asOf=datetime.fromisoformat(row["observed_at"]),
            longSpread=_optional_decimal(row["long_spread"]),
            shortSpread=_optional_decimal(row["short_spread"]),
            bybitMid=_optional_decimal(row["left_mid"]),
            mt5Mid=_optional_decimal(row["right_mid"]),
        )
        for row in reversed(rows)
    ]


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _optional_decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value not in (None, "") else None
