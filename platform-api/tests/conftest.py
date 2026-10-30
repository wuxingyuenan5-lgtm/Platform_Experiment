"""Assign every backend test to one executable test layer."""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import pytest

ARCHITECTURE_PATTERNS = ("architecture", "boundary", "boundaries")
LIVE_SAFETY_PATTERNS = (
    "disaster_recovery",
    "live",
    "redaction",
    "safety",
    "secret",
)
INTEGRATION_PATTERNS = (
    "audit",
    "auth",
    "batch",
    "catalog",
    "command",
    "concurrency",
    "contract",
    "financial_facts",
    "flow",
    "health",
    "idempotency",
    "journal",
    "migration",
    "monitoring",
    "readiness",
    "reconciliation",
    "session",
    "venue",
)
PRIMARY_MARKERS = ("architecture", "unit", "integration", "live_safety")


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    """Prevent one isolated test's auth, live gates or Runtime URL leaking to another."""
    from app.config import get_settings

    settings = get_settings()
    for name in type(settings).model_fields:
        monkeypatch.setattr(settings, name, getattr(settings, name))
    settings.strategy_research_database_path = None
    settings.runtime_base_url = "http://127.0.0.1:1"
    settings.database_path = str(tmp_path / "platform.db")
    settings.strategy_research_enabled = False
    settings.strategy_research_path = str(tmp_path / "strategy-research")
    settings.choice_csd_enabled = False


@pytest.fixture(autouse=True)
def isolated_test_network(monkeypatch):
    """Tests may reach only isolated loopback servers, never business services or venues."""
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex

    def isolated_connect(sock, address):
        if isinstance(address, tuple) and (
            address[0] not in {"127.0.0.1", "::1"} or address[1] in {8000, 8100, 4373}
        ):
            raise AssertionError(
                "Test attempted to connect to a business service or external network"
            )
        return connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", isolated_connect)

    def isolated_connect_ex(sock, address):
        if isinstance(address, tuple) and (
            address[0] not in {"127.0.0.1", "::1"} or address[1] in {8000, 8100, 4373}
        ):
            raise AssertionError(
                "Test attempted to connect to a business service or external network"
            )
        return connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect_ex", isolated_connect_ex)


@pytest.fixture
def authorize_funding_ceo():
    """Give legacy Funding endpoint checks a real isolated browser session."""
    from datetime import UTC, datetime

    from app.config import get_settings
    from app.user_service import create_initial_ceo, issue_browser_session

    def authorize(client):
        user = create_initial_ceo(
            username="funding-owner", password="isolated funding test password 123!"
        )
        issued = issue_browser_session(
            user_id=user.id, ip_address="127.0.0.1", user_agent="pytest", now=datetime.now(UTC)
        )
        settings = get_settings()
        client.cookies.set(settings.session_cookie_name, issued.session_token)
        client.headers.update(
            {"Origin": settings.allowed_cors_origins[0], "X-CSRF-Token": issued.csrf_token}
        )

    return authorize


@pytest.fixture
def generic_trading_instance(monkeypatch, request):
    """Generic pipeline tests use an isolated SIM desk, not a controlled CEO desk."""
    from app import application
    from app.database import connection

    initialize = application.initialize_database

    def initialize_generic_desk():
        initialize()
        with connection() as db:
            for original, target in (
                ("strategy_funding_arbitrage_instance_default", "strategy_generic_pipeline_test"),
                ("strategy_cross_venue_spread_instance_default", "strategy_generic_cross_test"),
            ):
                values = dict(
                    db.execute(
                        "SELECT * FROM strategy_instances WHERE id=?", (original,)
                    ).fetchone()
                )
                # A new instance ID does not change strategy authority. Generic
                # pipeline tests need a genuinely separate strategy definition,
                # not a renamed Cross/Funding instance that bypasses the gate.
                definition = dict(db.execute(
                    "SELECT * FROM strategy_definitions WHERE id=?",
                    (values["strategy_definition_id"],),
                ).fetchone())
                definition.update(id=target + "_definition", strategy_key=target)
                db.execute(
                    f"INSERT OR IGNORE INTO strategy_definitions ({','.join(definition)}) "
                    f"VALUES ({','.join('?' for _ in definition)})", tuple(definition.values()),
                )
                version = dict(db.execute(
                    "SELECT * FROM strategy_versions WHERE id=?", (values["strategy_version_id"],),
                ).fetchone())
                version.update(id=target + "_version", strategy_definition_id=definition["id"])
                db.execute(
                    f"INSERT OR IGNORE INTO strategy_versions ({','.join(version)}) "
                    f"VALUES ({','.join('?' for _ in version)})", tuple(version.values()),
                )
                values.update(
                    strategy_definition_id=definition["id"], strategy_version_id=version["id"]
                )
                values.update(id=target, status="active", trading_mode="simulation")
                db.execute(
                    f"INSERT OR IGNORE INTO strategy_instances ({','.join(values)}) "
                    f"VALUES ({','.join('?' for _ in values)})",
                    tuple(values.values()),
                )
                for row in db.execute(
                    "SELECT * FROM strategy_account_bindings WHERE strategy_instance_id=? "
                    "AND account_id='account_sim_usdt'",
                    (original,),
                ).fetchall():
                    binding = dict(row)
                    binding.update(
                        id="generic:" + binding["id"], strategy_instance_id=target, status="active"
                    )
                    db.execute(
                        f"INSERT OR IGNORE INTO strategy_account_bindings ({','.join(binding)}) "
                        f"VALUES ({','.join('?' for _ in binding)})",
                        tuple(binding.values()),
                    )
            # Raw legacy Order tests must also use an account outside controlled desks.
            db.execute(
                "UPDATE strategy_account_bindings SET status='inactive' "
                "WHERE account_id='account_sim_usdt' AND strategy_instance_id IN (?,?)",
                (
                    "strategy_funding_arbitrage_instance_default",
                    "strategy_cross_venue_spread_instance_default",
                ),
            )

    monkeypatch.setattr(application, "initialize_database", initialize_generic_desk)
    if hasattr(request.module, "initialize_database"):
        monkeypatch.setattr(request.module, "initialize_database", initialize_generic_desk)


@pytest.fixture(autouse=True)
def deterministic_funding_ticks(monkeypatch):
    """Unit/API tests drive ticks explicitly; browser subprocess tests run the real monitor."""
    from app.strategies import funding_runner

    async def wait_for_stop(stop):
        await stop.wait()

    monkeypatch.setattr(funding_runner, "run_funding_instruction_monitor", wait_for_stop)


@pytest.fixture(autouse=True)
def deterministic_account_snapshot_ticks(monkeypatch):
    """Snapshot tests invoke sync explicitly against their isolated Runtime stub."""
    from app import live_venue_snapshot_sync

    async def wait_for_cancellation():
        await asyncio.Event().wait()

    monkeypatch.setattr(
        live_venue_snapshot_sync, "run_snapshot_sync_monitor", wait_for_cancellation
    )


def classify_test_file(path: Path) -> str:
    """Return the default primary layer for an unmarked backend test module."""

    name = path.stem.lower()
    if any(pattern in name for pattern in ARCHITECTURE_PATTERNS):
        return "architecture"
    if any(pattern in name for pattern in LIVE_SAFETY_PATTERNS):
        return "live_safety"
    if any(pattern in name for pattern in INTEGRATION_PATTERNS):
        return "integration"
    return "unit"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Require one explicit or inferred primary marker for every backend test."""

    for item in items:
        explicit_markers = {
            name for name in PRIMARY_MARKERS if item.get_closest_marker(name) is not None
        }
        if len(explicit_markers) > 1:
            raise pytest.UsageError(
                f"{item.nodeid} must have exactly one primary test marker; "
                f"found {sorted(explicit_markers)}"
            )

        if explicit_markers:
            marker = next(iter(explicit_markers))
        else:
            marker = classify_test_file(Path(str(item.path)))
            item.add_marker(getattr(pytest.mark, marker))

        primary_markers = {
            name for name in PRIMARY_MARKERS if item.get_closest_marker(name) is not None
        }
        if primary_markers != {marker}:
            raise pytest.UsageError(
                f"{item.nodeid} must have exactly one primary test marker; "
                f"found {sorted(primary_markers)}"
            )
