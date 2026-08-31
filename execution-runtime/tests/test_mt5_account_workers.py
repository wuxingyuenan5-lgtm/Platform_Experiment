from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import Settings, get_settings
from app.gateway_errors import GatewayConfigurationError, GatewayResultUnknownError
from app.journal import claim_command, initialize_journal
from app.models import SubmitOrderCommand
from app.mt5_account_worker import (
    Mt5AccountWorkerClient,
    Mt5AccountWorkerSupervisor,
    _prove_worker_ready,
)


class AccountAdapter:
    name = "mt5_live"

    def __init__(self, account_id: str, *, fail: bool = False) -> None:
        self.account_id = account_id
        self.fail = fail

    def list_positions(self, account_id: str):
        assert account_id == self.account_id
        if self.fail:
            raise RuntimeError(f"worker failed:{account_id}")
        return [SimpleNamespace(account_id=account_id)]

    def capability(self):
        return SimpleNamespace(
            configured=True,
            operational=True,
            write_enabled=False,
            missing_requirements=[],
        )


class AccountSupervisor:
    def __init__(self) -> None:
        self.adapters = {
            "mt5-live-main": AccountAdapter("mt5-live-main"),
            "account_mt5_short_term_a": AccountAdapter(
                "account_mt5_short_term_a", fail=True
            ),
        }

    def adapter(self, account_id: str):
        return self.adapters[account_id]

    def missing_requirements(self):
        return []

    def close(self):
        return None


class UnusedBybit:
    name = "bybit_live"


def test_supervisor_requires_distinct_terminal_paths(tmp_path) -> None:
    terminal = tmp_path / "terminal64.exe"
    terminal.write_bytes(b"terminal")
    settings = Settings(
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_primary_account_id="mt5-live-main",
        mt5_account_terminal_paths=(
            f"mt5-live-main={terminal},account_mt5_short_term_a={terminal}"
        ),
    )

    missing = Mt5AccountWorkerSupervisor(settings).missing_requirements()

    assert any("MT5_TERMINAL_SHARED_WITH" in item for item in missing)


def test_gateway_routes_accounts_to_independent_workers() -> None:
    supervisor = AccountSupervisor()
    settings = Settings(
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_primary_account_id="mt5-live-main",
    )
    gateway = BybitMt5Gateway(
        settings=settings,
        bybit=cast(Any, UnusedBybit()),
        mt5_supervisor=cast(Any, supervisor),
    )

    positions = gateway.list_positions("mt5-live-main")

    assert positions[0].account_id == "mt5-live-main"
    with pytest.raises(RuntimeError, match="short_term_a"):
        gateway.list_positions("account_mt5_short_term_a")
    assert gateway.list_positions("mt5-live-main")[0].account_id == "mt5-live-main"


def test_worker_ready_requires_authoritative_account_identity() -> None:
    class Gateway:
        def get_account_snapshot(self, account_id: str):
            return SimpleNamespace(account_id=f"wrong-{account_id}")

    with pytest.raises(GatewayConfigurationError, match="account identity mismatch"):
        _prove_worker_ready(Gateway(), "mt5-live-main")


def test_worker_rpc_surface_is_explicit() -> None:
    client = Mt5AccountWorkerClient(
        settings=Settings(),
        account_id="mt5-live-main",
        terminal_path="C:/MT5/terminal64.exe",
    )

    with pytest.raises(AttributeError):
        client.delete_everything()


def test_unresolved_account_command_blocks_new_worker_write(tmp_path) -> None:
    journal_path = str(tmp_path / "runtime-journal.db")
    get_settings().journal_path = journal_path
    settings = Settings(journal_path=journal_path)
    initialize_journal()
    previous = SubmitOrderCommand(
        command_id="command-previous",
        platform_order_id="order-previous",
        strategy_instance_id="strategy-cross",
        account_id="mt5-live-main",
        instrument_id="instrument-xauusd",
        symbol="XAUUSD.s",
        side="buy",
        order_type="market",
        quantity="0.01",
    )
    current = previous.model_copy(
        update={
            "command_id": "command-current",
            "platform_order_id": "order-current",
        }
    )
    assert claim_command(previous) is True
    client = Mt5AccountWorkerClient(
        settings=settings,
        account_id="mt5-live-main",
        terminal_path="C:/MT5/terminal64.exe",
    )

    with pytest.raises(GatewayResultUnknownError, match="unresolved Runtime command"):
        client.submit_order(current)
