"""Browser acceptance host: fresh SQLite, fake execution runtime, fixture account reads."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app import application, live_venue_snapshot_sync
from app.config import get_settings
from app.database import connection
from app.live_venue_snapshot_sync import _persist_account_risk, _persist_venue_snapshot
from app.strategies import funding_workspace
from scripts.seed_hedge_board_e2e import main as seed

seed()  # Test mode, fresh path and isolated directory are checked before initialization.
now = datetime.now(UTC).isoformat()
with connection() as db:
    db.execute(
        "UPDATE accounts SET status='active' WHERE id IN "
        "('account_sim_usdt','account_crypto_test','account_mt5_demo')"
    )
    db.execute(
        "UPDATE strategy_instances SET status='active', trading_mode='simulation' "
        "WHERE id IN "
        "('strategy_funding_arbitrage_instance_default','strategy_cross_venue_spread_instance_default')"
    )
    db.execute(
        "UPDATE strategy_account_bindings SET status=CASE WHEN "
        "account_id='account_sim_usdt' THEN 'active' ELSE 'inactive' END WHERE "
        "strategy_instance_id='strategy_funding_arbitrage_instance_default'"
    )
    db.execute(
        "UPDATE strategy_account_bindings SET account_id='account_sim_usdt', status='active' "
        "WHERE strategy_instance_id='strategy_funding_arbitrage_instance_default' "
        "AND role='primary' AND account_id='bybit-live-main'"
    )
    db.execute(
        "UPDATE strategy_account_bindings SET status=CASE WHEN account_id IN "
        "('account_crypto_test','account_mt5_demo') THEN 'active' ELSE 'inactive' "
        "END WHERE "
        "strategy_instance_id='strategy_cross_venue_spread_instance_default'"
    )
    db.execute(
        "UPDATE strategy_account_bindings SET account_id=CASE role "
        "WHEN 'venue_a' THEN 'account_crypto_test' ELSE 'account_mt5_demo' END, "
        "status='active' WHERE strategy_instance_id="
        "'strategy_cross_venue_spread_instance_default' AND role IN ('venue_a','mt5_leg')"
    )
    db.execute(
        "UPDATE balance_snapshots SET equity='100000', "
        "available_balance='100000', as_of=?, created_at=? WHERE account_id IN "
        "('account_sim_usdt','account_crypto_test','account_mt5_demo')",
        (now, now),
    )
    db.execute(
        "INSERT INTO balance_snapshots "
        "(id,account_id,currency,equity,available_balance,source,"
        "data_quality_state,as_of,created_at) "
        "VALUES ('e2e-spot-cash','account_sim_usdt','BTC','10','10','isolated_fixture',"
        "'complete',?,?)",
        (now, now),
    )
    for account, currency in (("account_crypto_test", "USDT"), ("account_mt5_demo", "USD")):
        db.execute(
            "INSERT INTO balance_snapshots "
            "(id,account_id,currency,equity,available_balance,source,"
            "data_quality_state,as_of,created_at) "
            "VALUES (?,?,?,'100000','100000','isolated_fixture','complete',?,?)",
            (f"e2e-cross-{account}", account, currency, now, now),
        )
    for account, venue in (
        ("account_bybit_bottom_fishing", "bybit"),
        ("account_mt5_short_term_a", "mt5"),
    ):
        if not db.execute("SELECT 1 FROM accounts WHERE id=?", (account,)).fetchone():
            continue
        risk = {
            "accountId": account,
            "currency": "USD",
            "equity": "10000",
            "freeMargin": "7000",
            "margin": "3000",
            "dataQualityState": "complete",
            "asOf": now,
            "assetScope": "unified_trading" if venue == "bybit" else "mt5_trading",
            "totalAssets": "12500" if venue == "bybit" else None,
            "assetOverviewQuality": "complete" if venue == "bybit" else "not_requested",
            "assetOverviewAsOf": now,
            "assetBreakdown": [
                {
                    "accountType": "UnifiedTradingAccount",
                    "totalEquity": "10000",
                    "valuationCurrency": "USD",
                    "categories": [
                        {"category": "crypto", "equity": "8000"},
                        {"category": "stocks", "equity": "2000"},
                    ],
                },
                {"accountType": "Earn", "totalEquity": "2500", "valuationCurrency": "USD"},
            ]
            if venue == "bybit"
            else [],
        }
        _persist_account_risk(db, account, risk)
        _persist_venue_snapshot(
            db,
            account,
            {
                "accountId": account,
                "venue": venue,
                "source": "isolated_fixture",
                "asOf": now,
                "historyStart": (datetime.now(UTC) - timedelta(days=7)).isoformat(),
                "historyEnd": now,
                "dataQualityState": "complete",
                "balances": [],
                "positions": [],
                "orders": [],
                "fills": [],
                "economicEvents": [],
                "economicEventsQuality": "complete",
                "accountRisk": risk,
            },
        )
        db.execute(
            "INSERT OR REPLACE INTO account_sync_status "
            "(account_id,status,last_attempt_at,last_success_at,updated_at) VALUES "
            "(?,'ready',?,?,?)",
            (account, now, now, now),
        )

# FakeGateway exercises simulation instructions. Its UI eligibility is explicit
# fixture data, never a claim that controlled live readiness has been proven.
funding_workspace.get_funding_controlled_live_readiness = lambda **_: {
    "ready": True,
    "blockers": [],
    "source": "isolated_simulation_fixture",
}
# seed() already initializes the database. Re-running seed defaults during the
# lifespan would replace the simulation bindings prepared above.
application.initialize_database = lambda: None
# Exercise the production native-receipt collector against the same Fake Runtime.
# Only executable simulation accounts belong to this collector. The read-only
# account asset fixtures above must not be replaced by generic Fake balances.
live_venue_snapshot_sync.discover_live_accounts = lambda: [
    "account_crypto_test", "account_mt5_demo", "account_sim_usdt"
]
app = application.create_application()


@app.middleware("http")
async def isolated_response_delay(request, call_next):
    """A one-use file fixture holds the response after the real test write finishes."""
    fixture = Path(get_settings().database_path).parent / "response-delay.json"
    delay = 0
    if (
        request.method == "POST"
        and request.url.path
        in {
            "/api/v1/trading/cross-spread/lifecycle/open",
            "/api/v1/trading/funding/instructions",
        }
        and fixture.is_file()
    ):
        script = json.loads(fixture.read_text(encoding="utf-8"))
        if not script.get("consumedAt") and script.get("path") == request.url.path:
            delay = max(0, min(45, int(script["seconds"])))
            script["consumedAt"] = datetime.now(UTC).isoformat()
            fixture.write_text(json.dumps(script), encoding="utf-8")
    response = await call_next(request)
    if delay:
        await asyncio.sleep(delay)
    return response
