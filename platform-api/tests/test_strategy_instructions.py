import os
import socket
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app import application
from app.config import get_settings
from app.database import connection, initialize_database
from app.schema_migrations import apply_platform_migrations
from app.strategies.instruction_service import (
    CreateStrategyInstructionRequest,
    create_instruction,
    execute_instruction,
    get_instruction,
)

FUNDING_INSTANCE = "strategy_funding_instruction_unit_test"
REPO_ROOT = Path(os.environ.get("VG_REPO_ROOT") or Path(__file__).resolve().parents[2])
RUNTIME_DIR = Path(os.environ.get("VG_RUNTIME_DIR") or REPO_ROOT / "execution-runtime")
RUNTIME_PYTHON = RUNTIME_DIR / ".venv" / "Scripts" / "python.exe"
if not RUNTIME_PYTHON.exists():
    RUNTIME_PYTHON = Path(sys.executable)


@pytest.fixture(autouse=True)
def generic_instruction_fixture(monkeypatch):
    """Exercise the service directly; controlled HTTP entrypoints have separate tests."""

    initialize = application.initialize_database

    def initialize_test_instance():
        initialize()
        original = "strategy_funding_arbitrage_instance_default"
        with connection() as db:
            row = dict(
                db.execute("SELECT * FROM strategy_instances WHERE id=?", (original,)).fetchone()
            )
            row.update(id=FUNDING_INSTANCE, status="active", trading_mode="simulation")
            columns = ",".join(row)
            placeholders = ",".join("?" for _ in row)
            db.execute(
                f"INSERT OR IGNORE INTO strategy_instances ({columns}) VALUES ({placeholders})",
                tuple(row.values()),
            )
            for binding in db.execute(
                "SELECT * FROM strategy_account_bindings WHERE strategy_instance_id=?", (original,)
            ).fetchall():
                values = dict(binding)
                values.update(id="unit:" + values["id"], strategy_instance_id=FUNDING_INSTANCE)
                db.execute(
                    f"INSERT OR IGNORE INTO strategy_account_bindings ({','.join(values)}) "
                    f"VALUES ({','.join('?' for _ in values)})",
                    tuple(values.values()),
                )

    monkeypatch.setattr(application, "initialize_database", initialize_test_instance)
    monkeypatch.setattr(sys.modules[__name__], "initialize_database", initialize_test_instance)


def _payload(*, key: str, quantity: str = "1") -> dict[str, object]:
    return {
        "idempotencyKey": key,
        "action": "open",
        "parameters": {
            "perpetualSymbol": "BTCUSDT",
            "perpetualQuantity": quantity,
            "spotSymbol": "BTCUSDT",
            "spotQuantity": quantity,
        },
        "reason": "CEO manual instruction",
    }


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def _runtime_server(tmp_path: Path):
    journal_dir = tmp_path / "runtime-journal"
    journal_dir.mkdir()
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
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise AssertionError(f"runtime did not become ready; log={log_file}")
        try:
            import httpx

            with httpx.Client(timeout=1.0) as client:
                if client.get(f"{base_url}/status").status_code == 200:
                    break
        except Exception:
            time.sleep(0.3)
    else:
        raise AssertionError(f"runtime did not become ready; log={log_file}")
    try:
        yield base_url, journal_dir
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _set_quote(journal_dir: Path, *, symbol: str, bid: str, ask: str, last: str = "100") -> None:
    with sqlite3.connect(journal_dir / "runtime_journal.db") as db:
        db.execute(
            """
            INSERT INTO fake_venue_quotes (symbol, bid, ask, last, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                bid = excluded.bid,
                ask = excluded.ask,
                last = excluded.last,
                updated_at = excluded.updated_at
            """,
            (symbol, bid, ask, last, datetime.now(UTC).isoformat()),
        )


def _create(payload):
    return create_instruction(
        FUNDING_INSTANCE, CreateStrategyInstructionRequest.model_validate(payload),
        requested_by="isolated-owner",
    )


def test_instruction_replay_returns_the_original_frozen_plan_and_one_batch() -> None:
    initialize_database()
    first = _create(_payload(key="instruction-001"))
    second = _create(_payload(key="instruction-001"))
    assert second == first
    assert first["status"] == "accepted"
    assert first["executionPlan"]["schemaVersion"] == "1"
    assert first["executionPlan"]["legs"][0]["executionPolicy"] == "post_only_chase"
    assert first["executionPlan"]["simulationCompatibilityPolicy"] is None
    assert first["executionBatchId"]
    assert first["requestedBy"] == "isolated-owner"
    assert get_instruction(first["instructionId"]) == first


def test_instruction_rejects_idempotency_key_reused_for_different_parameters() -> None:
    initialize_database()
    _create(_payload(key="instruction-002"))
    with pytest.raises(HTTPException) as error:
        _create(_payload(key="instruction-002", quantity="2"))
    assert error.value.status_code == 409


@pytest.mark.parametrize("change", [{"reason": "different reason"}, {"positionGroupId": "other"}])
def test_instruction_idempotency_includes_business_reason_and_position_group(change) -> None:
    initialize_database()
    payload = _payload(key="instruction-business-fingerprint")
    _create(payload)
    with pytest.raises(HTTPException) as error:
        _create({**payload, **change})
    assert error.value.status_code == 409


def test_instruction_idempotency_normalizes_decimal_parameters() -> None:
    initialize_database()
    payload = _payload(key="instruction-normalized-fingerprint")
    payload["parameters"]["perpetualQuantity"] = 1
    payload["parameters"]["spotQuantity"] = 1
    first = _create(payload)
    replay = _create(_payload(key="instruction-normalized-fingerprint"))
    assert replay["instructionId"] == first["instructionId"]


def test_close_instruction_fails_closed_without_position_group() -> None:
    initialize_database()
    with pytest.raises(HTTPException) as error:
        _create({**_payload(key="close-without-position-group"), "action": "close"})
    assert error.value.status_code == 423
    assert error.value.detail == "Position Group close planning is unavailable"


def test_instruction_rejects_unknown_parameters_and_unmapped_symbols() -> None:
    initialize_database()
    for key, changes, detail in (
        ("extra", {"accountId": "spoofed"}, "Invalid strategy instruction parameters"),
        ("eth", {"perpetualSymbol": "ETHUSDT"}, "Authoritative crypto_perp"),
    ):
        payload = _payload(key=key)
        payload["parameters"].update(changes)
        with pytest.raises(HTTPException) as error:
            _create(payload)
        assert error.value.status_code == 422
        assert detail in error.value.detail


def test_instruction_preserves_account_ids_in_capability_snapshot() -> None:
    initialize_database()
    response = _create(_payload(key="instruction-account-id"))
    assert response["executionPlan"]["accountCapabilitySnapshot"] == {
        "account_sim_usdt": "trade_and_read"
    }


def test_planning_does_not_reserve_database_writer(monkeypatch) -> None:
    from app.strategies import instruction_service

    initialize_database()
    original = instruction_service.build_plan

    def build_without_lock(*args):
        # Represents an unrelated account-sync writer while native specs are read.
        with sqlite3.connect(get_settings().database_path, timeout=0.1) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE accounts SET status=status WHERE id='account_sim_usdt'")
        return original(*args)

    monkeypatch.setattr(instruction_service, "build_plan", build_without_lock)
    result = _create(_payload(key="no-writer-during-planning"))
    assert result["status"] == "accepted"


def test_concurrent_planning_publishes_one_frozen_instruction(monkeypatch) -> None:
    from threading import Barrier

    from app.strategies import instruction_service

    initialize_database()
    original = instruction_service.build_plan
    barrier = Barrier(2)

    def concurrent_plan(*args):
        plan = original(*args)
        barrier.wait(timeout=5)
        return plan

    monkeypatch.setattr(instruction_service, "build_plan", concurrent_plan)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_create, _payload(key="concurrent-plan")) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert results[0] == results[1]
    with connection() as db:
        assert db.execute("SELECT count(*) FROM strategy_runs").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM execution_batches").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM execution_batch_legs").fetchone()[0] == 2


def test_pending_instruction_batch_is_claimed_once_and_replay_does_not_duplicate_commands(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "instruction-dispatch-claim.db")
    settings.live_trading_enabled = True
    settings.default_trading_environment = "simulation"
    first_submit_started = Event()
    release_first_submit = Event()

    class FilledResponse:
        def __init__(self, command: dict[str, object]) -> None:
            self.command = command

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            command = self.command
            return [
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_filled",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-08-22T00:00:00+00:00",
                    "reason": None,
                }
            ]

    call_count = 0

    def fake_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            first_submit_started.set()
            assert release_first_submit.wait(timeout=5)
        return FilledResponse(kwargs["json"])

    monkeypatch.setattr("app.runtime_transport.post", fake_post)

    with _runtime_server(tmp_path) as (runtime_url, journal_dir):
        settings.runtime_base_url = runtime_url
        initialize_database()
        apply_platform_migrations()
        with connection() as db:
            db.execute("UPDATE accounts SET status = 'active' WHERE id = ?", ("account_sim_usdt",))
            db.execute(
                "UPDATE strategy_instances SET status = 'active' WHERE id = ?",
                (FUNDING_INSTANCE,),
            )
        _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")

        created = _create(_payload(key="instruction-dispatch-claim"))
        instruction_id = created["instructionId"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(execute_instruction, instruction_id)
            assert first_submit_started.wait(timeout=5)
            replay = pool.submit(execute_instruction, instruction_id)
            try:
                replay_result = replay.result(timeout=5)
            finally:
                release_first_submit.set()
            result = first.result(timeout=10)

        assert replay_result.status == "executing"
        assert result.status == "hedged"
        assert call_count == 2
        with connection() as db:
            command_count = db.execute("SELECT COUNT(*) AS count FROM trade_commands").fetchone()
            attempt_count = db.execute(
                "SELECT COUNT(*) AS count FROM funding_perpetual_attempts"
            ).fetchone()
            instruction = db.execute(
                "SELECT status FROM strategy_runs WHERE id = ?", (instruction_id,)
            ).fetchone()
        assert command_count["count"] == 2
        assert attempt_count["count"] == 1
        assert instruction["status"] == "reconciling"
