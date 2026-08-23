from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection, initialize_database
from app.main import app
from app.schema_migrations import apply_platform_migrations
from app.strategies.funding_orchestration import _attempt_status_from_order_status
from app.strategies.instruction_service import (
    CreateStrategyInstructionRequest,
    create_instruction,
    execute_instruction,
)

pytestmark = pytest.mark.integration

REPO_ROOT = Path(os.environ.get("VG_REPO_ROOT") or Path(__file__).resolve().parents[2])
RUNTIME_DIR = Path(os.environ.get("VG_RUNTIME_DIR") or REPO_ROOT / "execution-runtime")
RUNTIME_PYTHON = RUNTIME_DIR / ".venv" / "Scripts" / "python.exe"
if not RUNTIME_PYTHON.exists():
    RUNTIME_PYTHON = Path(sys.executable)

FUNDING_ENDPOINT = "/api/v1/trading/funding/market-command"
INSTANCE_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"


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


def _wait_runtime_ready(proc: subprocess.Popen, base_url: str) -> bool:
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


@pytest.fixture
def runtime(tmp_path: Path):
    journal_dir = tmp_path / "runtime-journal"
    journal_dir.mkdir()
    proc, base_url, log_file = _start_runtime(journal_dir)
    assert _wait_runtime_ready(proc, base_url), f"runtime did not become ready; log={log_file}"
    yield base_url, journal_dir
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _seed_environment(tmp_path: Path, runtime_url: str) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "funding-phase2-orchestration.db")
    settings.default_trading_environment = "simulation"
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True
    settings.environment = "development"
    settings.auth_mode = "development"
    initialize_database()
    apply_platform_migrations()
    with connection() as db:
        db.execute("UPDATE accounts SET status = 'active' WHERE id = ?", (ACCOUNT_ID,))
        db.execute(
            "UPDATE strategy_instances SET status = 'active' WHERE id = ?",
            (INSTANCE_ID,),
        )


def _seed_script(
    journal_dir: Path,
    *,
    symbol: str,
    behavior: str,
    partial_fill_quantity: str | None = None,
    partial_fill_price: str | None = None,
    cancel_terminal_after_queries: int = 0,
) -> None:
    import sqlite3

    with sqlite3.connect(journal_dir / "runtime_journal.db") as db:
        db.execute(
            """
            INSERT INTO fake_venue_order_scripts (
                symbol, behavior, partial_fill_quantity, partial_fill_price,
                cancel_terminal_after_queries, created_at, consumed_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                symbol,
                behavior,
                partial_fill_quantity,
                partial_fill_price,
                cancel_terminal_after_queries,
                datetime.now(UTC).isoformat(),
            ),
        )


def _set_quote(journal_dir: Path, *, symbol: str, bid: str, ask: str, last: str = "100") -> None:
    import sqlite3

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


def _set_runtime_position(
    journal_dir: Path,
    *,
    account_id: str,
    instrument_id: str,
    symbol: str,
    net_quantity: str,
    currency: str = "USDT",
) -> None:
    import sqlite3

    with sqlite3.connect(journal_dir / "runtime_journal.db") as db:
        db.execute(
            """
            INSERT INTO fake_venue_positions (
                account_id, instrument_id, symbol, net_quantity, average_price, currency, updated_at
            ) VALUES (?, ?, ?, ?, NULL, ?, ?)
            ON CONFLICT(account_id, instrument_id) DO UPDATE SET
                symbol = excluded.symbol,
                net_quantity = excluded.net_quantity,
                updated_at = excluded.updated_at
            """,
            (
                account_id,
                instrument_id,
                symbol,
                net_quantity,
                currency,
                datetime.now(UTC).isoformat(),
            ),
        )


def _instruction_row(instruction_id: str):
    with connection() as db:
        return db.execute("SELECT * FROM strategy_runs WHERE id = ?", (instruction_id,)).fetchone()


def _attempt_rows(batch_id: str) -> list[dict[str, object]]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT attempt_number, idempotency_key, limit_price,
                   requested_quantity, order_id, status,
                   cancel_requested_at, cancel_terminal_at
            FROM funding_perpetual_attempts
            WHERE batch_id = ?
            ORDER BY attempt_number
            """,
            (batch_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _release_rows(batch_id: str) -> list[dict[str, object]]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT child_id, release_quantity, cumulative_spot_quantity, status, order_id
            FROM funding_spot_release_commands
            WHERE batch_id = ?
            ORDER BY created_at, child_id
            """,
            (batch_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _age_attempt(batch_id: str, attempt_number: int, *, seconds: int = 5) -> None:
    stale = (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat()
    with connection() as db:
        db.execute(
            """
            UPDATE funding_perpetual_attempts
            SET created_at = ?, updated_at = ?
            WHERE batch_id = ? AND attempt_number = ?
            """,
            (stale, stale, batch_id, attempt_number),
        )


def _assert_tick_aligned(value: str | object, tick: str) -> None:
    price = Decimal(str(value))
    tick_value = Decimal(tick)
    steps = price / tick_value
    assert steps == steps.to_integral_value(), (price, tick_value)


def _make_instruction(idempotency_key: str, *, quantity: str = "1") -> str:
    instruction = create_instruction(
        INSTANCE_ID,
        CreateStrategyInstructionRequest(
            idempotencyKey=idempotency_key,
            action="open",
            parameters={
                "perpetualSymbol": "BTCUSDT",
                "perpetualQuantity": quantity,
                "spotSymbol": "BTCUSDT",
                "spotQuantity": quantity,
            },
            reason="phase2 orchestration test",
        ),
        requested_by="ceo-test",
    )
    return str(instruction["instructionId"])


def _live_ceo_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Request-ID": "phase2-funding"}


def _configure_live_ceo_auth(tmp_path: Path) -> None:
    settings = get_settings()
    settings.environment = "development"
    settings.auth_mode = "development"
    settings.development_user_id = "ceo-principal-1"
    settings.database_path = str(tmp_path / "funding-phase2-auth.db")


def test_first_postonly_no_fill_is_not_treated_as_completed_and_uses_tick_aligned_attempt_price(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.03", ask="100.07")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="accepted_no_fill",
        cancel_terminal_after_queries=1,
    )

    instruction_id = _make_instruction("phase2-first-no-fill")
    result = execute_instruction(instruction_id)

    assert result.status == "executing"
    attempts = _attempt_rows(result.batch_id)
    assert len(attempts) == 1
    assert attempts[0]["attempt_number"] == 1
    _assert_tick_aligned(attempts[0]["limit_price"], "0.01")
    assert attempts[0]["status"] in {"acknowledged", "accepted"}
    assert _release_rows(result.batch_id) == []
    assert _instruction_row(instruction_id)["status"] == "executing"


def test_cancel_ack_is_not_terminal_and_repost_waits_for_authoritative_cancel_terminal(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.03", ask="100.07")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="accepted_no_fill",
        cancel_terminal_after_queries=1,
    )
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="accepted_no_fill",
        cancel_terminal_after_queries=1,
    )

    instruction_id = _make_instruction("phase2-cancel-terminal")
    first = execute_instruction(instruction_id)
    _age_attempt(first.batch_id, 1)

    second = execute_instruction(instruction_id)
    attempts_after_cancel_request = _attempt_rows(second.batch_id)
    assert len(attempts_after_cancel_request) == 1
    assert attempts_after_cancel_request[0]["cancel_requested_at"] is not None

    third = execute_instruction(instruction_id)
    attempts_after_ack = _attempt_rows(third.batch_id)
    assert len(attempts_after_ack) == 1, attempts_after_ack

    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.13", ask="100.17")
    fourth = execute_instruction(instruction_id)
    attempts_after_terminal = _attempt_rows(fourth.batch_id)
    assert len(attempts_after_terminal) == 2, attempts_after_terminal
    assert attempts_after_terminal[0]["status"] == "canceled"
    assert attempts_after_terminal[0]["cancel_terminal_at"] is not None
    assert attempts_after_terminal[1]["attempt_number"] == 2
    assert (
        attempts_after_terminal[1]["idempotency_key"]
        != attempts_after_terminal[0]["idempotency_key"]
    )
    _assert_tick_aligned(attempts_after_terminal[1]["limit_price"], "0.01")


def test_partial_fill_releases_first_spot_delta_and_repeat_resume_does_not_duplicate_release(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="0.4",
        partial_fill_price="100.1",
    )

    instruction_id = _make_instruction("phase2-partial-release")
    first = execute_instruction(instruction_id)
    second = execute_instruction(instruction_id)

    releases = _release_rows(second.batch_id)
    assert first.status == "partially_executed"
    assert second.status == "partially_executed"
    assert len(releases) == 1, releases
    assert Decimal(str(releases[0]["release_quantity"])) == Decimal("0.4")
    assert Decimal(str(releases[0]["cumulative_spot_quantity"])) == Decimal("0.4")
    assert releases[0]["status"] == "filled"

    with connection() as db:
        spot_commands = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM trade_commands
            WHERE idempotency_key LIKE 'funding-spot:%'
            """
        ).fetchone()
    assert int(spot_commands["count"]) == 1


def test_second_cumulative_fill_only_releases_new_decimal_delta(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="1.007",
        partial_fill_price="100.1",
    )
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="0.002",
        partial_fill_price="100.2",
    )

    instruction_id = _make_instruction("phase2-decimal-delta", quantity="1.009")
    first = execute_instruction(instruction_id)
    _age_attempt(first.batch_id, 1)
    execute_instruction(instruction_id)
    execute_instruction(instruction_id)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.1", ask="100.2")
    execute_instruction(instruction_id)
    execute_instruction(instruction_id)

    releases = _release_rows(first.batch_id)
    assert [Decimal(str(row["release_quantity"])) for row in releases] == [
        Decimal("1.007"),
        Decimal("0.002"),
    ]
    assert sum(
        (Decimal(str(row["release_quantity"])) for row in releases),
        Decimal("0"),
    ) == Decimal("1.009")


def test_second_attempt_uses_residual_quantity_and_caps_runtime_partial_fill_to_remaining(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="0.4",
        partial_fill_price="100.1",
        cancel_terminal_after_queries=1,
    )
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="1.0",
        partial_fill_price="100.2",
    )

    instruction_id = _make_instruction("phase2-residual-attempt")
    first = execute_instruction(instruction_id)
    _age_attempt(first.batch_id, 1)
    execute_instruction(instruction_id)
    execute_instruction(instruction_id)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.1", ask="100.2")
    execute_instruction(instruction_id)
    execute_instruction(instruction_id)

    attempts = _attempt_rows(first.batch_id)
    releases = _release_rows(first.batch_id)
    assert len(attempts) == 2, attempts
    assert Decimal(str(attempts[0]["requested_quantity"])) == Decimal("1")
    assert Decimal(str(attempts[1]["requested_quantity"])) == Decimal("0.6")
    assert [Decimal(str(row["release_quantity"])) for row in releases] == [
        Decimal("0.4"),
        Decimal("0.6"),
    ]


def test_same_instruction_concurrent_resume_claims_one_release_and_one_spot_command(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="0.5",
        partial_fill_price="100.1",
    )
    instruction_id = _make_instruction("phase2-concurrent-release")

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: execute_instruction(instruction_id), range(2)))

    batch_id = str(_instruction_row(instruction_id)["execution_batch_id"])
    releases = _release_rows(batch_id)
    assert len(releases) == 1, releases
    with connection() as db:
        count = db.execute(
            """
            SELECT COUNT(*) AS count FROM trade_commands
            WHERE idempotency_key LIKE 'funding-spot:%'
            """
        ).fetchone()
    assert int(count["count"]) == 1


def test_same_price_cancel_terminal_does_not_repost_until_quote_moves_one_tick(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.03", ask="100.07")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="accepted_no_fill",
        cancel_terminal_after_queries=1,
    )
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="accepted_no_fill",
        cancel_terminal_after_queries=1,
    )

    instruction_id = _make_instruction("phase2-no-same-price-repost")
    first = execute_instruction(instruction_id)
    _age_attempt(first.batch_id, 1)

    execute_instruction(instruction_id)
    execute_instruction(instruction_id)
    still_one = execute_instruction(instruction_id)

    attempts = _attempt_rows(still_one.batch_id)
    assert len(attempts) == 1, attempts
    assert attempts[0]["status"] == "canceled"

    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.04", ask="100.08")
    moved = execute_instruction(instruction_id)
    moved_attempts = _attempt_rows(moved.batch_id)
    assert len(moved_attempts) == 2, moved_attempts
    assert Decimal(str(moved_attempts[1]["limit_price"])) == Decimal("100.08")


def test_two_funding_instructions_cannot_hold_execution_lease_concurrently(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="accepted_no_fill",
        cancel_terminal_after_queries=1,
    )

    first_id = _make_instruction("phase2-lease-first")
    execute_instruction(first_id)
    second_id = _make_instruction("phase2-lease-second")

    with pytest.raises(HTTPException) as exc:
        execute_instruction(second_id)

    assert exc.value.status_code == 409
    assert "Active execution batch blocks new strategy instruction" in str(exc.value.detail)


def test_result_unknown_keeps_lease_and_creates_no_new_attempt_or_spot(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(journal_dir, symbol="BTCUSDT", behavior="result_unknown")

    instruction_id = _make_instruction("phase2-result-unknown")
    first = execute_instruction(instruction_id)
    second = execute_instruction(instruction_id)

    attempts = _attempt_rows(first.batch_id)
    assert first.status == "manual_intervention"
    assert second.status == "manual_intervention"
    assert len(attempts) == 1
    assert attempts[0]["status"] == "result_unknown"
    assert _release_rows(first.batch_id) == []


def test_unknown_order_status_is_fail_closed_to_result_unknown() -> None:
    assert _attempt_status_from_order_status("mystery_status") == "result_unknown"


def test_reconciling_instruction_completes_without_creating_new_attempt(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")

    instruction_id = _make_instruction("phase2-reconcile-complete")
    first = execute_instruction(instruction_id)
    second = execute_instruction(instruction_id)

    attempts = _attempt_rows(first.batch_id)
    assert first.status == "hedged"
    assert second.status == "hedged"
    assert len(attempts) == 1, attempts
    assert _instruction_row(instruction_id)["status"] == "completed"


def test_ttl_expiry_stops_new_attempts_directly(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="accepted_no_fill",
        cancel_terminal_after_queries=1,
    )

    instruction_id = _make_instruction("phase2-ttl-stop")
    first = execute_instruction(instruction_id)
    with connection() as db:
        stale = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
        db.execute(
            """
            UPDATE funding_perpetual_attempts
            SET created_at = ?, updated_at = ?
            WHERE batch_id = ?
            """,
            (stale, stale, first.batch_id),
        )
    execute_instruction(instruction_id)
    execute_instruction(instruction_id)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.1", ask="100.2")
    final_batch = execute_instruction(instruction_id)

    assert final_batch.status == "manual_intervention"
    assert "TTL expired" in str(final_batch.failure_reason)


def test_max_mutations_exhaustion_stops_reposts_directly(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    for _ in range(8):
        _seed_script(
            journal_dir,
            symbol="BTCUSDT",
            behavior="accepted_no_fill",
            cancel_terminal_after_queries=1,
        )

    instruction_id = _make_instruction("phase2-max-mutations")
    batch_id = None
    result = None
    for index in range(6):
        result = execute_instruction(instruction_id)
        batch_id = result.batch_id
        _age_attempt(result.batch_id, 2)
        execute_instruction(instruction_id)
        _set_quote(
            journal_dir,
            symbol="BTCUSDT",
            bid=str(100 + index + 1),
            ask=str(100.1 + index + 1),
        )
        result = execute_instruction(instruction_id)
        if index < 5:
            assert result.status == "executing"
        else:
            assert result.status == "manual_intervention"
    assert result is not None
    assert batch_id is not None
    attempts = _attempt_rows(batch_id)
    assert len(attempts) == 6
    assert "maxMutations exhausted" in str(result.failure_reason)


def test_restart_recovery_resumes_without_duplicate_release(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="0.5",
        partial_fill_price="100.1",
    )

    instruction_id = _make_instruction("phase2-restart-recovery")
    first = execute_instruction(instruction_id)
    settings = get_settings()
    settings.database_path = str(tmp_path / "funding-phase2-orchestration.db")
    apply_platform_migrations()
    second = execute_instruction(instruction_id)

    assert first.status == "partially_executed"
    assert second.status == "partially_executed"
    assert len(_release_rows(first.batch_id)) == 1


def test_residual_quantity_is_quantized_and_total_requested_never_exceeds_maximum(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="0.9995",
        partial_fill_price="100.1",
        cancel_terminal_after_queries=1,
    )
    _seed_script(
        journal_dir,
        symbol="BTCUSDT",
        behavior="partial_fill",
        partial_fill_quantity="1.0",
        partial_fill_price="100.2",
    )

    instruction_id = _make_instruction("phase2-residual-quantized")
    first = execute_instruction(instruction_id)
    _age_attempt(first.batch_id, 1)
    execute_instruction(instruction_id)
    execute_instruction(instruction_id)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100.1", ask="100.2")
    execute_instruction(instruction_id)
    execute_instruction(instruction_id)

    attempts = _attempt_rows(first.batch_id)
    assert len(attempts) == 1
    assert Decimal(str(attempts[0]["requested_quantity"])) == Decimal("1")
    with connection() as db:
        total_requested = db.execute(
            """
            SELECT COALESCE(SUM(CAST(requested_quantity AS REAL)), 0) AS total
            FROM funding_perpetual_attempts
            WHERE batch_id = ?
            """,
            (first.batch_id,),
        ).fetchone()
    assert Decimal(str(total_requested["total"])) <= Decimal("1")


def test_reconciliation_query_unavailable_keeps_instruction_reconciling(
    runtime: tuple[str, Path],
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")

    instruction_id = _make_instruction("phase2-reconcile-unavailable")
    first = execute_instruction(instruction_id)

    from app.strategies import funding_orchestration as orchestration

    original_runtime_get = orchestration._runtime_get

    def blocked_runtime_get(path: str, *args, **kwargs):
        if path == "/venue/positions":
            raise HTTPException(status_code=502, detail="runtime unavailable")
        return original_runtime_get(path, *args, **kwargs)

    monkeypatch.setattr(orchestration, "_runtime_get", blocked_runtime_get)
    second = execute_instruction(instruction_id)

    assert first.status == "hedged"
    assert second.status == "hedged"
    assert _instruction_row(instruction_id)["status"] == "reconciling"


def test_reconciliation_position_mismatch_enters_manual_intervention(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, journal_dir = runtime
    _seed_environment(tmp_path, runtime_url)
    _set_quote(journal_dir, symbol="BTCUSDT", bid="100", ask="100.1")

    instruction_id = _make_instruction("phase2-reconcile-mismatch")
    first = execute_instruction(instruction_id)
    _set_runtime_position(
        journal_dir,
        account_id=ACCOUNT_ID,
        instrument_id="instrument_btc_usdt_perp",
        symbol="BTCUSDT",
        net_quantity="-2",
    )
    second = execute_instruction(instruction_id)

    assert first.status == "hedged"
    assert second.status == "manual_intervention"
    assert "mismatches plan" in str(second.failure_reason)


def test_hedged_batch_leaves_instruction_in_reconciling_and_legacy_route_uses_principal_user_id(
    runtime: tuple[str, Path],
    tmp_path: Path,
) -> None:
    runtime_url, _journal_dir = runtime
    _configure_live_ceo_auth(tmp_path)
    settings = get_settings()
    settings.default_trading_environment = "simulation"
    settings.runtime_base_url = runtime_url
    settings.live_trading_enabled = True
    initialize_database()
    apply_platform_migrations()
    with connection() as db:
        db.execute("UPDATE accounts SET status = 'active' WHERE id = ?", (ACCOUNT_ID,))
        db.execute(
            "UPDATE strategy_instances SET status = 'active' WHERE id = ?",
            (INSTANCE_ID,),
        )

    with TestClient(app) as client:
        response = client.post(
            FUNDING_ENDPOINT,
            json={
                "action": "OPEN_SHORT_PERP_LONG_SPOT",
                "perpetualSymbol": "BTCUSDT",
                "spotSymbol": "BTC",
                "quantity": "1",
                "idempotencyKey": "phase2-requested-by",
            },
        )

    assert response.status_code == 200, response.text
    batch = response.json()
    assert batch["status"] == "hedged", batch
    with connection() as db:
        row = db.execute(
            "SELECT requested_by, status FROM strategy_runs WHERE idempotency_key = ?",
            ("phase2-requested-by",),
        ).fetchone()
    assert row is not None
    assert row["requested_by"] == "ceo-principal-1"
    assert row["status"] == "reconciling"


def test_controlled_live_funding_still_returns_423(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "funding-phase2-live-gate.db")
    settings.live_trading_enabled = True
    settings.environment = "development"
    settings.auth_mode = "development"
    settings.default_trading_environment = "live"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/funding/market-command",
            json={
                "action": "OPEN_SHORT_PERP_LONG_SPOT",
                "perpetualSymbol": "BTCUSDT",
                "spotSymbol": "BTC",
                "quantity": "1",
            },
        )

    assert response.status_code == 423
    assert response.json()["detail"] == (
        "Funding controlled-live execution requires Phase 2 post-only "
        "chase and authoritative incremental release"
    )
