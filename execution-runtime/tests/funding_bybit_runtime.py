"""Isolated HTTP fixture: production Bybit gateway/adapter with only SDK I/O replaced.

No external network is permitted. The two accounts and BTC spot/perpetual share
the real routing, CCXT parsing, Runtime journal and command/query contracts.
"""

import json
import os
import socket
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from test_bybit_order_market_identity import MarketClient

from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import get_settings
from app.main import create_app
from app.models import GatewayAdapterCapability
from app.secret_resolver import env_prefix_for_secret_name
from app.strict_live_acceptance_adapters import StrictBybitAcceptanceAdapter

fixture_dir = Path(os.environ["FUNDING_BYBIT_FIXTURE_DIR"])
original_connect = socket.socket.connect


def loopback_connect(sock, address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1"}:
        raise AssertionError("External network is prohibited in the Bybit contract fixture")
    return original_connect(sock, address)


socket.socket.connect = loopback_connect


def controls():
    path = fixture_dir / "controls.json"
    return json.loads(path.read_text()) if path.exists() else {}


def milliseconds():
    return str(int(datetime.now(UTC).timestamp() * 1000))


class NativeClient(MarketClient):
    def __init__(self, account):
        super().__init__()
        self.account = account

    def get_api_key_information(self):
        self.spot_permission = not controls().get("deny_spot_permission", False)
        return super().get_api_key_information()

    def get_tickers(self, **query):
        return {
            "retCode": 0,
            "time": milliseconds(),
            "result": {
                "category": query["category"],
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "lastPrice": "79000",
                        "bid1Price": controls().get("bid", "79000"),
                        "ask1Price": controls().get("ask", "79000.1"),
                        "fundingRate": "0.0001",
                        "nextFundingTime": milliseconds(),
                    }
                ],
            },
        }

    def place_order(self, **payload):
        assert self.account == "bybit-live-main", "Monitor account received a write"
        if payload["category"] == "spot":
            assert payload["marketUnit"] == "baseCoin" and payload["isLeverage"] == 0
            assert "reduceOnly" not in payload
        if payload.get("reduceOnly"):
            net = self.net("linear")
            assert net and (payload["side"] == "Buy") == (net < 0)
            assert Decimal(payload["qty"]) <= abs(net), "Reduction exceeds actual position"
        with (fixture_dir / "sdk-writes.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"account": self.account, **payload}) + "\n")
        if payload["category"] == "spot" and controls().get("reject_spot_order"):
            return {"retCode": 10001, "retMsg": "Isolated venue rejection", "result": {}}
        identity = f"native-{len(self.orders) + 1}"
        filled = payload["qty"]
        if not self.orders and controls().get("partial_first_quantity"):
            assert payload["category"] == "linear" and payload["timeInForce"] == "PostOnly"
            filled = controls()["partial_first_quantity"]
        self.orders[identity] = {**payload, "createdTime": milliseconds(), "filled": filled}
        return {"retCode": 0, "result": {"orderId": identity}}

    def cancel_order(self, **query):
        order = self.orders[query["orderId"]]
        assert query["category"] == order["category"]
        order["canceled"] = True
        order["updatedTime"] = milliseconds()
        with (fixture_dir / "sdk-cancels.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(query) + "\n")
        return {"retCode": 0, "result": {"orderId": query["orderId"]}}

    def get_open_orders(self, **query):
        rows = []
        for identity, order in self.orders.items():
            if order["category"] != query["category"]:
                continue
            if query.get("orderId") and query["orderId"] != identity:
                continue
            if query.get("orderLinkId") and query["orderLinkId"] != order["orderLinkId"]:
                continue
            rows.append(
                {
                    **order,
                    "orderId": identity,
                    "orderStatus": (
                        "Cancelled"
                        if order.get("canceled")
                        else "Filled"
                        if order["filled"] == order["qty"]
                        else "PartiallyFilled"
                    ),
                    "cumExecQty": order["filled"],
                    "avgPrice": "79000",
                    "leavesQty": str(Decimal(order["qty"]) - Decimal(order["filled"])),
                    "updatedTime": order.get("updatedTime", order["createdTime"]),
                }
            )
        return {"retCode": 0, "result": {"list": rows}}

    def get_order_history(self, **query):
        return self.get_open_orders(**query)

    def get_executions(self, **query):
        if controls().get("fail_fill_query"):
            raise ValueError("Isolated native fill-query failure after acknowledgement")
        rows = []
        for identity, order in self.orders.items():
            if order["category"] != query["category"]:
                continue
            if query.get("orderId") and query["orderId"] != identity:
                continue
            spot_buy = order["category"] == "spot" and order["side"] == "Buy"
            quantity = Decimal(order["filled"])
            fee = (
                quantity * Decimal("0.001")
                if spot_buy
                else quantity * Decimal("79000") * (Decimal("0.001") if order["category"] == "spot" else Decimal("0.00055"))
            )
            rows.append(
                {
                    "execId": f"fill-{identity}",
                    "orderId": identity,
                    "symbol": "BTCUSDT",
                    "side": order["side"],
                    "execQty": order["filled"],
                    "execPrice": "79000",
                    "execFee": str(fee),
                    "feeCurrency": "BTC" if spot_buy else "USDT",
                    "execTime": order["createdTime"],
                }
            )
        return {"retCode": 0, "result": {"list": rows}}

    def net(self, category):
        result = Decimal(0)
        for order in self.orders.values():
            if order["category"] != category:
                continue
            quantity = Decimal(order["filled"])
            result += quantity if order["side"] == "Buy" else -quantity
            if category == "spot" and order["side"] == "Buy":
                result -= quantity * Decimal("0.001")
        return result

    def get_positions(self, **query):
        net = self.net("linear")
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "side": "Buy" if net > 0 else "Sell",
                        "size": str(abs(net)),
                        "avgPrice": "79000",
                        "markPrice": "79000",
                        "leverage": "50",
                        "positionIdx": 0,
                        "updatedTime": milliseconds(),
                    }
                ]
            },
        }

    def get_wallet_balance(self, **query):
        btc = self.net("spot")
        cash_fields = {
            key: "0" for key in ("locked", "totalOrderIM", "totalPositionIM", "bonus", "spotBorrow")
        }
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "totalEquity": "100000",
                        "totalAvailableBalance": "100000",
                        "totalWalletBalance": "100000",
                        "totalMarginBalance": "100000",
                        "totalInitialMargin": "0",
                        "totalMaintenanceMargin": "0",
                        "totalPerpUPL": "0",
                        "coin": [
                            {
                                **cash_fields,
                                "coin": "USDT",
                                "equity": "100000",
                                "walletBalance": "100000",
                                "usdValue": "100000",
                            },
                            {
                                **cash_fields,
                                "coin": "BTC",
                                "equity": str(btc),
                                "walletBalance": str(btc),
                                "usdValue": str(btc * 79000),
                            },
                        ],
                    }
                ]
            },
        }

    def get_account_info(self):
        return {"retCode": 0, "result": {"marginMode": "REGULAR_MARGIN"}}


class NoMt5:
    def capability(self):
        return GatewayAdapterCapability(
            adapter="mt5_live",
            environment="live",
            configured=False,
            operational=False,
            writeEnabled=False,
            accountIds=[],
            capabilities=[],
            missingRequirements=["Isolated Bybit-only fixture"],
        )


settings = get_settings()
settings.environment = "live"
settings.gateway_name = "bybit_mt5"
settings.live_write_enabled = True
settings.live_account_allowlist = "bybit-live-main"
settings.bybit_account_ids = "bybit-live-main,bybit-monitor"
settings.bybit_read_only_account_ids = "bybit-monitor"
settings.bybit_account_credential_refs = ""
settings.bybit_credential_ref = "secret://environment/funding-contract-test"
settings.bybit_instrument_map = "XAUTUSDT=instrument_xau_usdt_perp"
settings.mt5_account_ids = ""
prefix = env_prefix_for_secret_name("funding-contract-test")
os.environ[prefix + "_API_KEY"] = "isolated-placeholder"
os.environ[prefix + "_SECRET"] = "isolated-placeholder"
clients = {account: NativeClient(account) for account in settings.bybit_accounts}
adapter = StrictBybitAcceptanceAdapter(settings)
adapter._client = lambda account_id: clients[account_id]
gateway = BybitMt5Gateway(settings, bybit=adapter, mt5=NoMt5())
app = create_app(gateway)
