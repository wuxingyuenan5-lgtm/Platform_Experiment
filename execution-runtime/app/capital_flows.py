"""Read-only capital movements, separate from trading/accounting events."""

from datetime import UTC, datetime
from decimal import Decimal

from app.gateway_errors import GatewayConfigurationError


def bybit_capital_flows(adapter, account_id, start_time, end_time):
    uta = adapter._snapshot_pages(
        account_id,
        "get_transaction_log",
        {
            "accountType": "UNIFIED",
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": 50,
        },
    )
    query = {
        "createTimeFrom": str(int(start_time.timestamp())),
        "createTimeTo": str(int(end_time.timestamp())),
        "limit": "100",
    }
    funding, cursors = [], set()
    for _ in range(100):
        response = adapter._read_with_retry(
            account_id,
            lambda client: client._submit_request(
                method="GET",
                path=client.endpoint + "/v5/asset/fundinghistory",
                query=query,
                auth=True,
            ),
        )
        adapter._require_success(response, "Bybit funding history query failed")
        result = response.get("result") or {}
        funding.extend(result.get("list") or [])
        cursor = str(result.get("nextPageCursor") or "")
        if not cursor:
            break
        if cursor in cursors:
            raise GatewayConfigurationError("Capital flow pagination did not advance")
        cursors.add(cursor)
        query["cursor"] = cursor
    else:
        raise GatewayConfigurationError("Capital flow pagination limit exceeded")
    events = []
    zero = Decimal(0)
    income = {
        "TRADE",
        "SETTLEMENT",
        "FUNDING",
        "INTEREST",
        "BORROW",
        "REPAY",
        "BYUSDT_INTEREST",
        "AIRDROP",
        "BONUS",
        "FEE_REFUND",
        "CASHBACK",
        "EARNING_REDEMPTION_BUY",
        "EARNING_REDEMPTION_SELL",
    }
    staking = {
        "FLEXIBLE_STAKING_SUBSCRIPTION",
        "FLEXIBLE_STAKING_REDEMPTION",
        "FIXED_STAKING_SUBSCRIPTION",
        "FIXED_STAKING_REDEMPTION",
        "BYUSDT_MINT",
        "BYUSDT_REDEEM",
    }
    for row in uta:
        kind = str(row.get("type", ""))
        amount = Decimal(str(row.get("change") or "0"))
        stamp = datetime.fromtimestamp(int(row["transactionTime"]) / 1000, UTC)
        trading = (
            amount
            if kind in staking | {"TRANSFER_IN", "TRANSFER_OUT"}
            else zero
            if kind in income
            else None
        )
        # Only matched Funding/UTA movements are proven internal to the overview.
        internal = kind in staking or any(
            f.get("descriptionEn")
            in {"Transfer from Unified Trading Account", "Transfer to Unified Trading Account"}
            and f.get("currency") == row.get("currency")
            and Decimal(str(f["txnAmt"])) == abs(amount)
            and abs(int(f["createTime"]) - stamp.timestamp()) <= 2
            and ((f.get("ioDirection") == "I") == (amount < 0))
            for f in funding
        )
        total = zero if kind in income or internal else None
        for scope, value in (("unified_trading", trading), ("full_account", total)):
            events.append(
                _event(
                    "uta:" + str(row["id"]), scope, stamp, str(row["currency"]), value, kind, row
                )
            )
    for row in funding:
        kind, desc = str(row.get("showBusiType", "")), str(row.get("descriptionEn", ""))
        amount = Decimal(str(row["txnAmt"])) * (1 if row["ioDirection"] == "I" else -1)
        if kind in {"fundingAccountRecordTypeWithdraw", "fundingAccountRecordTypeDeposit"}:
            value = amount
        elif kind in {"fundingAccountRecordEarn", "fundingAccountRecordAirdrop"} or desc in {
            "Transfer from Unified Trading Account",
            "Transfer to Unified Trading Account",
            "Transfer in From MT5",
            "Transfer out To MT5",
        }:
            value = zero
        else:
            value = None
        events.append(
            _event(
                "fund:" + str(row["currcCursor"]),
                "full_account",
                datetime.fromtimestamp(int(row["createTime"]), UTC),
                str(row["currency"]),
                value,
                kind,
                row,
            )
        )
    return {
        "accountId": account_id,
        "startTime": start_time,
        "endTime": end_time,
        "scopes": ["unified_trading", "full_account"],
        "events": events,
    }


def _event(identity, scope, stamp, currency, value, kind, raw):
    if not identity.split(":", 1)[-1] or not currency:
        raise GatewayConfigurationError("Capital movement identity/currency missing")
    return {
        "externalEventId": identity,
        "assetScope": scope,
        "occurredAt": stamp,
        "currency": currency,
        "amount": str(value) if value is not None else None,
        "eventType": kind,
        "raw": raw,
    }


def mt5_capital_flows(adapter, account_id, start_time, end_time):
    adapter._assert_account(account_id)
    mt5 = adapter._connect()
    deals = mt5.history_deals_get(start_time, end_time)
    if deals is None:
        raise GatewayConfigurationError("MT5 capital movement history unavailable")
    currency = adapter._account_currency(mt5)
    events = []
    for deal in deals:
        kind = int(deal.type)
        # Buy/sell and fees, dividends and interest are performance, not investor capital.
        if kind in {0, 1, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17}:
            value = Decimal(0)
        elif kind in {2, 3}:  # balance / credit, signed account-reported amount
            value = Decimal(str(deal.profit))
        else:
            value = None
        events.append(
            _event(
                "deal:" + str(deal.ticket),
                "mt5_trading",
                adapter._deal_time(deal),
                currency,
                value,
                str(kind),
                {"ticket": str(deal.ticket), "type": kind, "profit": str(deal.profit)},
            )
        )
    return {
        "accountId": account_id,
        "startTime": start_time,
        "endTime": end_time,
        "scopes": ["mt5_trading"],
        "events": events,
    }
