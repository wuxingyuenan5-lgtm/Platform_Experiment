import json
from decimal import Decimal

import ccxt


exchange = ccxt.bybit({"enableRateLimit": False})
exchange.number = str
order_raw = {
    "orderId": "order-native-001",
    "orderLinkId": "client-native-001",
    "symbol": "BTCUSDT",
    "category": "linear",
    "side": "Buy",
    "orderType": "Limit",
    "qty": "0.123456789",
    "price": "60123.40000000",
    "avgPrice": "60120.123456789",
    "cumExecQty": "0.023456789",
    "cumExecValue": "1410.1234567890123",
    "orderStatus": "PartiallyFilled",
    "createdTime": "1784800000000",
    "updatedTime": "1784800000123",
    "timeInForce": "PostOnly",
    "reduceOnly": False,
    "leavesQty": "0.100000000",
    "rejectReason": "EC_NoError",
}
trade_raw = {
    "execId": "exec-native-001",
    "orderId": "order-native-001",
    "symbol": "BTCUSDT",
    "category": "linear",
    "side": "Buy",
    "execQty": "0.023456789",
    "execPrice": "60120.123456789",
    "execFee": "0.00000123456789",
    "feeCurrency": "USDT",
    "execTime": "1784800000456",
    "isMaker": True,
    "execType": "Trade",
}
market = {
    "id": "BTCUSDT",
    "symbol": "BTC/USDT:USDT",
    "base": "BTC",
    "quote": "USDT",
    "settle": "USDT",
    "type": "swap",
    "spot": False,
    "swap": True,
    "linear": True,
    "inverse": False,
    "contract": True,
    "contractSize": 1,
    "precision": {"amount": 0.001, "price": 0.1},
    "limits": {},
    "info": {},
}
parsed_order = exchange.parse_order(order_raw, market)
parsed_trade = exchange.parse_trade(trade_raw, market)
print(json.dumps({
    "order": {key: parsed_order.get(key) for key in (
        "id", "clientOrderId", "symbol", "side", "type", "amount", "price",
        "filled", "remaining", "average", "status", "timestamp", "datetime",
        "fee", "info",
    )},
    "trade": {key: parsed_trade.get(key) for key in (
        "id", "order", "symbol", "side", "amount", "price", "cost", "timestamp",
        "datetime", "fee", "takerOrMaker", "info",
    )},
    "decimal_checks": {
        "order_amount": str(Decimal(str(parsed_order["amount"]))),
        "order_average": str(Decimal(str(parsed_order["average"]))),
        "trade_amount": str(Decimal(str(parsed_trade["amount"]))),
        "trade_price": str(Decimal(str(parsed_trade["price"]))),
        "trade_fee": str(Decimal(str(parsed_trade["fee"]["cost"]))),
    },
}, default=str, indent=2))
