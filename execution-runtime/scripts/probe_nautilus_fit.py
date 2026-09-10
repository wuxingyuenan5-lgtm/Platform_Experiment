"""Offline fit probes. No venue client, credentials, terminal or live node is started."""

import asyncio
import json
from decimal import Decimal
from importlib.metadata import version

from nautilus_trader.adapters.bybit.config import BybitExecClientConfig
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.live.config import LiveExecEngineConfig
from nautilus_trader.live.execution_engine import LiveExecutionEngine
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import ClientId, ClientOrderId, PositionId, TradeId
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.test_kit.mocks.exec_clients import MockLiveExecutionClient
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.test_kit.stubs.commands import TestCommandStubs
from nautilus_trader.test_kit.stubs.events import TestEventStubs
from nautilus_trader.test_kit.stubs.execution import TestExecStubs
from nautilus_trader.test_kit.stubs.identifiers import TestIdStubs

results = {"version": version("nautilus_trader"), "network_clients_started": 0}
if results["version"] != "1.231.0":
    raise RuntimeError("This acceptance probe is pinned to nautilus_trader==1.231.0")


async def probe():
    clock = LiveClock()
    bus = MessageBus(trader_id=TestIdStubs.trader_id(), clock=clock)
    cache = Cache(database=None)
    instrument = TestInstrumentProvider.btcusdt_binance()
    cache.add_instrument(instrument)
    engine = LiveExecutionEngine(
        loop=asyncio.get_running_loop(),
        msgbus=bus,
        cache=cache,
        clock=clock,
        config=LiveExecEngineConfig(reconciliation=False, inflight_check_interval_ms=0),
    )
    client = MockLiveExecutionClient(
        loop=asyncio.get_running_loop(),
        client_id=ClientId("BINANCE"),
        venue=instrument.id.venue,
        account_type=AccountType.CASH,
        base_currency=None,
        instrument_provider=InstrumentProvider(),
        msgbus=bus,
        cache=cache,
        clock=clock,
        oms_type=OmsType.HEDGING,
    )
    engine.register_client(client)
    fills = []
    bus.subscribe("events.order.*", fills.append)
    engine.start()

    def make_order(identity, quantity, side=OrderSide.BUY):
        return TestExecStubs.limit_order(
            instrument=instrument,
            quantity=Quantity.from_str(quantity),
            price=Price.from_str("100.00"),
            order_side=side,
            client_order_id=ClientOrderId(identity),
        )

    async def flush():
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    async def submit(order):
        command = TestCommandStubs.submit_order_command(order)
        engine.execute(command)
        await flush()
        engine.process(TestEventStubs.order_submitted(order, account_id=client.account_id))
        engine.process(TestEventStubs.order_accepted(order, account_id=client.account_id))
        await flush()

    def fill(order, trade, quantity):
        return TestEventStubs.order_filled(
            order,
            instrument,
            account_id=client.account_id,
            trade_id=TradeId(trade),
            last_qty=Quantity.from_str(quantity),
            last_px=Price.from_str("100.00"),
            commission=Money(0, USDT),
            position_id=PositionId("funding-open-1"),
        )

    try:
        order = make_order("funding-perp-open", "0.5")
        await submit(order)
        cumulative = []
        events = []
        for trade, quantity in [
            ("fill-1", "0.2"),
            ("fill-2", "0.1"),
            ("fill-1", "0.2"),
            ("fill-3", "0.2"),
        ]:
            event = fill(order, trade, quantity)
            events.append(event)
            engine.process(event)
            await flush()
            cumulative.append(str(order.filled_qty))
        assert [Decimal(x) for x in cumulative] == list(map(Decimal, ["0.2", "0.3", "0.3", "0.5"]))
        results["partial_fill_deduplication"] = cumulative
        results["published_fill_count"] = sum(type(e).__name__ == "OrderFilled" for e in fills)

        # Rebuild from persisted real order events, then redeliver an old trade.
        replay = make_order("funding-perp-open", "0.5")
        replay.apply(TestEventStubs.order_submitted(replay, account_id=client.account_id))
        replay.apply(TestEventStubs.order_accepted(replay, account_id=client.account_id))
        for event in (events[0], events[1], events[3]):
            replay.apply(event)
        try:
            replay.apply(events[0])
        except KeyError:
            pass
        assert replay.filled_qty.as_decimal() == Decimal("0.5")
        results["model_event_replay"] = str(replay.filled_qty)

        late = make_order("funding-stop-late", "0.5")
        await submit(late)
        engine.process(fill(late, "stop-fill-1", "0.2"))
        await flush()
        engine.process(TestEventStubs.order_pending_cancel(late))
        engine.process(TestEventStubs.order_canceled(late))
        await flush()
        engine.process(fill(late, "stop-fill-2", "0.1"))
        await flush()
        results["late_fill_after_cancel"] = {
            "quantity": str(late.filled_qty),
            "status": str(late.status),
        }

        results["mock_submit_count"] = client.calls.count("submit_order")
        results["limits"] = [
            "Uses a mock venue client; not a Bybit timeout or restart integration acceptance.",
            "Funding spot release and target-group partial close still require the platform saga.",
            "MT5 Ticket/account worker mapping requires a new execution client.",
        ]
    finally:
        engine.stop()
        await flush()


asyncio.run(probe())
config = BybitExecClientConfig(auto_repay_spot_borrows=False)
results["explicit_bybit_no_mutation_configuration"] = {
    key: getattr(config, key)
    for key in ("futures_leverages", "position_mode", "margin_mode", "auto_repay_spot_borrows")
}
precision = {}
for value in ("0.000000001", "0.0000000001"):
    try:
        precision[value] = str(Quantity.from_str(value))
    except ValueError as exc:
        precision[value] = str(exc)
results["windows_quantity_precision"] = precision
results["native_fee_roundtrip"] = {
    "input": "0.123456789012345678",
    "money": str(Money(Decimal("0.123456789012345678"), USDT).as_decimal()),
}
# Fail this candidate early when native amounts cannot round-trip. This is not
# a complete Funding/MT5 integration acceptance and must never claim to be one.
results["native_precision_passed"] = results["windows_quantity_precision"][
    "0.0000000001"
] == "0.0000000001" and Decimal(results["native_fee_roundtrip"]["money"]) == Decimal(
    results["native_fee_roundtrip"]["input"]
)
print(json.dumps(results, indent=2))
