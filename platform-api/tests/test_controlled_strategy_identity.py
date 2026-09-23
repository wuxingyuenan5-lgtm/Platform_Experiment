"""Real HTTP denial before orders, reservations or Runtime calls; isolated SQLite."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from test_auth_rbac import auth_headers, configure_live_auth

from app.config import get_settings
from app.database import connection
from app.main import app
from app.user_service import create_initial_ceo, issue_browser_session


def clone_row(db, table, original, **changes):
    row = dict(db.execute(f"SELECT * FROM {table} WHERE id=?", (original,)).fetchone())
    row.update(changes)
    db.execute(
        f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
        tuple(row.values()),
    )


def counts():
    tables = (
        "orders",
        "trade_commands",
        "execution_batches",
        "strategy_runs",
        "execution_resource_claims",
        "execution_balance_reservations",
    )
    with connection() as db:
        return {t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}


@pytest.mark.parametrize("key", ["funding_arbitrage", "cross_venue_spread"])
@pytest.mark.parametrize("role", ["ceo", "tech_lead", "employee", "member", "api_admin"])
def test_nondefault_instances_cannot_bypass_controlled_entrypoints(
    monkeypatch, tmp_path, key, role
):
    configure_live_auth(monkeypatch, tmp_path)
    instance = "renamed-second-instance"
    account = "account_sim_usdt"

    def unexpected_effect(*args, **kwargs):
        pytest.fail("denied request reached an order or Runtime side effect")

    # Spy at the actual HTTP -> business boundary as well as persisted effects.
    monkeypatch.setattr("app.trading_routes.create_trade_command", unexpected_effect)
    monkeypatch.setattr("app.trading_routes.create_execution_batch", unexpected_effect)
    monkeypatch.setattr("app.trading_routes.submit_order", unexpected_effect)
    monkeypatch.setattr("app.catalog_routes.create_strategy_run", unexpected_effect)
    monkeypatch.setattr("app.catalog_routes.create_instruction", unexpected_effect)

    with TestClient(app) as client:
        with connection() as db:
            clone_row(db, "strategy_instances", f"strategy_{key}_instance_default", id=instance)
            # Only the new instance controls this account: a default-ID check cannot pass.
            db.execute(
                "UPDATE strategy_account_bindings SET status='inactive' WHERE account_id=?",
                (account,),
            )
            db.execute(
                "INSERT INTO strategy_account_bindings "
                "(id,strategy_instance_id,account_id,role,capability,status,created_at) "
                "VALUES ('new-binding',?,?, 'primary','trade_and_read','active',?)",
                (instance, account, datetime.now(UTC).isoformat()),
            )
        if role == "api_admin":
            client.headers.update(auth_headers("admin-token"))
        else:
            user = create_initial_ceo(
                username="isolated-owner", password="isolated test password 123!"
            )
            with connection() as db:
                db.execute("UPDATE users SET role_code=? WHERE id=?", (role, user.id))
            session = issue_browser_session(
                user_id=user.id, ip_address="127.0.0.1", user_agent="pytest", now=datetime.now(UTC)
            )
            client.cookies.set(get_settings().session_cookie_name, session.session_token)
            client.headers.update(
                {
                    "Origin": get_settings().allowed_cors_origins[0],
                    "X-CSRF-Token": session.csrf_token,
                }
            )

        order = dict(
            accountId=account,
            instrumentId="instrument_btc_usdt",
            symbol="BTCUSDT",
            side="buy",
            orderType="market",
            quantity="1",
        )
        legs = [{**order, "role": "perpetual"}, {**order, "side": "sell", "role": "spot"}]
        batch = dict(
            idempotencyKey="denied-batch",
            strategyInstanceId=instance,
            strategyKey=key,
            direction="OPEN",
            legs=legs,
        )
        requests = [
            (
                "/api/v1/trading/commands",
                {**order, "strategyInstanceId": instance, "idempotencyKey": "denied-command"},
            ),
            ("/api/v1/trading/execution-batches", batch),
            (
                "/api/v1/trading/execution-batches",
                {k: v for k, v in batch.items() if k != "strategyInstanceId"},
            ),
            ("/api/v1/trading/orders", order),
            (
                f"/api/v1/strategies/{instance}/instructions",
                dict(idempotencyKey="denied-instruction", action="open", parameters={}),
            ),
            (
                f"/api/v1/strategies/instances/{instance}/runs",
                dict(idempotencyKey="denied-run", direction="OPEN", legs=legs),
            ),
        ]
        before = counts()
        for path, body in requests:
            response = client.post(path, json=body)
            assert response.status_code == 403, (role, path, response.text)
            assert counts() == before


@pytest.mark.parametrize("key", ["funding_arbitrage", "cross_venue_spread"])
def test_risk_authority_resolves_persisted_instance_type(monkeypatch, tmp_path, key):
    from app.auth import _record_requires_ceo_trade_authority

    configure_live_auth(monkeypatch, tmp_path)
    with TestClient(app):
        with connection() as db:
            clone_row(
                db, "strategy_instances", f"strategy_{key}_instance_default", id="second-instance"
            )
            db.execute("CREATE TABLE authority_test (id TEXT, strategy_instance_id TEXT)")
            db.execute("INSERT INTO authority_test VALUES ('batch','second-instance')")
        assert _record_requires_ceo_trade_authority(
            "SELECT strategy_instance_id FROM authority_test WHERE id=?", "batch"
        )
