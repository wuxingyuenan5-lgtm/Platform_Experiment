"""Normal live admission without acceptance sessions; no Runtime/venue writes."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.auth import AuthenticationMiddleware
from app.config import get_settings
from app.database import connection, initialize_database
from app.live_trading_sessions import ensure_schema
from app.security import enforce_order_safety
from app.user_service import create_initial_ceo, issue_browser_session

STRATEGY = "strategy_funding_arbitrage_instance_default"
ACCOUNT = "account_sim_usdt"
PATH = "/api/v1/trading/funding/instructions"
RISK_PATH = "/api/v1/trading/execution-batches/funding-risk-test/risk-actions"
RECONCILE_PATH = "/api/v1/trading/orders/existing-order/venue-reconcile"
RUNTIME_RECONCILE_PATH = "/api/v1/trading/orders/existing-order/reconcile"


@pytest.fixture
def admission(monkeypatch, tmp_path):
    settings = get_settings()
    for name, value in {
        "database_path": str(tmp_path / "normal-trading.db"),
        "environment": "development",
        "auth_mode": "development",
        "live_trading_enabled": True,
        "live_session_absolute_max_order_notional": Decimal("1"),
        "live_session_absolute_max_daily_notional": Decimal("1"),
    }.items():
        monkeypatch.setattr(settings, name, value)
    initialize_database()
    ensure_schema()

    def native_specification(url, *, params, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={
                "accountId": params["accountId"],
                "symbol": "BTCUSDT",
                "instrumentType": params["instrumentType"],
                "category": params["category"],
                "dataQualityState": "complete",
                "status": "Trading",
                "minQuantity": "0.001",
                "quantityStep": "0.001",
                "priceTick": "0.01",
            },
        )

    monkeypatch.setattr("app.runtime_transport.get", native_specification)
    with connection() as db:
        db.execute("UPDATE accounts SET environment='live',status='active' WHERE id=?", (ACCOUNT,))
        db.execute(
            "UPDATE strategy_account_bindings SET status='active',capability='trade_and_read' "
            "WHERE strategy_instance_id=? AND account_id=?",
            (STRATEGY, ACCOUNT),
        )
        db.execute(
            "INSERT INTO execution_batches (id,strategy_instance_id,account_id,strategy_key,"
            "direction,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                "funding-risk-test",
                STRATEGY,
                ACCOUNT,
                "funding_arbitrage",
                "open",
                "manual_intervention",
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
    user = create_initial_ceo(username="test_owner", password="isolated test password 123!")
    issued = issue_browser_session(
        user_id=user.id, ip_address="127.0.0.1", user_agent="pytest", now=datetime.now(UTC)
    )
    app = FastAPI()

    @app.post(RECONCILE_PATH)
    @app.post(RUNTIME_RECONCILE_PATH)
    async def reconcile_existing_order():
        return {"reconciled": True}

    @app.post(PATH)
    @app.post(RISK_PATH)
    async def admit(request: Request):
        payload = await request.json()
        enforce_order_safety(
            ACCOUNT,
            "instrument_btc_usdt",
            Decimal(payload.get("quantity", "2")),
            None,
            strategy_instance_id=STRATEGY,
            symbol="BTCUSDT",
            side="buy",
            order_type="market",
            command_id="normal-command",
        )
        return {"admitted": True}

    app.add_middleware(AuthenticationMiddleware)
    with TestClient(app) as client:
        client.cookies.set(settings.session_cookie_name, issued.session_token)
        client.headers.update(
            {"Origin": settings.allowed_cors_origins[0], "X-CSRF-Token": issued.csrf_token}
        )
        yield client, user.id


@pytest.mark.parametrize(
    "role,expected", [("ceo", 200), ("tech_lead", 403), ("employee", 403), ("member", 403)]
)
@pytest.mark.parametrize("path", [RECONCILE_PATH, RUNTIME_RECONCILE_PATH])
def test_existing_order_reconciliation_uses_review_permission(admission, role, expected, path):
    client, user_id = admission
    with connection() as db:
        db.execute("UPDATE users SET role_code=? WHERE id=?", (role, user_id))
    assert client.post(path).status_code == expected


@pytest.mark.parametrize("path", [RECONCILE_PATH, RUNTIME_RECONCILE_PATH])
def test_reconciliation_keeps_csrf_and_missing_external_exception_boundary(admission, path):
    from app.auth import permission_for_request

    client, _ = admission
    client.headers.pop("X-CSRF-Token")
    assert client.post(path).status_code == 403
    assert (
        permission_for_request(
            "POST", "/api/v1/trading/orders/existing-order/resolve-missing-external"
        )
        == "admin:write"
    )


@pytest.mark.parametrize(
    "role,expected", [("ceo", 200), ("tech_lead", 403), ("employee", 403), ("member", 403)]
)
def test_controlled_strategy_risk_actions_require_ceo(admission, role, expected):
    client, user_id = admission
    with connection() as db:
        db.execute("UPDATE users SET role_code=? WHERE id=?", (role, user_id))
    assert client.post(RISK_PATH, json={}).status_code == expected


def test_ceo_market_admission_without_acceptance_window_or_notional_caps(admission):
    client, _ = admission
    assert client.post(PATH, json={}).status_code == 200
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM live_trading_session_claims").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM live_trading_sessions").fetchone()[0] == 0


@pytest.mark.parametrize("role", ["tech_lead", "employee", "member"])
def test_other_browser_roles_cannot_trade(admission, role):
    client, user_id = admission
    with connection() as db:
        db.execute("UPDATE users SET role_code=? WHERE id=?", (role, user_id))
    assert client.post(PATH, json={}).status_code == 403


def test_development_identity_cannot_trade_with_live_gate_enabled(admission):
    client, _ = admission
    client.cookies.clear()
    response = client.post(PATH, json={})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "live_authentication_required"


@pytest.mark.parametrize("failure", ["csrf", "origin", "revoked"])
def test_browser_security_still_blocks_invalid_requests(admission, failure):
    client, user_id = admission
    if failure == "csrf":
        client.headers.pop("X-CSRF-Token")
    elif failure == "origin":
        client.headers["Origin"] = "https://untrusted.invalid"
    else:
        with connection() as db:
            db.execute("UPDATE users SET auth_version=auth_version+1 WHERE id=?", (user_id,))
    assert client.post(PATH, json={}).status_code in {401, 403}


@pytest.mark.parametrize(
    "scope,scope_id", [("global", "*"), ("strategy", STRATEGY), ("account", ACCOUNT)]
)
def test_kill_switch_still_blocks_without_live_session(admission, scope, scope_id):
    client, _ = admission
    with connection() as db:
        db.execute(
            "INSERT OR REPLACE INTO trading_kill_switches "
            "(scope_type,scope_id,enabled,reason,actor,version,updated_at) VALUES (?,?,1,?,?,1,?)",
            (scope, scope_id, "test stop", "test-owner", datetime.now(UTC).isoformat()),
        )
    response = client.post(PATH, json={})
    assert response.status_code == 423
    assert "kill switch" in response.json()["detail"]


def test_account_binding_and_venue_step_still_apply(admission):
    client, _ = admission
    assert client.post(PATH, json={"quantity": "0.000001"}).status_code == 422
    with connection() as db:
        db.execute(
            "UPDATE strategy_account_bindings SET capability='read_only' WHERE account_id=?",
            (ACCOUNT,),
        )
    assert client.post(PATH, json={}).status_code == 403


@pytest.mark.parametrize("status", ["open", "accepted"])
def test_unresolved_reconciliation_still_blocks_without_live_session(admission, status):
    client, _ = admission
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            "INSERT INTO venue_reconciliation_runs "
            "(id,idempotency_key,payload_hash,strategy_instance_id,account_id,run_type,source,status,"
            "order_count,fill_count,position_count,balance_count,"
            "fact_count,difference_count,started_at) "
            "VALUES ('run','run','hash',?,?,'intraday','test','differences',0,0,0,0,0,1,?)",
            (STRATEGY, ACCOUNT, now),
        )
        db.execute(
            "INSERT INTO reconciliation_differences "
            "(id,run_id,difference_key,difference_type,entity_type,local_value_json,"
            "external_value_json,status,created_at) "
            "VALUES ('difference','run','difference','quantity_mismatch','position','{}','{}',?,?)",
            (status, now),
        )
    response = client.post(PATH, json={})
    assert response.status_code == 423
    assert "reconciliation differences" in response.json()["detail"]


def test_closed_live_gate_does_not_grant_development_ceo_authority(admission, monkeypatch):
    client, _ = admission
    monkeypatch.setattr(get_settings(), "default_trading_environment", "live")
    monkeypatch.setattr(get_settings(), "live_trading_enabled", False)
    client.cookies.clear()
    response = client.post(PATH, json={})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ceo_trade_authority_required"


@pytest.mark.parametrize("changed_field", [None, "quantity", "accountId", "currency"])
def test_accepted_native_time_only_correction_matches_ingestion_gate(admission, changed_field):
    client, _ = admission
    now = datetime.now(UTC).isoformat()
    original = {
        "accountId": ACCOUNT,
        "source": "native",
        "externalFillId": "fill",
        "quantity": "1",
        "currency": "USDT",
        "occurredAt": "2026-09-09T12:00:00Z",
    }
    corrected = {**original, "occurredAt": "2026-09-09T15:00:00Z"}
    if changed_field:
        corrected[changed_field] = "changed"
    with connection() as db:
        db.execute(
            "INSERT INTO venue_reconciliation_runs(id,idempotency_key,payload_hash,"
            "strategy_instance_id,account_id,run_type,source,status,order_count,fill_count,"
            "position_count,balance_count,fact_count,difference_count,started_at) "
            "VALUES ('time','time','hash',?,?,'intraday','native','differences',0,0,0,0,0,1,?)",
            (STRATEGY, ACCOUNT, now),
        )
        db.execute(
            "INSERT INTO reconciliation_differences(id,run_id,difference_key,difference_type,"
            "entity_type,external_reference,local_value_json,external_value_json,status,"
            "resolution_actor,resolved_at,created_at) VALUES ('time','time','time',"
            "'timestamp_mismatch','venue_event','trade_fill:fill',?,?,'accepted','owner',?,?)",
            (json.dumps(original), json.dumps(corrected), now, now),
        )
    response = client.post(PATH, json={})
    assert response.status_code == (423 if changed_field else 200)


def test_batch_checks_second_account_before_dispatching_first_leg(admission, monkeypatch):
    from app import execution_batches
    from app.schemas import BatchLegRequest, CreateExecutionBatchRequest

    client, _ = admission
    # Install a real blocking Difference on the second leg's live account.
    test_unresolved_reconciliation_still_blocks_without_live_session(admission, "open")
    calls = []
    monkeypatch.setattr(execution_batches, "create_trade_command", lambda r: calls.append(r))
    monkeypatch.setattr(execution_batches, "validate_trade_command_catalog", lambda r: None)
    with connection() as db:
        other = db.execute("SELECT id FROM accounts WHERE id!=? LIMIT 1", (ACCOUNT,)).fetchone()[0]
        db.execute("UPDATE accounts SET environment='simulation' WHERE id=?", (other,))
    request = CreateExecutionBatchRequest(
        idempotencyKey="preflight-both",
        strategyInstanceId=STRATEGY,
        accountId=other,
        strategyKey="funding_arbitrage",
        direction="open",
        legs=[
            BatchLegRequest(
                role="first",
                accountId=other,
                instrumentId="instrument_btc_usdt",
                symbol="BTCUSDT",
                side="buy",
                orderType="market",
                quantity="1",
            ),
            BatchLegRequest(
                role="second",
                accountId=ACCOUNT,
                instrumentId="instrument_btc_usdt",
                symbol="BTCUSDT",
                side="sell",
                orderType="market",
                quantity="1",
            ),
        ],
    )
    from fastapi import HTTPException

    with pytest.raises(HTTPException, match="reconciliation differences"):
        execution_batches.create_execution_batch(request)
    assert not calls
