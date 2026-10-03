from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import get_settings
from app.database import connection
from app.main import app
from app.strategies import funding_exit_repository as repo
from app.strategies import funding_exit_service as service
from app.strategies.funding_runner import run_funding_instruction_monitor as actual_funding_runner
from app.strategies.funding_schemas import FundingExitPlanRequest
from app.strategies.instruction_service import execute_instruction
from tests.test_funding_phase2_orchestration import (
    ACCOUNT_ID,
    _make_instruction,
    _seed_environment,
    _set_quote,
)
from tests.test_funding_phase2_orchestration import (
    runtime as runtime,
)

pytestmark = pytest.mark.integration


def context():
    result = {
        "accountId": ACCOUNT_ID,
        "dataQualityState": "complete",
        "spotSymbol": "BTCUSDT",
        "perpetualSymbol": "BTCUSDT",
        "controlledLiveReadiness": {"ready": True},
    }
    for leg, category, bid, ask in (
        ("spot", "spot", "101", "102"),
        ("perpetual", "linear", "99", "100"),
    ):
        result[f"{leg}Quote"] = {
            "accountId": ACCOUNT_ID,
            "category": category,
            "symbol": "BTCUSDT",
            "bid": bid,
            "ask": ask,
            "dataQualityState": "complete",
            "sourceAsOf": datetime.now(UTC).isoformat(),
        }
    return result


@pytest.fixture
def plan(tmp_path, monkeypatch):
    _seed_environment(tmp_path, "http://127.0.0.1:1")
    open_id = _make_instruction("exit-open", execution_policy="market")
    group = {
        "openInstructionId": open_id,
        "isAbnormal": False,
        "lifecycleState": "active",
        "remainingClosableQuantity": "1",
        "pendingCloseQuantity": "0",
        "resultUnknownReservedQuantity": "0",
        "spotSymbol": "BTCUSDT",
        "perpetualSymbol": "BTCUSDT",
    }
    monkeypatch.setattr(service, "list_funding_position_groups", lambda: [group])
    service.configure_exit(
        open_id,
        FundingExitPlanRequest(
            expectedRevision=0, enabled=True, takeProfitSpread="1", stopLossSpread="-2"
        ),
        actor="test-ceo",
    )
    return open_id, group


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"takeProfitSpread": "NaN"},
        {"takeProfitSpread": "Infinity"},
        {"takeProfitSpread": "-2", "stopLossSpread": "-1"},
    ],
)
def test_invalid_thresholds(payload):
    with pytest.raises(ValidationError):
        FundingExitPlanRequest(expectedRevision=0, enabled=True, **payload)


def test_quote_direction_and_thresholds():
    quote = context()
    assert service.closing_spread(quote, ACCOUNT_ID, now=datetime.now(UTC)) == 1
    assert (
        service._trigger_reason({"take_profit_spread": "1", "stop_loss_spread": "-2"}, Decimal("1"))
        == "take_profit"
    )
    assert (
        service._trigger_reason(
            {"take_profit_spread": "1", "stop_loss_spread": "-2"}, Decimal("-2")
        )
        == "stop_loss"
    )


@pytest.mark.parametrize("fault", ["stale", "future", "crossed", "account", "category", "missing"])
def test_bad_quote_cannot_claim_or_dispatch(plan, monkeypatch, fault):
    quote = context()
    leg = quote["spotQuote"]
    if fault in ("stale", "future"):
        leg["sourceAsOf"] = (
            datetime.now(UTC) + timedelta(seconds=-15 if fault == "stale" else 15)
        ).isoformat()
    elif fault == "crossed":
        leg["bid"] = "103"
    elif fault in ("account", "category"):
        leg["accountId" if fault == "account" else "category"] = "other"
    else:
        leg["dataQualityState"] = "partial"
    monkeypatch.setattr(service, "get_funding_execution_context", lambda **_: quote)
    assert not service.evaluate_exit_plans()
    assert repo.list_plans()[0]["close_key"] is None
    assert repo.list_plans()[0]["last_error"]


def test_off_and_abnormal_cannot_claim(plan, monkeypatch):
    monkeypatch.setattr(
        service, "get_funding_execution_context", lambda **_: pytest.fail("must not read")
    )
    get_settings().live_trading_enabled = False
    assert service.evaluate_exit_plans()
    get_settings().live_trading_enabled = True
    plan[1]["isAbnormal"] = True
    assert service.evaluate_exit_plans()
    assert repo.list_plans()[0]["close_key"] is None


def test_revision_disable_and_concurrent_claim(plan):
    open_id, _ = plan
    old = repo.list_plans()[0]
    with pytest.raises(ValueError, match="刷新"):
        repo.save_plan(
            open_id,
            ACCOUNT_ID,
            FundingExitPlanRequest(expectedRevision=0, enabled=False),
            actor="ceo",
        )
    repo.save_plan(
        open_id, ACCOUNT_ID, FundingExitPlanRequest(expectedRevision=1, enabled=False), actor="ceo"
    )
    assert repo.claim_trigger(old, {}) is None
    repo.save_plan(
        open_id,
        ACCOUNT_ID,
        FundingExitPlanRequest(expectedRevision=2, enabled=True, takeProfitSpread="1"),
        actor="ceo",
    )
    current = repo.list_plans()[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: repo.claim_trigger(current, {"spread": "1"}), range(2)))
    assert sum(item is not None for item in outcomes) == 1
    with pytest.raises(ValueError, match="已触发"):
        repo.save_plan(
            open_id,
            ACCOUNT_ID,
            FundingExitPlanRequest(expectedRevision=3, enabled=False),
            actor="ceo",
        )


def test_crash_after_claim_requires_fresh_market_and_original_group(plan, monkeypatch):
    original = repo.list_plans()[0]
    repo.claim_trigger(
        original, {"quantity": "1", "spotSymbol": "BTCUSDT", "perpetualSymbol": "BTCUSDT"}
    )
    quote = context()
    quote["spotQuote"]["bid"] = "99"
    monkeypatch.setattr(service, "get_funding_execution_context", lambda **_: quote)
    monkeypatch.setattr(
        service, "submit_funding_instruction", lambda **_: pytest.fail("stale trigger dispatched")
    )
    assert not service.evaluate_exit_plans()
    assert "未达到" in repo.list_plans()[0]["last_error"]
    plan[1]["remainingClosableQuantity"] = "0.5"
    assert not service.evaluate_exit_plans()
    assert "原持仓已变化" in repo.list_plans()[0]["last_error"]


def test_automatic_close_uses_real_workflow_and_recovers_lost_response(
    runtime, tmp_path, monkeypatch
):
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    open_id = _make_instruction("auto-close-open", execution_policy="market")
    assert execute_instruction(open_id).status == "hedged"
    assert execute_instruction(open_id).status == "completed"
    from app.strategies.domain import ExecutionPlan
    from app.strategies.plan_service import validate_funding_close_capacity

    with connection() as db:
        original = ExecutionPlan.model_validate_json(
            db.execute(
                "SELECT execution_plan_json FROM strategy_runs WHERE id=?", (open_id,)
            ).fetchone()[0]
        )
        foreign = original.model_copy(
            update={
                "legs": tuple(
                    leg.model_copy(update={"account_id": "different-account"})
                    for leg in original.legs
                )
            }
        )
        with pytest.raises(HTTPException, match="original accounts"):
            validate_funding_close_capacity(
                db, service.STRATEGY_INSTANCE_ID, {"targetOpenInstructionId": open_id}, foreign
            )
        now = datetime.now(UTC).isoformat()
        db.execute(
            "INSERT INTO balance_snapshots(id,account_id,currency,equity,available_balance,"
            "source,data_quality_state,as_of,created_at) VALUES (?,?,'BTC','1','1',"
            "'fake_venue_snapshot','complete',?,?)",
            ("btc", ACCOUNT_ID, now, now),
        )
    service.configure_exit(
        open_id,
        FundingExitPlanRequest(expectedRevision=0, enabled=True, takeProfitSpread="1"),
        actor="ceo-test",
    )
    monkeypatch.setattr(service, "get_funding_execution_context", lambda **_: context())
    submit = service.submit_funding_instruction

    def lost(**kwargs):
        submit(**kwargs)
        raise TimeoutError("response lost after instruction publication")

    monkeypatch.setattr(service, "submit_funding_instruction", lost)
    assert not service.evaluate_exit_plans()
    monkeypatch.setattr(
        service, "submit_funding_instruction", lambda **_: pytest.fail("duplicate publication")
    )
    assert service.evaluate_exit_plans()
    close_id = repo.list_plans()[0]["close_instruction_id"]
    assert close_id
    assert execute_instruction(close_id).status == "hedged"
    assert execute_instruction(close_id).status == "completed"
    assert service.evaluate_exit_plans()
    with connection() as db:
        assert db.execute("SELECT count(*) FROM trade_commands").fetchone()[0] == 4
        assert (
            db.execute("SELECT count(*) FROM strategy_runs WHERE action='close'").fetchone()[0] == 1
        )


def test_configuration_requires_ceo_session_and_csrf(plan, authorize_funding_ceo):
    get_settings().auth_mode = "api_key"
    url = f"/api/v1/trading/funding/exit-plans/{plan[0]}"
    payload = {"enabled": False, "expectedRevision": 1}
    client = TestClient(app)
    authorize_funding_ceo(client)
    assert TestClient(app).patch(url, json=payload).status_code == 401
    csrf = client.headers.pop("X-CSRF-Token")
    assert client.patch(url, json=payload).status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    assert client.patch(url, json=payload).status_code == 200
    assert not repo.list_plans()[0]["enabled"]


def test_submission_returns_durable_identity_while_runner_is_blocked(
    runtime, tmp_path, monkeypatch, authorize_funding_ceo
):
    import time
    from threading import Event

    from app.strategies import funding_runner

    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    entered, release = Event(), Event()
    original_tick = funding_runner.execute_instruction

    def delayed_tick(identity):
        entered.set()
        assert release.wait(10)
        return original_tick(identity)

    monkeypatch.setattr(funding_runner, "execute_instruction", delayed_tick)
    monkeypatch.setattr(funding_runner, "run_funding_instruction_monitor", actual_funding_runner)
    payload = {
        "idempotencyKey": "fast-durable-receipt", "action": "open",
        "perpetualSymbol": "BTCUSDT", "spotSymbol": "BTCUSDT",
        "quantity": "1", "executionPolicy": "market",
    }
    with TestClient(app) as client:
        authorize_funding_ceo(client)
        try:
            response = client.post("/api/v1/trading/funding/instructions", json=payload)
            assert response.status_code == 200, response.text
            received = response.json()
            assert received["workspaceState"]["executionState"] == "accepted"
            identity = received["instruction"]["instructionId"]
            assert entered.wait(3)
            repeated = client.post("/api/v1/trading/funding/instructions", json=payload)
            assert repeated.status_code == 200, repeated.text
            assert repeated.json()["instruction"]["instructionId"] == identity
            with connection() as db:
                assert db.execute("SELECT count(*) FROM trade_commands").fetchone()[0] == 0
                assert db.execute("SELECT count(*) FROM strategy_runs").fetchone()[0] == 1
        finally:
            release.set()
        for _ in range(50):
            current = client.get("/api/v1/trading/funding/instructions/" + identity).json()
            if current["instruction"]["status"] == "completed":
                break
            time.sleep(0.1)
        assert current["instruction"]["status"] == "completed", current
        with connection() as db:
            assert db.execute("SELECT count(*) FROM trade_commands").fetchone()[0] == 2


def test_disabled_admission_cannot_leave_a_dormant_close(plan, monkeypatch):
    from app.strategies import funding_workspace as workspace

    open_id, group = plan
    monkeypatch.setattr(workspace, "_funding_group_snapshot", lambda **_: group)
    monkeypatch.setattr(workspace, "funding_account_binding", lambda *_: {
        "trading_mode": "live", "account_id": ACCOUNT_ID,
    })
    monkeypatch.setattr(workspace, "get_funding_controlled_live_readiness", lambda **_: {
        "ready": False, "blockedMessage": "writes disabled",
    })
    with pytest.raises(HTTPException, match="writes disabled") as rejected:
        workspace.submit_funding_instruction(
            action="close", idempotency_key="blocked-close", perpetual_symbol="BTCUSDT",
            spot_symbol="BTCUSDT", quantity=Decimal("1"), requested_by="owner",
            target_open_instruction_id=open_id, execution_policy="market",
        )
    assert rejected.value.status_code == 423
    with connection() as db:
        assert (
            db.execute("SELECT count(*) FROM strategy_runs WHERE action='close'").fetchone()[0] == 0
        )
