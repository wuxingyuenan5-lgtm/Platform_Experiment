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


@pytest.fixture(scope="module")
def runtime_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    port = _free_port()
    journal_dir = tmp_path_factory.mktemp("runtime-journal")
    env = dict(os.environ)
    env["VG_RUNTIME_GATEWAY_NAME"] = "fake"
    env["VG_RUNTIME_JOURNAL_PATH"] = str(journal_dir / "runtime_journal.db")
    env["VG_RUNTIME_LIVE_WRITE_ENABLED"] = "false"
    log_file = journal_dir / "runtime.log"
    with log_file.open("ab") as log_out:
        proc = subprocess.Popen(
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
        base_url = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"runtime exited early rc={proc.returncode}; log={log_file}"
                )
            try:
                with httpx.Client(timeout=1.0) as client:
                    if client.get(f"{base_url}/status").status_code == 200:
                        break
            except Exception:
                time.sleep(0.3)
        else:
            proc.terminate()
            raise RuntimeError("runtime did not become ready; log={log_file}")
        yield base_url
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _venue_positions(runtime_url: str, account_id: str) -> list[dict]:
    with httpx.Client(base_url=runtime_url, timeout=10) as client:
        response = client.get("/venue/positions")
        response.raise_for_status()
        return [p for p in response.json() if p.get("accountId") == account_id]


def _seed_cross_spread_environment(tmp_path: Path, database_name: str) -> None:
    settings = get_settings()
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
            SET status = 'active'
            WHERE id = 'strategy_cross_venue_spread_instance_default'
            """
        )
        db.execute(
            """
            INSERT INTO balance_snapshots (
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


def test_cross_spread_gold_local_closed_loop(runtime_url: str, tmp_path: Path) -> None:
    _seed_cross_spread_environment(tmp_path, "platform-closed-loop.db")
    settings = get_settings()
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")

    with TestClient(app) as client:
        # --- OPEN_LONG: buy Bybit XAUTUSDT, sell MT5 XAUUSD.s ---
        opened = client.post(
            LIFECYCLE_OPEN_ENDPOINT,
            json={
                "direction": "LONG_SPREAD",
                "quantityOz": "1",
                "takeProfitSpread": "0",
                "stopLossSpread": "-3",
                "executionMode": "market",
            },
        )
        assert opened.status_code == 200, opened.text
        open_data = opened.json()
        batch = open_data["executionBatch"]
        assert batch["status"] == "hedged", batch
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


def test_cross_spread_local_closed_loop_blocks_second_open_while_plan_is_active(
    runtime_url: str,
    tmp_path: Path,
) -> None:
    _seed_cross_spread_environment(tmp_path, "platform-closed-loop-idem.db")
    settings = get_settings()
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")

    with TestClient(app) as client:
        first = client.post(
            LIFECYCLE_OPEN_ENDPOINT,
            json={
                "direction": "LONG_SPREAD",
                "quantityOz": "1",
                "takeProfitSpread": "0",
                "stopLossSpread": "-3",
                "executionMode": "market",
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
            },
        )
        assert second.status_code == 409, second.text
        assert second.json()["detail"] in {
            "A non-closed cross-spread lifecycle already exists",
            "A live Bybit gold position already exists",
        }
        assert first_batch_id
