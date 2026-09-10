"""Funding HTTP path through the production multi-account Bybit adapter, no venue network."""

import json
import os
import subprocess
import time
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient
from test_funding_phase2_orchestration import (
    INSTANCE_ID,
    RUNTIME_DIR,
    RUNTIME_PYTHON,
    _age_attempt,
    _free_port,
    _seed_environment,
    _wait_runtime_ready,
)

from app.config import get_settings
from app.database import connection
from app.live_venue_snapshot_sync import _persist_balances
from app.main import app
from app.strategies.instruction_service import execute_instruction

pytestmark = pytest.mark.integration
ENDPOINT = "/api/v1/trading/funding/instructions"


@pytest.fixture
def bybit_contract(tmp_path, monkeypatch, authorize_funding_ceo):
    fixture_dir = tmp_path / "sdk"
    fixture_dir.mkdir()
    port = _free_port()
    env = dict(os.environ)
    env.update(
        VG_RUNTIME_GATEWAY_NAME="fake",
        VG_RUNTIME_LIVE_WRITE_ENABLED="false",
        VG_RUNTIME_JOURNAL_PATH=str(fixture_dir / "runtime.db"),
        FUNDING_BYBIT_FIXTURE_DIR=str(fixture_dir),
    )
    log = fixture_dir / "runtime.log"
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [
                str(RUNTIME_PYTHON),
                "-m",
                "uvicorn",
                "--app-dir",
                "tests",
                "funding_bybit_runtime:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            cwd=RUNTIME_DIR,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        runtime = f"http://127.0.0.1:{port}"
        try:
            assert _wait_runtime_ready(process, runtime), log.read_text(encoding="utf-8")
            _seed_environment(tmp_path, runtime)
            monkeypatch.setattr(get_settings(), "research_refresh_enabled", False)
            monkeypatch.setattr(get_settings(), "cross_spread_exit_monitor_enabled", False)
            with connection() as db:
                db.execute(
                    "UPDATE strategy_instances SET trading_mode='live' WHERE id=?", (INSTANCE_ID,)
                )
                db.execute("UPDATE accounts SET status='active' WHERE id='bybit-live-main'")
                now = datetime.now(UTC).isoformat()
                db.execute(
                    "INSERT INTO balance_snapshots(id,account_id,currency,equity,available_balance,"
                    "source,data_quality_state,as_of,created_at) "
                    "VALUES ('contract-cash','bybit-live-main','USDT','100000','100000',"
                    "'isolated_fixture','complete',?,?)",
                    (now, now),
                )
            with TestClient(app) as client:
                authorize_funding_ceo(client)
                yield client, runtime, fixture_dir
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def writes(directory):
    path = directory / "sdk-writes.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def submit(client, *, key, action="open", quantity="0.002", policy="market", target=None):
    return client.post(
        ENDPOINT,
        json={
            "idempotencyKey": key,
            "action": action,
            "perpetualSymbol": "BTCUSDT",
            "spotSymbol": "BTCUSDT",
            "quantity": quantity,
            "executionPolicy": policy,
            **({"perpetualLimitPrice": "79000"} if policy == "fok" else {}),
            **({"targetOpenInstructionId": target} if target else {}),
        },
    )


def finish(client, result):
    identity = result["instruction"]["instructionId"]
    for _ in range(3):
        execute_instruction(identity)
        latest = client.get(ENDPOINT + "/" + identity).json()
        if latest["instruction"]["status"] == "completed":
            # Read the real adapter's coin availability into the same persisted
            # balance boundary used by the background snapshot collector.
            with httpx.Client(trust_env=False) as native:
                balances = native.get(
                    get_settings().runtime_base_url + "/venue/balances",
                    params={"accountId": "bybit-live-main"},
                )
                balances.raise_for_status()
            with connection() as db:
                _persist_balances(db, "bybit-live-main", balances.json())
            return latest
    pytest.fail(str(latest))


@pytest.mark.parametrize("policy", ["market", "fok", "post_only_chase"])
def test_full_bybit_path_open_partial_close_full_close(bybit_contract, policy):
    client, runtime, directory = bybit_contract
    response = submit(client, key="bybit-open", quantity="0.003", policy=policy)
    assert response.status_code == 200, response.text
    opened = finish(client, response.json())
    target = opened["instruction"]["instructionId"]
    sent = writes(directory)
    assert [(r["category"], r["side"]) for r in sent] == [("linear", "Sell"), ("spot", "Buy")]
    assert {r["account"] for r in sent} == {"bybit-live-main"}
    assert sent[0]["qty"] == "0.002"
    assert sent[1]["qty"] == "0.003" and sent[1]["marketUnit"] == "baseCoin"
    for key in ("partial-close", "full-close"):
        closed = submit(
            client, key=key, action="close", quantity="0.001", target=target, policy=policy
        )
        assert closed.status_code == 200, closed.text
        finish(client, closed.json())
    sent = writes(directory)
    assert len(sent) == 6
    assert all(sent[index]["reduceOnly"] for index in (2, 4))
    assert [sent[index]["qty"] for index in (3, 5)] == ["0.001498", "0.001499"]
    assert client.get("/api/v1/trading/funding/positions").json() == []
    with httpx.Client(trust_env=False) as native:
        assert (
            native.get(runtime + "/venue/positions", params={"accountId": "bybit-live-main"}).json()
            == []
        )


def test_minimum_fee_adjusted_open_close_keeps_sub_step_dust(bybit_contract):
    client, runtime, directory = bybit_contract
    response = submit(client, key="minimum-net-open", quantity="0.001002")
    assert response.status_code == 200, response.text
    opened = finish(client, response.json())
    target = opened["instruction"]["instructionId"]
    group = next(
        row for row in client.get("/api/v1/trading/funding/positions").json()
        if row["openInstructionId"] == target
    )
    assert Decimal(group["remainingSpotQuantity"]) == Decimal("0.001000998")
    assert Decimal(group["remainingClosableQuantity"]) == Decimal("0.001")
    assert not group["isAbnormal"]
    response = submit(
        client, key="minimum-net-close", action="close", quantity="0.001", target=target
    )
    assert response.status_code == 200, response.text
    finish(client, response.json())
    sent = writes(directory)
    assert [(row["category"], Decimal(row["qty"])) for row in sent] == [
        ("linear", Decimal("0.001")), ("spot", Decimal("0.001002")),
        ("linear", Decimal("0.001")), ("spot", Decimal("0.001000")),
    ]
    assert sent[2]["reduceOnly"] is True
    with httpx.Client(trust_env=False) as native:
        assert native.get(
            runtime + "/venue/positions", params={"accountId": "bybit-live-main"}
        ).json() == []
        balances = native.get(
            runtime + "/venue/balances", params={"accountId": "bybit-live-main"}
        ).json()
    btc = next(row for row in balances if row["currency"] == "BTC")
    assert Decimal(btc["equity"]) == Decimal("0.000000998")


@pytest.mark.parametrize("failure", ["fail_fill_query", "reject_spot_order"])
def test_single_leg_failure_exposes_risk_then_flattens_once(bybit_contract, failure):
    client, runtime, directory = bybit_contract
    (directory / "controls.json").write_text(json.dumps({failure: True}))
    response = submit(client, key="bybit-failure")
    assert response.status_code == 200, response.text
    result = response.json()
    batch = result["instruction"]["executionBatchId"]
    assert result["instruction"]["status"] == "manual_intervention"
    risk = client.get(f"/api/v1/trading/execution-batches/{batch}/risk").json()
    assert risk["riskStatus"] == "escalated"
    assert Decimal(risk["residualExposureNotional"]) > 0
    before = len(writes(directory))
    (directory / "controls.json").write_text("{}")
    payload = {"idempotencyKey": "owner-flatten", "action": "flatten_filled_legs", "actor": "owner"}
    route = f"/api/v1/trading/execution-batches/{batch}/risk-actions"
    flattened = client.post(route, json=payload)
    assert flattened.status_code == 200, flattened.text
    assert flattened.json()["status"] == "completed", flattened.text
    assert len(writes(directory)) == before + 1
    assert writes(directory)[-1]["reduceOnly"] is True
    assert client.post(route, json=payload).json() == flattened.json()
    assert len(writes(directory)) == before + 1
    assert client.get("/api/v1/trading/funding/positions").json() == []
    historical = client.get("/api/v1/trading/funding/positions?scope=history").json()[0]
    assert historical["status"] == "failed" and Decimal(historical["residualQuantity"]) == 0
    with connection() as db:
        assert (
            db.execute(
                "SELECT count(*) FROM execution_balance_reservations WHERE owner_id=? "
                "AND status='active'",
                (batch,),
            ).fetchone()[0]
            == 0
        )


def test_missing_spot_permission_blocks_before_any_perpetual_order(bybit_contract):
    client, _, directory = bybit_contract
    (directory / "controls.json").write_text('{"deny_spot_permission":true}')
    response = submit(client, key="permission-block")
    assert response.status_code == 409, response.text
    assert "现货交易权限" in response.text
    assert writes(directory) == []


def test_permission_removed_after_plan_creation_blocks_dispatch(bybit_contract):
    _, _, directory = bybit_contract
    from app.strategies.instruction_service import (
        CreateStrategyInstructionRequest,
        create_instruction,
    )

    instruction_id = create_instruction(
        INSTANCE_ID,
        CreateStrategyInstructionRequest(
            idempotencyKey="permission-changed",
            action="open",
            parameters={
                "perpetualSymbol": "BTCUSDT",
                "perpetualQuantity": "0.001",
                "spotSymbol": "BTCUSDT",
                "spotQuantity": "0.002",
                "executionPolicy": "market",
            },
            reason="Permission may change after preview",
        ),
        requested_by="owner",
    )["instructionId"]
    (directory / "controls.json").write_text('{"deny_spot_permission":true}')
    from fastapi import HTTPException

    with pytest.raises(HTTPException, match="现货交易权限"):
        execute_instruction(instruction_id)
    assert writes(directory) == []


def test_multiple_attempts_and_base_fee_inventory_flatten_without_duplicate_orders(bybit_contract):
    client, runtime, directory = bybit_contract
    controls = directory / "controls.json"
    controls.write_text('{"partial_first_quantity":"0.5"}')
    response = submit(client, key="partial-then-reject", quantity="1.002", policy="post_only_chase")
    assert response.status_code == 200, response.text
    instruction = response.json()["instruction"]["instructionId"]
    batch = response.json()["instruction"]["executionBatchId"]
    assert response.json()["workspaceState"]["cumulativePerpetualFill"] == "0.5"
    assert len(writes(directory)) == 2
    # The first partial fill is canceled authoritatively before the residual
    # attempt. Only the second Spot release is rejected by the SDK fixture.
    _age_attempt(batch, 1, seconds=2)
    controls.write_text('{"bid":"79000.1","ask":"79000.2","reject_spot_order":true}')
    time.sleep(5.1)  # Let the production five-second quote cache expire.
    for _ in range(5):
        execute_instruction(instruction)
        latest = client.get(ENDPOINT + "/" + instruction).json()
        if latest["instruction"]["status"] == "manual_intervention":
            break
    assert latest["instruction"]["status"] == "manual_intervention", latest
    assert Decimal(latest["workspaceState"]["cumulativePerpetualFill"]) == Decimal("1.000")
    assert len(latest["workspaceState"]["attempts"]) == 2
    assert len(writes(directory)) == 4
    assert len((directory / "sdk-cancels.jsonl").read_text().splitlines()) == 1
    controls.write_text("{}")
    route = f"/api/v1/trading/execution-batches/{batch}/risk-actions"
    payload = {
        "idempotencyKey": "flatten-multiple",
        "action": "flatten_filled_legs",
        "actor": "owner",
    }
    response = client.post(route, json=payload)
    assert response.status_code == 200 and response.json()["status"] == "completed", response.text
    sent = writes(directory)
    assert len(sent) == 6
    assert [(row["category"], row["qty"]) for row in sent[-2:]] == [
        ("linear", "1.000"),
        ("spot", "0.500499"),
    ]
    assert sent[-2]["reduceOnly"] is True
    assert len(response.json()["generatedOrderIds"]) == 2
    assert client.post(route, json=payload).json() == response.json()
    assert (
        client.post(route, json={**payload, "idempotencyKey": "already-flat"}).json()["status"]
        == "completed"
    )
    assert len(writes(directory)) == 6
    assert client.get("/api/v1/trading/funding/positions").json() == []
    with httpx.Client(trust_env=False) as native:
        assert (
            native.get(runtime + "/venue/positions", params={"accountId": "bybit-live-main"}).json()
            == []
        )
    with connection() as db:
        assert (
            db.execute(
                "SELECT count(*) FROM execution_balance_reservations WHERE owner_id=? "
                "AND status='active'",
                (batch,),
            ).fetchone()[0]
            == 0
        )
