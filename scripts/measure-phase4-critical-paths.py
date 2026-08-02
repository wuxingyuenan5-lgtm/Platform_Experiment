from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_component(
    root: Path,
    component: str,
    code: str,
    iterations: int,
) -> dict[str, object]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / component)
    env["PHASE4_ITERATIONS"] = str(iterations)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root / component,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


RUNTIME = r'''
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from app.config import get_settings
from app.journal import (
    claim_command,
    get_events,
    initialize_journal,
    mark_command_result_unknown,
    save_command_events,
)
from app.models import ExecutionEvent, SubmitOrderCommand, VenueOrderSnapshot
from app.runtime_recovery import recover_command

iterations = int(os.environ["PHASE4_ITERATIONS"])
temporary_root = Path(tempfile.mkdtemp())
get_settings().journal_path = str(temporary_root / "runtime.db")
initialize_journal()


def command(index):
    return SubmitOrderCommand(
        command_id=f"bench-command-{index}",
        platform_order_id=f"bench-order-{index}",
        account_id="account-bench",
        instrument_id="instrument-btc",
        symbol="BTCUSDT",
        side="buy",
        order_type="limit",
        quantity="1",
        price="100",
        received_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )


started = time.perf_counter()
for index in range(iterations):
    assert claim_command(command(index))
command_claim_seconds = time.perf_counter() - started

started = time.perf_counter()
for index in range(iterations):
    current = command(index)
    save_command_events(
        current,
        [
            ExecutionEvent(
                event_id=f"ack-{index}",
                command_id=current.command_id,
                platform_order_id=current.platform_order_id,
                event_type="order_acknowledged",
                external_order_id=f"ext-{index}",
            ),
            ExecutionEvent(
                event_id=f"fill-{index}",
                command_id=current.command_id,
                platform_order_id=current.platform_order_id,
                event_type="order_filled",
                external_order_id=f"ext-{index}",
                fill_price=Decimal("100"),
                fill_quantity=Decimal("1"),
            ),
        ],
    )
    assert len(get_events(current.command_id)) == 2
journal_write_read_seconds = time.perf_counter() - started

recovery_start = iterations
for index in range(recovery_start, recovery_start + iterations):
    current = command(index)
    assert claim_command(current)
    assert mark_command_result_unknown(current.command_id)


class Gateway:
    name = "benchmark"

    def submit_order(self, current):
        raise AssertionError("Recovery must never submit a command")

    def get_order(self, *, platform_order_id):
        index = int(platform_order_id.rsplit("-", 1)[1])
        current = command(index)
        return VenueOrderSnapshot(
            source="bench",
            externalOrderId=f"ext-{index}",
            platformOrderId=current.platform_order_id,
            commandId=current.command_id,
            accountId=current.account_id,
            instrumentId=current.instrument_id,
            symbol=current.symbol,
            side=current.side,
            orderType=current.order_type,
            quantity=current.quantity,
            price=current.price,
            status="accepted",
            filledQuantity=Decimal("0"),
            remainingQuantity=current.quantity,
            occurredAt=datetime(2026, 8, 2, 12, 1, tzinfo=UTC),
            asOf=datetime(2026, 8, 2, 12, 1, tzinfo=UTC),
        )

    def list_fills(self, **kwargs):
        return []


gateway = Gateway()
started = time.perf_counter()
for index in range(recovery_start, recovery_start + iterations):
    assert len(recover_command(command(index).command_id, gateway=gateway)) == 1
result_unknown_recovery_seconds = time.perf_counter() - started

print(
    json.dumps(
        {
            "iterations": iterations,
            "command_claim_seconds": command_claim_seconds,
            "journal_write_read_seconds": journal_write_read_seconds,
            "result_unknown_recovery_seconds": result_unknown_recovery_seconds,
        }
    )
)
'''

PLATFORM = r'''
import json
import os
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
import app.trade_command_execution as execution

iterations = max(10, int(os.environ["PHASE4_ITERATIONS"]) // 4)
temporary_root = Path(tempfile.mkdtemp())
get_settings().database_path = str(temporary_root / "platform.db")


class Response:
    def __init__(self, command):
        self.command = command

    def raise_for_status(self):
        return None

    def json(self):
        command_id = self.command["command_id"]
        platform_order_id = self.command["platform_order_id"]
        external_order_id = f"ext-{command_id}"
        return [
            {
                "event_id": f"ack-{command_id}",
                "command_id": command_id,
                "platform_order_id": platform_order_id,
                "event_type": "order_acknowledged",
                "external_order_id": external_order_id,
                "fill_price": None,
                "fill_quantity": None,
                "occurred_at": "2026-08-02T12:00:00+00:00",
                "reason": None,
            },
            {
                "event_id": f"fill-{command_id}",
                "command_id": command_id,
                "platform_order_id": platform_order_id,
                "event_type": "order_filled",
                "external_order_id": external_order_id,
                "fill_price": "100",
                "fill_quantity": "1",
                "occurred_at": "2026-08-02T12:00:01+00:00",
                "reason": None,
            },
        ]


execution.httpx.post = lambda *args, **kwargs: Response(kwargs["json"])
payload = {
    "accountId": "account_sim_usdt",
    "instrumentId": "instrument_btc_usdt",
    "symbol": "BTCUSDT",
    "side": "buy",
    "orderType": "limit",
    "quantity": "1",
    "price": "100",
}
with TestClient(app) as client:
    started = time.perf_counter()
    for index in range(iterations):
        request = dict(payload)
        request["idempotencyKey"] = f"bench-{index}"
        response = client.post("/api/v1/trading/orders", json=request)
        assert response.status_code == 200, response.text
    platform_trading_route_seconds = time.perf_counter() - started

print(
    json.dumps(
        {
            "iterations": iterations,
            "platform_trading_route_seconds": platform_trading_route_seconds,
        }
    )
)
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()
    payload = {
        "runtime": run_component(
            args.root,
            "execution-runtime",
            RUNTIME,
            args.iterations,
        ),
        "platform_api": run_component(
            args.root,
            "platform-api",
            PLATFORM,
            args.iterations,
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
