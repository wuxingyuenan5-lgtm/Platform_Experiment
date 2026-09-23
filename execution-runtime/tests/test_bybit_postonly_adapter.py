from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.bybit_fill_confirming_adapter import (
    CROSS_SPREAD_STRATEGY_INSTANCE_ID,
    BybitFillConfirmingAdapter,
)
from app.config import Settings, get_settings
from app.gateway_errors import GatewayResultUnknownError
from app.journal import initialize_journal
from app.models import SubmitOrderCommand


class NativeClient:
    endpoint = "https://api.bybit.com"

    def __init__(self, strategy_pages, order_pages, executions=None, create_error=None):
        self.strategy_pages, self.order_pages = list(strategy_pages), list(order_pages)
        self.executions, self.create_error, self.calls = executions or [], create_error, []

    def _submit_request(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["path"].endswith("/strategy/create"):
            if self.create_error:
                raise self.create_error
            return {"retCode": 0, "result": {"strategyId": "strategy-1"}}
        if kwargs["path"].endswith("/strategy/stop"):
            return {"retCode": 0, "result": {"strategyId": "strategy-1"}}
        pages = (
            self.strategy_pages if kwargs["path"].endswith("/strategy/list") else self.order_pages
        )
        return {"retCode": 0, "result": pages.pop(0) if pages else {"list": []}}

    def get_positions(self, **kwargs):
        return {"retCode": 0, "result": {"list": [{"symbol": kwargs["symbol"], "positionIdx": 0}]}}

    def get_executions(self, **kwargs):
        order_id = kwargs.get("orderId")
        rows = [row for row in self.executions if row.get("orderId") == order_id]
        return {"retCode": 0, "result": {"list": rows}}


def settings():
    return Settings(
        _env_file=None,
        environment="live",
        live_write_enabled=True,
        live_account_allowlist="account-bybit",
        live_strategy_allowlist=CROSS_SPREAD_STRATEGY_INSTANCE_ID,
        live_symbol_allowlist="XAUTUSDT",
        live_max_order_notional="200000",
        bybit_account_ids="account-bybit",
        bybit_instrument_map="XAUTUSDT=instrument-xaut",
        bybit_postonly_chase_ttl_seconds=0,
    )


def guard():
    return {
        "target_spread": Decimal("2"),
        "max_adverse_spread": Decimal("1"),
        "mt5_account_id": "mt5",
        "mt5_symbol": "XAUUSD",
        "mt5_close": False,
        "mt5_min_quantity": Decimal("0.1"),
        "mt5_quantity_step": Decimal("0.1"),
        "mt5_contract_multiplier": Decimal("1"),
    }


def command(name):
    return SubmitOrderCommand(
        command_id=f"command-{name}",
        platform_order_id=f"platform-{name}",
        strategy_instance_id=CROSS_SPREAD_STRATEGY_INSTANCE_ID,
        account_id="account-bybit",
        instrument_id="instrument-xaut",
        symbol="XAUTUSDT",
        side="buy",
        order_type="limit",
        execution_policy="post_only_chase",
        quantity="1",
        price="2500.5",
        cross_spread_guard=guard(),
    )


def adapter(client):
    instance = BybitFillConfirmingAdapter(settings(), client)
    now = datetime.now(UTC)
    mt5 = SimpleNamespace(
        account_id="mt5",
        symbol="XAUUSD",
        bid=Decimal("100"),
        ask=Decimal("101"),
        source_as_of=now,
        as_of=now,
        raw_payload={
            "accountTradeAllowed": True,
            "accountExpertTradeAllowed": True,
            "pythonTradeAllowed": True,
            "symbolVisible": True,
            "terminalTradeAllowed": True,
            "tradeMode": 4,
        },
    )
    bybit = SimpleNamespace(
        account_id="account-bybit",
        symbol="XAUTUSDT",
        bid=Decimal("101"),
        ask=Decimal("102"),
        source_as_of=now,
        as_of=now,
        raw_payload={},
    )
    instance.market_quote_reader = lambda **_: mt5
    instance.get_market_quote = lambda **_: bybit
    return instance


def prepare(tmp_path):
    get_settings().journal_path = str(tmp_path / "runtime.db")
    initialize_journal()


def test_native_full_fill_uses_real_execution_average(tmp_path):
    prepare(tmp_path)
    strategy = {
        "strategyId": "strategy-1",
        "symbol": "XAUTUSDT",
        "side": "Buy",
        "strategyType": "chaseOrder",
        "category": "UTA_USDT",
        "size": "1",
        "executedSize": "1",
        "status": "4",
    }
    orders = {
        "list": [
            {
                "strategyId": "strategy-1",
                "orderId": "child-1",
                "size": "0.4",
                "executedSize": "0.4",
                "status": "5",
            },
            {
                "strategyId": "strategy-1",
                "orderId": "child-2",
                "size": "0.6",
                "executedSize": "0.6",
                "status": "5",
            },
        ]
    }
    client = NativeClient(
        [{"list": [strategy]}],
        [orders],
        [
            {
                "execId": "exec-1",
                "orderId": "child-1",
                "symbol": "XAUTUSDT",
                "side": "Buy",
                "execQty": "0.4",
                "execPrice": "2500",
                "execTime": "1780000000000",
            },
            {
                "execId": "exec-2",
                "orderId": "child-2",
                "symbol": "XAUTUSDT",
                "side": "Buy",
                "execQty": "0.6",
                "execPrice": "2500.2",
                "execTime": "1780000000001",
            },
        ],
    )
    events = adapter(client).submit_order(command("full"))
    assert events[-1].fill_quantity == Decimal("1")
    assert events[-1].fill_price == Decimal("2500.12")


def test_native_partial_after_stop_is_terminal(tmp_path):
    prepare(tmp_path)
    strategy = {
        "strategyId": "strategy-1",
        "symbol": "XAUTUSDT",
        "side": "Buy",
        "strategyType": "chaseOrder",
        "category": "UTA_USDT",
        "size": "1",
        "executedSize": "0.4",
        "status": "4",
    }
    child = {
        "strategyId": "strategy-1",
        "orderId": "child-1",
        "size": "1",
        "executedSize": "0.4",
        "status": "7",
    }
    client = NativeClient(
        [{"list": [{**strategy, "status": "2"}]}, {"list": [strategy]}],
        [{"list": [{**child, "status": "4"}]}, {"list": [child]}],
        [
            {
                "execId": "exec-1",
                "orderId": "child-1",
                "symbol": "XAUTUSDT",
                "side": "Buy",
                "execQty": "0.4",
                "execPrice": "2500",
                "execTime": "1780000000000",
            }
        ],
    )
    events = adapter(client).submit_order(command("partial"))
    assert sum(call["path"].endswith("/strategy/stop") for call in client.calls) == 1
    assert events[-1].terminal is True
    assert events[-1].fill_quantity == Decimal("0.4")
    from app.journal import mark_command_result_unknown, save_command_started
    from app.runtime_recovery import recover_command

    frozen = command("partial")
    # The normal route already owns the same command; recovery reads native facts.
    save_command_started(frozen)
    mark_command_result_unknown(frozen.command_id)
    client.strategy_pages = [{"list": [strategy]}]
    client.order_pages = [{"list": [child]}]
    recovered = recover_command(frozen.command_id, gateway=adapter(client))
    assert recovered[-1].terminal is True
    assert recovered[-1].fill_quantity == Decimal("0.4")
    assert recovered[-1].event_id == events[-1].event_id
    assert sum(call["path"].endswith("/strategy/create") for call in client.calls) == 1


def test_native_create_unknown_is_not_retried(tmp_path):
    prepare(tmp_path)
    client = NativeClient([], [], create_error=TimeoutError("timeout"))
    with pytest.raises(GatewayResultUnknownError):
        adapter(client).submit_order(command("unknown"))
    with pytest.raises(GatewayResultUnknownError):
        adapter(client).submit_order(command("unknown"))
    assert sum(call["path"].endswith("/strategy/create") for call in client.calls) == 1


def test_stop_ack_without_child_terminal_never_releases_fill(tmp_path):
    prepare(tmp_path)
    strategy = {
        "strategyId": "strategy-1",
        "symbol": "XAUTUSDT",
        "side": "Buy",
        "strategyType": "chaseOrder",
        "category": "UTA_USDT",
        "size": "1",
        "executedSize": "0",
        "status": "3",
    }
    child = {
        "strategyId": "strategy-1",
        "orderId": "child",
        "size": "1",
        "executedSize": "0",
        "status": "2",
    }
    client = NativeClient([{"list": [strategy]}] * 4, [{"list": [child]}] * 4)
    instance = adapter(client)
    instance.settings.bybit_postonly_chase_rest_reconcile_seconds = 0
    with pytest.raises(GatewayResultUnknownError):
        instance.submit_order(command("stop-unknown"))
    assert sum(call["path"].endswith("/strategy/stop") for call in client.calls) == 1
    assert sum(call["path"].endswith("/strategy/create") for call in client.calls) == 1


def test_guard_blocked_or_live_disabled_never_creates(tmp_path):
    from app.gateway_errors import GatewayConfigurationError, GatewayRequestRejectedError

    prepare(tmp_path)
    client = NativeClient([], [])
    instance = adapter(client)
    instance.market_quote_reader(account_id="mt5").raw_payload["tradeMode"] = 0
    with pytest.raises(GatewayRequestRejectedError):
        instance.submit_order(command("closed"))
    assert not client.calls
    instance.settings.live_write_enabled = False
    with pytest.raises(GatewayConfigurationError):
        instance.submit_order(command("disabled"))
    assert not client.calls


def test_execution_pages_deduplicate_and_reject_conflicts(tmp_path):
    prepare(tmp_path)
    fill = {
        "execId": "e",
        "orderId": "c",
        "symbol": "XAUTUSDT",
        "side": "Buy",
        "execQty": "0.4",
        "execPrice": "2500",
        "execTime": "1780000000000",
    }
    client = NativeClient([], [])
    queries = []

    def execute(**kwargs):
        queries.append(kwargs)
        return {
            "retCode": 0,
            "result": {
                "list": [fill],
                "nextPageCursor": "next" if not kwargs.get("cursor") else "",
            },
        }

    client.get_executions = execute
    assert adapter(client)._native_executions(client, command("pages"), [{"orderId": "c"}]) == [
        fill
    ]
    assert queries[1]["cursor"] == "next"

    def conflict(**kwargs):
        row = {**fill, "execPrice": "2600"} if kwargs.get("cursor") else fill
        return {
            "retCode": 0,
            "result": {"list": [row], "nextPageCursor": "next" if not kwargs.get("cursor") else ""},
        }

    client.get_executions = conflict
    with pytest.raises(GatewayResultUnknownError, match="conflicting"):
        adapter(client)._native_executions(client, command("conflict"), [{"orderId": "c"}])


def test_spread_guard_direction_and_close_only_market():
    instance = adapter(NativeClient([], []))
    buy = command("buy")
    buy.cross_spread_guard.max_adverse_spread = Decimal("0")
    assert instance._cross_guard_allows(buy)  # Ask 102 - Bid 100 == 2
    buy.cross_spread_guard.target_spread = Decimal("1.99")
    assert not instance._cross_guard_allows(buy)
    sell = command("sell").model_copy(update={"side": "sell"})
    sell.cross_spread_guard.target_spread = Decimal("1")
    assert instance._cross_guard_allows(sell)  # Bid 101 - Ask 101 == 0 >= 1-1
    sell.cross_spread_guard.max_adverse_spread = Decimal("0.99")
    assert not instance._cross_guard_allows(sell)
    sell.cross_spread_guard.target_spread = Decimal("0")
    instance.market_quote_reader().raw_payload["tradeMode"] = 3
    assert not instance._cross_guard_allows(sell)
    sell.cross_spread_guard.mt5_close = True
    assert instance._cross_guard_allows(sell)


@pytest.mark.parametrize("side,expected", [("buy", 1), ("sell", 2)])
def test_native_open_resolves_hedge_position_mode(side, expected):
    client = NativeClient([], [])
    client.get_positions = lambda **kw: {"retCode": 0, "result": {"list": [
        {"symbol": kw["symbol"], "positionIdx": 1}, {"symbol": kw["symbol"], "positionIdx": 2}]}}
    cmd = command("hedge-mode").model_copy(update={"side": side})
    assert adapter(client)._resolve_native_position_idx(client, cmd) == expected
