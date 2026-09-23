from decimal import Decimal

import pytest

from app.config import get_settings
from app.live_route_store import (
    get_order_route,
    get_strategy_route_for_order,
    record_order_route,
    record_strategy_order_route,
    record_strategy_route,
)
from app.models import SubmitOrderCommand


def command(platform: str, account: str) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=f"cmd-{platform}",
        platform_order_id=platform,
        strategy_instance_id="strategy-cross",
        account_id=account,
        instrument_id="instrument-x",
        symbol="XAUTUSDT",
        side="buy",
        order_type="limit",
        quantity=Decimal("1"),
        price=Decimal("100"),
    )


def test_native_identity_conflicts_are_rejected(tmp_path):
    get_settings().journal_path = str(tmp_path / "routes.db")
    first = command("platform-1", "account-1")
    record_order_route(first, "bybit_live", "client-1")
    record_strategy_route(first, "bybit_live", "strategy-1")
    with pytest.raises(ValueError, match="already assigned"):
        record_strategy_route(command("platform-2", "account-1"), "bybit_live", "strategy-1")
    with pytest.raises(ValueError, match="already assigned"):
        record_strategy_order_route(
            strategy_id="strategy-1",
            order_id="child-1",
            command=command("platform-2", "account-1"),
        )
    record_strategy_order_route(strategy_id="strategy-1", order_id="child-1", command=first)


def test_child_order_resolves_parent_and_preserves_account_isolation(tmp_path):
    get_settings().journal_path = str(tmp_path / "routes.db")
    first = command("platform-1", "account-1")
    record_order_route(first, "bybit_live", "client-1")
    record_strategy_route(first, "bybit_live", "strategy-1")
    record_strategy_order_route(strategy_id="strategy-1", order_id="child-1", command=first)
    route = get_order_route(external_order_id="child-1")
    assert route is not None
    assert get_strategy_route_for_order("child-1").strategy_id == "strategy-1"
    assert route.platform_order_id == "platform-1"
    assert route.external_order_id == "child-1"
    assert get_order_route(external_order_id="child-1", account_id="account-2") is None
