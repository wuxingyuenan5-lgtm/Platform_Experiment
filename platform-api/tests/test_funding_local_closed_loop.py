"""Funding-carry (perpetual-short + spot-long) local closed-loop acceptance.

Drives the real Platform API funding market command against a real
execution-runtime subprocess with the deterministic FakeGateway on one Bybit
account: opens the CEO-specified pair (perpetual leg first, spot hedge only
after the confirmed perpetual fill), verifies both legs fill and both
positions appear, closes through the market command, and verifies both
positions return to zero with exact platform<->venue reconciliation. A
runtime-unavailable scenario must fail closed.
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

REPO_ROOT = Path(os.environ.get("VG_REPO_ROOT") or Path(__file__).resolve().parents[2])
RUNTIME_DIR = Path(os.environ.get("VG_RUNTIME_DIR") or REPO_ROOT / "execution-runtime")
RUNTIME_PYTHON = RUNTIME_DIR / ".venv" / "Scripts" / "python.exe"
if not RUNTIME_PYTHON.exists():
    RUNTIME_PYTHON = Path(sys.executable)

FUNDING_ENDPOINT = "/api/v1/trading/funding/market-command"
FUNDING_ACCOUNT_ID = "account_sim_usdt"
PERPETUAL_SYMBOL = "BTCUSDT"
SPOT_SYMBOL = "BTC"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_runtime(journal_dir: Path) -> tuple[subprocess.Popen, str, Path]:
    port = _free_port()
    env = dict(os.environ)
    env["VG_RUNTIME_GATEWAY_NAME"] = "fake"
    env["VG_RUNTIME_JOURNAL_PATH"] = str(journal_dir / "runtime_journal.db")
    env["VG_RUNTIME_LIVE_WRITE_ENABLED"] = "false"
    log_file = journal_dir / "runtime.log"
    log_out = log_file.open("ab")
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
    return proc, f"http://127.0.0.1:{port}", log_file


def _wait_runtime_ready(proc: subprocess.Popen, base_url: str, log_file: Path) -> bool:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with httpx.Client(timeout=1.0) as client:
                if client.get(f"{base_url}/status").status_code == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def runtime(tmp_path_factory: pytest.TempPathFactory) -> str:
    journal_dir = tmp_path_factory.mktemp("runtime-journal")
    proc, base_url, log_file = _start_runtime(journal_dir)
    if not _wait_runtime_ready(proc, base_url, log_file):
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        proc, base_url, log_file = _start_runtime(journal_dir)
        assert _wait_runtime_ready(proc, base_url, log_file), (
            f"runtime did not become ready; log={log_file}"
        )
    yield base_url, journal_dir
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _seed_funding_environment(tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "funding-closed-loop.db")
    initialize_database()
    with connection() as db:
        db.execute(
            "UPDATE accounts SET status = 'active' WHERE id = 'account_sim_usdt'"
        )
        db.execute(
            "UPDATE strategy_instances SET status = 'active' "
            "WHERE id = 'strategy_funding_arbitrage_instance_default'"
        )
        for instrument_id, symbol, instrument_type, code in (
            ("instrument_btcusdt", "BTCUSDT", "crypto_perp", "BTCUSDT.PERP"),
            ("instrument_btc", "BTC", "crypto_spot", "BTC.SPOT"),
        ):
            db.execute(
                """
                INSERT OR IGNORE INTO instruments (
                    id, instrument_code, name, instrument_type, base_currency,
                    quote_currency, settle_currency, quantity_unit,
                    data_quality_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'complete', ?)
                """,
                (
                    instrument_id,
                    code,
                    symbol,
                    instrument_type,
                    "BTC",
                    "USDT",
                    "USDT",
                    "BTC",
                    "2026-08-18T00:00:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT OR IGNORE INTO contract_specifications (
                    id, instrument_id, version, price_tick, min_order_quantity,
                    quantity_step, contract_multiplier, effective_from,
                    data_quality_state
                ) VALUES (?, ?, 1, ?, ?, ?, 1, ?, 'complete')
                """,
                (
                    f"contract_{instrument_id}",
                    instrument_id,
                    "0.01",
                    "0.000001",
                    "0.000001",
                    "2026-08-18T00:00:00+00:00",
                ),
            )


def _venue_positions(runtime_url: str, account_id: str) -> list[dict]:
    with httpx.Client(base_url=runtime_url, timeout=10) as client:
        response = client.get("/venue/positions")
        response.raise_for_status()
        return [p for p in response.json() if p.get("accountId") == account_id]


def test_funding_local_closed_loop_open_close_and_reconcile(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, _journal_dir = runtime
    _seed_funding_environment(tmp_path)
    settings = get_settings()
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True

    with TestClient(app) as client:
        opened = client.post(
            FUNDING_ENDPOINT,
            json={
                "action": "OPEN_SHORT_PERP_LONG_SPOT",
                "perpetualSymbol": PERPETUAL_SYMBOL,
                "spotSymbol": SPOT_SYMBOL,
                "quantity": "1",
            },
        )
        assert opened.status_code == 200, opened.text
        open_batch = opened.json()
        assert open_batch["status"] == "hedged", open_batch
        legs = {leg["role"]: leg for leg in open_batch["legs"]}
        assert legs["perpetual_leg"]["status"] == "filled"
        assert legs["spot_leg"]["status"] == "filled"

        positions = _venue_positions(runtime_url, FUNDING_ACCOUNT_ID)
        perp = [p for p in positions if p.get("instrumentId") == "instrument_btcusdt"]
        spot = [p for p in positions if p.get("instrumentId") == "instrument_btc"]
        assert perp, "perpetual short position missing"
        assert spot, "spot long position missing"

        # Exact platform <-> venue reconciliation of both open legs.
        with httpx.Client(base_url=runtime_url, timeout=10) as rt:
            venue_orders = rt.get("/venue/orders").json()
        leg_order_ids = {leg["role"]: leg["orderId"] for leg in open_batch["legs"]}
        expected_fill = {
            "perpetual_leg": Decimal("1"),
            "spot_leg": Decimal("1"),
        }
        for role, order_id in leg_order_ids.items():
            matches = [o for o in venue_orders if o.get("platformOrderId") == order_id]
            assert len(matches) == 1, f"{role} venue order missing: {order_id}"
            assert matches[0]["status"] == "filled", matches[0]
            assert Decimal(matches[0]["filledQuantity"]) == expected_fill[role]

        # CLOSE the pair through the market command.
        closed = client.post(
            FUNDING_ENDPOINT,
            json={
                "action": "CLOSE_SHORT_PERP_LONG_SPOT",
                "perpetualSymbol": PERPETUAL_SYMBOL,
                "spotSymbol": SPOT_SYMBOL,
                "quantity": "1",
            },
        )
        assert closed.status_code == 200, closed.text
        close_batch = closed.json()
        assert close_batch["status"] == "hedged", close_batch

        positions_after = _venue_positions(runtime_url, FUNDING_ACCOUNT_ID)
        perp_after = [p for p in positions_after if p.get("instrumentId") == "instrument_btcusdt"]
        spot_after = [p for p in positions_after if p.get("instrumentId") == "instrument_btc"]
        assert perp_after and all(
            Decimal(p["netQuantity"]) == 0 for p in perp_after
        ), perp_after
        assert spot_after and all(
            Decimal(p["netQuantity"]) == 0 for p in spot_after
        ), spot_after


def test_funding_local_closed_loop_fails_closed_when_runtime_unavailable(
    tmp_path: Path,
) -> None:
    _seed_funding_environment(tmp_path)
    settings = get_settings()
    settings.runtime_base_url = "http://127.0.0.1:1"
    settings.live_trading_enabled = True

    with TestClient(app) as client:
        opened = client.post(
            FUNDING_ENDPOINT,
            json={
                "action": "OPEN_SHORT_PERP_LONG_SPOT",
                "perpetualSymbol": PERPETUAL_SYMBOL,
                "spotSymbol": SPOT_SYMBOL,
                "quantity": "1",
            },
        )
        # Fail closed: an unreachable runtime must not hedge or silently retry.
        # The perpetual leg becomes result_unknown and the batch requires manual
        # intervention; the spot hedge is never released.
        assert opened.status_code == 200, opened.text
        batch = opened.json()
        assert batch["status"] == "manual_intervention", batch
        legs = {leg["role"]: leg for leg in batch["legs"]}
        assert legs["perpetual_leg"]["status"] == "result_unknown", legs
        assert legs["spot_leg"]["status"] == "pending", legs


def test_funding_local_closed_loop_simulated_funding_settlement(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_funding_environment(tmp_path)
    settings = get_settings()
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True

    with TestClient(app) as client:
        opened = client.post(
            FUNDING_ENDPOINT,
            json={
                "action": "OPEN_SHORT_PERP_LONG_SPOT",
                "perpetualSymbol": PERPETUAL_SYMBOL,
                "spotSymbol": SPOT_SYMBOL,
                "quantity": "1",
            },
        )
        assert opened.status_code == 200, opened.text
        assert opened.json()["status"] == "hedged", opened.json()

    # Simulated funding settlement on the perpetual leg, recorded directly in
    # the deterministic fake venue, then imported through the platform's live
    # economic-event machinery into the financial-fact ledger.
    import sqlite3

    with sqlite3.connect(journal_dir / "runtime_journal.db") as db:
        db.execute(
            """
            INSERT OR REPLACE INTO fake_venue_economic_events (
                external_event_id, event_type, account_id, instrument_id, symbol,
                amount, currency, occurred_at, data_quality_state, payload_json
            ) VALUES (?, 'funding', ?, ?, ?, ?, 'USDT', ?, 'complete', ?)
            """,
            (
                "FUND-SETTLE-001",
                FUNDING_ACCOUNT_ID,
                "instrument_btcusdt",
                PERPETUAL_SYMBOL,
                "0.001",
                "2026-08-18T12:00:00+00:00",
                '{"simulated": true}',
            ),
        )

    from app.live_venue_accounting import (
        LiveEconomicEventImportRequest,
        import_live_economic_events,
    )

    result = import_live_economic_events(
        LiveEconomicEventImportRequest(
            idempotencyKey="funding-import-001",
            strategyInstanceId="strategy_funding_arbitrage_instance_default",
            accountId=FUNDING_ACCOUNT_ID,
            eventType="funding",
            actor="eod-runner",
        )
    )
    assert result.status == "completed", result
    assert len(result.imported_fact_ids) == 1, result

    with connection() as db:
        row = db.execute(
            """
            SELECT fact_type, amount, external_id
            FROM financial_facts
            WHERE external_id = 'FUND-SETTLE-001'
            """
        ).fetchone()
    assert row is not None, "funding fact not imported into the ledger"
    assert row["fact_type"] == "funding"
    assert Decimal(row["amount"]) == Decimal("0.001")
