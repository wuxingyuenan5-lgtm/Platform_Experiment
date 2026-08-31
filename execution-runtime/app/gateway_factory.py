from app.bybit_mt5_gateway import BybitMt5Gateway
from app.fake_gateway import FakeGateway
from app.gateway import VenueGateway


def create_gateway(
    gateway_name: str,
    *,
    live_write_enabled: bool = False,
) -> VenueGateway:
    normalized_name = gateway_name.strip().lower()
    if normalized_name in {"fake", "simulation"}:
        if live_write_enabled:
            raise ValueError("Fake execution gateway cannot be used with Live Write enabled")
        return FakeGateway()
    if normalized_name in {
        "bybit_mt5",
        "bybit_mt5_live",
        "cross_venue_market",
        "live",
    }:
        return BybitMt5Gateway()
    raise ValueError(f"Unsupported execution gateway: {gateway_name}")
