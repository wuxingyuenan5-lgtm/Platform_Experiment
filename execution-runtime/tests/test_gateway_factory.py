import pytest

from app.bybit_mt5_gateway import BybitMt5Gateway
from app.fake_gateway import FakeGateway
from app.gateway_factory import create_gateway
from app.models import SubmitOrderCommand


def test_gateway_factory_creates_fake_gateway() -> None:
    assert isinstance(create_gateway("fake"), FakeGateway)
    assert isinstance(create_gateway("simulation"), FakeGateway)


def test_gateway_factory_rejects_fake_gateway_for_live_write() -> None:
    for gateway_name in ("fake", "simulation"):
        with pytest.raises(
            ValueError,
            match="Fake execution gateway cannot be used with Live Write enabled",
        ):
            create_gateway(gateway_name, live_write_enabled=True)


def test_gateway_factory_creates_bybit_mt5_gateway() -> None:
    gateway = create_gateway("bybit_mt5")

    assert isinstance(gateway, BybitMt5Gateway)
    assert gateway.name == "bybit_mt5"


def test_gateway_factory_allows_live_gateway_for_live_write() -> None:
    gateway = create_gateway("bybit_mt5", live_write_enabled=True)

    assert isinstance(gateway, BybitMt5Gateway)


def test_gateway_factory_rejects_unknown_gateway() -> None:
    with pytest.raises(ValueError, match="Unsupported execution gateway"):
        create_gateway("real")


def test_fake_gateway_exposes_the_normalized_venue_gateway_surface() -> None:
    gateway = create_gateway("fake")
    command = SubmitOrderCommand(
        command_id="command-gateway-contract",
        platform_order_id="order-gateway-contract",
        account_id="account_crypto_test",
        instrument_id="instrument-btcusdt",
        symbol="BTCUSDT",
        side="buy",
        quantity="0.01",
    )

    assert gateway.place_order(command)[0].command_id == command.command_id
    assert gateway.get_account(command.account_id).account_id == command.account_id
    assert gateway.get_positions(command.account_id)
    assert gateway.get_open_orders(account_id=command.account_id) == []
    assert gateway.health().gateway == "fake"
