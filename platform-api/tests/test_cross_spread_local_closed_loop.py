"""Cross-venue gold spread: local closed-loop acceptance.

Drives the real Platform API flow (cross-spread lifecycle open/close ->
execution batch -> runtime command submission) against a real execution-runtime
subprocess configured with the deterministic FakeGateway. It opens the gold
spread, verifies both venue legs fill and both venue positions appear, closes
through the claimed exit plan, and verifies both venue positions return to
zero. Order/fill/position facts are read back from the runtime as venue
evidence.

Safety: no external venue, no credentials, no Live Write. The runtime runs
with the FakeGateway and live_write_enabled=False.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection, initialize_database
from app.main import app

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "execution-runtime"
RUNTIME_PYTHON = RUNTIME_DIR / ".venv" / "Scripts" / "python.exe"
if not RUNTIME_PYTHON.exists():
    RUNTIME_PYTHON = Path(sys.executable)
LIFECYCLE_OPEN_ENDPOINT = "/api/v1/trading/cross-spread/lifecycle/open"
BYBIT_ACCOUNT_ID = "account_crypto_test"
MT5_ACCOUNT_ID = "account_mt5_demo"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def runtime_process(tmp_path):
    port = _free_port()
    journal_dir = tmp_path / "runtime-journal"
    journal_dir.mkdir()
    env = dict(os.environ)
    env["VG_RUNTIME_GATEWAY_NAME"] = "fake"
    env["VG_RUNTIME_JOURNAL_PATH"] = str(journal_dir / "runtime_journal.db")
    env["VG_RUNTIME_LIVE_WRITE_ENABLED"] = "false"
    log_file = journal_dir / "runtime.log"
    base_url = f"http://127.0.0.1:{port}"
    process = None

    def stop():
        nonlocal process
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            process = None

    def start():
        nonlocal process
        with log_file.open("ab") as log_out:
            process = subprocess.Popen(
                [
                    str(RUNTIME_PYTHON),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--log-level",
                    "warning",
                ],
                cwd=str(RUNTIME_DIR),
                env=env,
                stdout=log_out,
                stderr=subprocess.STDOUT,
            )
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    f"runtime exited early rc={process.returncode}; log={log_file}"
                )
            try:
                with httpx.Client(timeout=1.0, trust_env=False) as client:
                    response = client.get(f"{base_url}/status")
                    if response.status_code == 200:
                        assert response.json()["capabilities"]["liveWriteEnabled"] is False
                        return process.pid
            except httpx.HTTPError:
                time.sleep(0.3)
        raise RuntimeError(f"runtime did not become ready; log={log_file}")

    try:
        initial_pid = start()
        yield SimpleNamespace(url=base_url, stop=stop, start=start, initial_pid=initial_pid)
    finally:
        stop()


@pytest.fixture
def runtime_url(runtime_process):
    return runtime_process.url


def _venue_positions(runtime_url: str, account_id: str) -> list[dict]:
    with httpx.Client(base_url=runtime_url, timeout=10) as client:
        response = client.get("/venue/positions")
        response.raise_for_status()
        return [p for p in response.json() if p.get("accountId") == account_id]


def _seed_cross_spread_environment(tmp_path: Path, database_name: str) -> None:
    settings = get_settings()
    settings.environment = "development"
    settings.auth_mode = "development"
    settings.development_roles = "admin"
    settings.cross_spread_exit_monitor_enabled = False
    settings.research_refresh_enabled = False
    settings.database_path = str(tmp_path / database_name)
    initialize_database()
    with connection() as db:
        db.execute(
            "UPDATE accounts SET status = 'active' WHERE id IN (?, ?)",
            (BYBIT_ACCOUNT_ID, MT5_ACCOUNT_ID),
        )
        db.execute(
            """
            UPDATE strategy_instances
            SET status = 'active', trading_mode = 'simulation'
            WHERE id = 'strategy_cross_venue_spread_instance_default'
            """
        )
        db.execute(
            """
            UPDATE strategy_account_bindings
            SET account_id = CASE role
                    WHEN 'venue_a' THEN 'account_crypto_test'
                    WHEN 'mt5_leg' THEN 'account_mt5_demo'
                    ELSE account_id
                END,
                status = 'active'
            WHERE strategy_instance_id = 'strategy_cross_venue_spread_instance_default'
              AND role IN ('venue_a', 'mt5_leg')
            """
        )
        db.execute(
            """
            INSERT OR REPLACE INTO balance_snapshots (
                id, account_id, currency, equity, available_balance, source,
                data_quality_state, as_of, created_at
            ) VALUES
                (
                    'cross-balance-bybit-usdt', 'account_crypto_test', 'USDT',
                    '100000', '100000', 'test_seed', 'complete',
                    '2026-08-23T00:00:00+00:00', '2026-08-23T00:00:00+00:00'
                ),
                (
                    'cross-balance-mt5-usd', 'account_mt5_demo', 'USD',
                    '100000', '100000', 'test_seed', 'complete',
                    '2026-08-23T00:00:00+00:00', '2026-08-23T00:00:00+00:00'
                )
            """
        )


def test_cross_spread_gold_local_closed_loop(
    runtime_url: str, tmp_path: Path, authorize_funding_ceo
) -> None:
    _seed_cross_spread_environment(tmp_path, "platform-closed-loop.db")
    settings = get_settings()
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")

    with TestClient(app) as client:
        _seed_cross_spread_environment(tmp_path, "platform-closed-loop.db")
        authorize_funding_ceo(client)
        # --- OPEN_LONG: buy Bybit XAUTUSDT, sell MT5 XAUUSD.s ---
        opened = client.post(
            LIFECYCLE_OPEN_ENDPOINT,
            json={
                "direction": "LONG_SPREAD",
                "quantityOz": "1",
                "takeProfitSpread": "0",
                "stopLossSpread": "-3",
                "executionMode": "market",
                "idempotencyKey": "cross-local-open-1",
            },
        )
        assert opened.status_code == 200, opened.text
        open_data = opened.json()
        batch = open_data["executionBatch"]
        assert batch["status"] == "hedged", (batch["failureReason"], batch["legs"])
        legs = {leg["role"]: leg for leg in batch["legs"]}
        assert legs["bybit_leg"]["status"] == "filled"
        assert legs["mt5_leg"]["status"] == "filled"
        plan = open_data["exitPlan"]
        assert plan is not None, "hedged open must create an exit plan"

        # Venue evidence: both venues have orders, fills and open positions.
        with httpx.Client(base_url=runtime_url, timeout=10) as rt:
            orders = rt.get("/venue/orders").json()
            fills = rt.get("/venue/fills").json()
        assert len(orders) >= 2, orders
        assert len(fills) >= 2, fills
        bybit_positions = _venue_positions(runtime_url, BYBIT_ACCOUNT_ID)
        mt5_positions = _venue_positions(runtime_url, MT5_ACCOUNT_ID)
        assert bybit_positions, "Bybit long position missing after hedged open"
        assert mt5_positions, "MT5 short position missing after hedged open"

        # --- CLOSE_LONG through the claimed exit plan ---
        closed = client.post(
            f"/api/v1/trading/cross-spread/exit-plans/{plan['planId']}/close",
            json={},
        )
        assert closed.status_code == 200, closed.text
        close_batch = closed.json()["executionBatch"]
        assert close_batch["status"] in {"hedged", "completed"}, close_batch

        # Both venue positions must return to zero after the close.
        bybit_after = _venue_positions(runtime_url, BYBIT_ACCOUNT_ID)
        mt5_after = _venue_positions(runtime_url, MT5_ACCOUNT_ID)
        assert bybit_after and all(
            Decimal(position["netQuantity"]) == 0 for position in bybit_after
        ), bybit_after
        assert mt5_after and all(
            Decimal(position["netQuantity"]) == 0 for position in mt5_after
        ), mt5_after


def test_cross_spread_local_closed_loop_allows_independent_completed_groups(
    runtime_url: str,
    tmp_path: Path,
    authorize_funding_ceo,
) -> None:
    _seed_cross_spread_environment(tmp_path, "platform-closed-loop-idem.db")
    settings = get_settings()
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")
    settings.cross_spread_acceptance_max_active_plans = 1

    with TestClient(app) as client:
        _seed_cross_spread_environment(tmp_path, "platform-closed-loop-idem.db")
        authorize_funding_ceo(client)
        first = client.post(
            LIFECYCLE_OPEN_ENDPOINT,
            json={
                "direction": "LONG_SPREAD",
                "quantityOz": "1",
                "takeProfitSpread": "0",
                "stopLossSpread": "-3",
                "executionMode": "market",
                "idempotencyKey": "cross-local-open-active-1",
            },
        )
        assert first.status_code == 200, first.text
        first_batch_id = first.json()["executionBatch"]["batchId"]

        second = client.post(
            LIFECYCLE_OPEN_ENDPOINT,
            json={
                "direction": "LONG_SPREAD",
                "quantityOz": "1",
                "takeProfitSpread": "0",
                "stopLossSpread": "-3",
                "executionMode": "market",
                "idempotencyKey": "cross-local-open-active-2",
            },
        )
        assert second.status_code == 200, second.text
        assert second.json()["executionBatch"]["batchId"] != first_batch_id
        assert second.json()["exitPlan"]["planId"] != first.json()["exitPlan"]["planId"]
        for opened in (first, second):
            cleanup = client.post(
                f"/api/v1/trading/cross-spread/exit-plans/{opened.json()['exitPlan']['planId']}/close",
                json={},
            )
            assert cleanup.status_code == 200, cleanup.text
        assert all(
            Decimal(position["netQuantity"]) == 0
            for position in _venue_positions(runtime_url, BYBIT_ACCOUNT_ID)
        )
        assert all(
            Decimal(position["netQuantity"]) == 0
            for position in _venue_positions(runtime_url, MT5_ACCOUNT_ID)
        )


def test_cross_spread_local_closed_loop_tracks_alternating_position_groups(
    runtime_url: str,
    tmp_path: Path,
    authorize_funding_ceo,
) -> None:
    _seed_cross_spread_environment(tmp_path, "platform-closed-loop-multiple.db")
    settings = get_settings()
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")
    settings.cross_spread_acceptance_max_active_plans = 0

    payload = {
        "quantityOz": "1",
        "executionMode": "market",
    }
    with TestClient(app) as client:
        _seed_cross_spread_environment(tmp_path, "platform-closed-loop-multiple.db")
        authorize_funding_ceo(client)
        first = client.post(
            LIFECYCLE_OPEN_ENDPOINT,
            json={
                **payload,
                "direction": "LONG_SPREAD",
                "idempotencyKey": "cross-local-multiple-open-1",
            },
        )
        assert first.status_code == 200, first.text
        second = client.post(
            LIFECYCLE_OPEN_ENDPOINT,
            json={
                **payload,
                "direction": "SHORT_SPREAD",
                "idempotencyKey": "cross-local-multiple-open-2",
            },
        )
        assert second.status_code == 200, second.text
        third = client.post(
            LIFECYCLE_OPEN_ENDPOINT,
            json={
                **payload,
                "direction": "LONG_SPREAD",
                "idempotencyKey": "cross-local-multiple-open-3",
            },
        )
        assert third.status_code == 200, third.text
        first_plan = first.json()["exitPlan"]
        second_plan = second.json()["exitPlan"]
        third_plan = third.json()["exitPlan"]
        assert first_plan is not None and second_plan is not None and third_plan is not None

        bybit_open = _venue_positions(runtime_url, BYBIT_ACCOUNT_ID)
        mt5_open = _venue_positions(runtime_url, MT5_ACCOUNT_ID)
        assert [Decimal(position["netQuantity"]) for position in bybit_open] == [Decimal("1")]
        assert [Decimal(position["netQuantity"]) for position in mt5_open] == [Decimal("-0.01")]

        first_close = client.post(
            f"/api/v1/trading/cross-spread/exit-plans/{second_plan['planId']}/close",
            json={},
        )
        assert first_close.status_code == 200, first_close.text
        assert first_close.json()["exitPlan"]["status"] == "closed"
        bybit_after_first_close = _venue_positions(runtime_url, BYBIT_ACCOUNT_ID)
        mt5_after_first_close = _venue_positions(runtime_url, MT5_ACCOUNT_ID)
        assert [Decimal(position["netQuantity"]) for position in bybit_after_first_close] == [
            Decimal("2")
        ]
        assert [Decimal(position["netQuantity"]) for position in mt5_after_first_close] == [
            Decimal("-0.02")
        ]

        second_close = client.post(
            f"/api/v1/trading/cross-spread/exit-plans/{first_plan['planId']}/close",
            json={},
        )
        assert second_close.status_code == 200, second_close.text
        assert second_close.json()["exitPlan"]["status"] == "closed"
        assert [
            Decimal(position["netQuantity"])
            for position in _venue_positions(runtime_url, BYBIT_ACCOUNT_ID)
        ] == [Decimal("1")]
        third_close = client.post(
            f"/api/v1/trading/cross-spread/exit-plans/{third_plan['planId']}/close",
            json={},
        )
        assert third_close.status_code == 200, third_close.text
        assert third_close.json()["exitPlan"]["status"] == "closed"
        assert all(
            Decimal(position["netQuantity"]) == 0
            for position in _venue_positions(runtime_url, BYBIT_ACCOUNT_ID)
        )
        assert all(
            Decimal(position["netQuantity"]) == 0
            for position in _venue_positions(runtime_url, MT5_ACCOUNT_ID)
        )


@pytest.mark.parametrize("interruption", ["before_mt5_submit", "after_mt5_fill"])
def test_runtime_and_api_restart_after_first_leg_never_repeat_orders(
    runtime_process, tmp_path, monkeypatch, authorize_funding_ceo, interruption
):
    from app import runtime_transport

    _seed_cross_spread_environment(tmp_path, "platform-interrupted.db")
    settings = get_settings()
    settings.runtime_base_url = runtime_process.url
    settings.live_trading_enabled = True
    original_post = runtime_transport.post
    submissions = []

    def interrupted_post(url, **kwargs):
        assert url.startswith(runtime_process.url + "/")
        if url.endswith("/commands/orders"):
            command = kwargs["json"]
            submissions.append(command)
            if command["account_id"] == MT5_ACCOUNT_ID:
                if interruption == "after_mt5_fill":
                    response = original_post(url, **kwargs)
                    assert response.status_code == 200, response.text
                runtime_process.stop()
                raise httpx.ReadTimeout("isolated Runtime stopped before response was delivered")
        return original_post(url, **kwargs)

    monkeypatch.setattr(runtime_transport, "post", interrupted_post)
    payload = {
        "direction": "LONG_SPREAD", "quantityOz": "1", "executionMode": "market",
        "idempotencyKey": "interrupted-cross-open",
    }
    with TestClient(app) as client:
        _seed_cross_spread_environment(tmp_path, "platform-interrupted.db")
        authorize_funding_ceo(client)
        opened = client.post(LIFECYCLE_OPEN_ENDPOINT, json=payload)
        assert opened.status_code == 200, opened.text
        batch = opened.json()["executionBatch"]
        legs = {leg["role"]: leg for leg in batch["legs"]}
        assert legs["bybit_leg"]["status"] == "filled"
        assert legs["mt5_leg"]["status"] == "result_unknown"
        unknown_order = legs["mt5_leg"]["orderId"]
        unavailable = client.post(f"/api/v1/trading/orders/{unknown_order}/reconcile")
        assert unavailable.status_code == 200, unavailable.text
        assert unavailable.json()["status"] == "result_unknown"
        cookies, headers = dict(client.cookies), dict(client.headers)
    restarted_pid = runtime_process.start()
    assert restarted_pid != runtime_process.initial_pid

    with TestClient(app) as restarted:
        _seed_cross_spread_environment(tmp_path, "platform-interrupted.db")
        restarted.cookies.update(cookies)
        restarted.headers.update(headers)
        repeated = restarted.post(LIFECYCLE_OPEN_ENDPOINT, json=payload)
        assert repeated.status_code == 409, repeated.text
        original = restarted.get(f"/api/v1/trading/execution-batches/{batch['batchId']}")
        assert original.status_code == 200, original.text
        assert original.json()["batchId"] == batch["batchId"]
        refused = restarted.post(
            LIFECYCLE_OPEN_ENDPOINT, json={**payload, "idempotencyKey": "unsafe-new-intent"}
        )
        assert refused.status_code == 409, refused.text
        for _ in range(2):
            recovered = restarted.post(f"/api/v1/trading/orders/{unknown_order}/reconcile")
            assert recovered.status_code == 200, recovered.text
            assert recovered.json()["status"] == (
                "filled" if interruption == "after_mt5_fill" else "result_unknown"
            )
        native = restarted.post(f"/api/v1/trading/orders/{unknown_order}/venue-reconcile")
        assert native.status_code == 200, native.text
        recovered_batch = restarted.get(
            f"/api/v1/trading/execution-batches/{batch['batchId']}"
        ).json()
        if interruption == "after_mt5_fill":
            assert native.json()["differenceIds"] == []
            assert recovered_batch["status"] == "hedged"
            repeated_native = restarted.post(
                f"/api/v1/trading/orders/{unknown_order}/venue-reconcile"
            )
            assert repeated_native.status_code == 200, repeated_native.text
            assert repeated_native.json()["differenceIds"] == []
        else:
            assert native.json()["differenceIds"]
            assert recovered_batch["status"] == "manual_intervention"
    assert len(submissions) == 2
    assert [row["account_id"] for row in submissions] == [BYBIT_ACCOUNT_ID, MT5_ACCOUNT_ID]
    with httpx.Client(base_url=runtime_process.url, trust_env=False) as runtime:
        orders = runtime.get("/venue/orders").json()
        fills = runtime.get("/venue/fills").json()
        status = runtime.get("/status").json()
    assert status["capabilities"]["liveWriteEnabled"] is False
    assert len(orders) == len(fills) == (2 if interruption == "after_mt5_fill" else 1)
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM execution_batches").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == (
            2 if interruption == "after_mt5_fill" else 1
        )
