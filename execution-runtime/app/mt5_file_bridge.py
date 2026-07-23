from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from app.models import CrossSpreadVenueSnapshot, MarketQuote, VenuePosition


def read_mt5_bridge_snapshot(path: str, symbol: str) -> CrossSpreadVenueSnapshot:
    bridge_path = Path(path)
    if not bridge_path.exists():
        return CrossSpreadVenueSnapshot(
            venue="mt5",
            symbol=symbol,
            status="unavailable",
            reason=f"MT5 bridge file not found: {bridge_path}",
        )

    try:
        payload = json.loads(bridge_path.read_text(encoding="utf-8-sig"))
        payload_symbol = str(payload.get("symbol") or symbol)
        bid = Decimal(str(payload["bid"]))
        ask = Decimal(str(payload["ask"]))
        positions = []
        for row in payload.get("positions", []):
            side = str(row.get("side") or "").lower()
            volume = Decimal(str(row.get("volume") or "0"))
            signed_volume = volume if side == "buy" else -volume
            positions.append(
                VenuePosition(
                    symbol=str(row.get("symbol") or payload_symbol),
                    side=side or "unknown",
                    quantity=signed_volume,
                    averagePrice=_optional_decimal(row.get("priceOpen")),
                    unrealizedPnl=_optional_decimal(row.get("profit")),
                    externalId=str(row.get("ticket") or "") or None,
                )
            )

        return CrossSpreadVenueSnapshot(
            venue="mt5",
            symbol=payload_symbol,
            status="available",
            quote=MarketQuote(
                bid=bid,
                ask=ask,
                mid=(bid + ask) / Decimal("2"),
                last=_optional_decimal(payload.get("last")),
                currency="USD",
            ),
            positions=positions,
            reason=_swap_reason(payload),
        )
    except Exception as exc:
        return CrossSpreadVenueSnapshot(
            venue="mt5",
            symbol=symbol,
            status="unavailable",
            reason=f"MT5 bridge file parse failed: {exc}",
        )


def _optional_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _swap_reason(payload: dict[str, object]) -> str | None:
    if "swapLong" not in payload and "swapShort" not in payload:
        return None
    return f"swapLong={payload.get('swapLong')};swapShort={payload.get('swapShort')}"
