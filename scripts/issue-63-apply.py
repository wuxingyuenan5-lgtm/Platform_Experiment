from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "platform-backend/app"
TESTS = ROOT / "platform-backend/tests"


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise SystemExit(f"expected exactly one match in {path}: {old[:100]!r}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


(APP / "trade_command_execution.py").write_text(
    '''from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import get_settings
from app.database import connection
from app.runtime_contracts import RuntimeExecutionEventV1, RuntimeSubmitOrderCommandV1
from app.schemas import CreateOrderRequest, OrderResponse
from app.security import enforce_order_safety
from app.trading import (
    apply_execution_events,
    decimal_text,
    get_order_response,
    mark_order_result_unknown,
    now_iso,
)

SubmissionMode = Literal["legacy", "v1"]


def submit_order_through_runtime(
    request: CreateOrderRequest,
    *,
    mode: SubmissionMode,
    strategy_instance_id: str | None = None,
    command_id: str | None = None,
    reduce_only: bool = False,
) -> OrderResponse:
    """Create one local Order and submit it through the selected Runtime contract mode."""

    if mode == "v1":
        if strategy_instance_id is None or command_id is None:
            raise ValueError("V1 order submission requires Strategy and Command identity")
        resolved_command_id = command_id
    else:
        resolved_command_id = command_id or str(uuid4())

    settings = get_settings()
    order_id = str(uuid4())
    created_at = now_iso()

    if request.order_type == "limit" and request.price is None:
        raise HTTPException(status_code=422, detail="Limit orders require price")

    if mode == "v1":
        enforce_order_safety(
            request.account_id,
            request.instrument_id,
            request.quantity,
            request.price,
            strategy_instance_id=strategy_instance_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            command_id=resolved_command_id,
        )
    else:
        enforce_order_safety(
            request.account_id,
            request.instrument_id,
            request.quantity,
            request.price,
        )

    with connection() as db:
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side,
                order_type, quantity, price, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                resolved_command_id,
                request.account_id,
                request.instrument_id,
                request.symbol,
                request.side,
                request.order_type,
                decimal_text(request.quantity),
                decimal_text(request.price) if request.price is not None else None,
                "processing",
                created_at,
                created_at,
            ),
        )

    if mode == "v1":
        command_payload = RuntimeSubmitOrderCommandV1(
            command_id=resolved_command_id,
            platform_order_id=order_id,
            strategy_instance_id=strategy_instance_id,
            account_id=request.account_id,
            instrument_id=request.instrument_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            reduce_only=reduce_only,
        ).model_dump(mode="json")
    else:
        command_payload = {
            "command_id": resolved_command_id,
            "platform_order_id": order_id,
            "account_id": request.account_id,
            "instrument_id": request.instrument_id,
            "symbol": request.symbol,
            "side": request.side,
            "order_type": request.order_type,
            "quantity": decimal_text(request.quantity),
            "price": decimal_text(request.price) if request.price is not None else None,
        }

    try:
        response = httpx.post(
            f"{settings.runtime_base_url}/commands/orders",
            json=command_payload,
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
        if mode == "v1":
            events = [
                event.model_dump(mode="json")
                for event in (
                    RuntimeExecutionEventV1.model_validate(item)
                    for item in response.json()
                )
            ]
        else:
            events = response.json()
    except httpx.HTTPError:
        mark_order_result_unknown(order_id)
        return get_order_response(order_id)
    except (ValidationError, TypeError):
        if mode != "v1":
            raise
        mark_order_result_unknown(order_id)
        return get_order_response(order_id)

    apply_execution_events(
        order_id,
        request,
        events,
        expected_command_id=resolved_command_id,
    )
    return get_order_response(order_id)


def submit_trade_command_order(
    request: CreateOrderRequest,
    *,
    strategy_instance_id: str,
    command_id: str,
    reduce_only: bool = False,
) -> OrderResponse:
    """Submit through the authoritative versioned Runtime contract."""

    return submit_order_through_runtime(
        request,
        mode="v1",
        strategy_instance_id=strategy_instance_id,
        command_id=command_id,
        reduce_only=reduce_only,
    )


def estimated_order_notional(request: CreateOrderRequest) -> Decimal | None:
    if request.price is None:
        return None
    return request.quantity * request.price
''',
    encoding="utf-8",
)

trading_path = APP / "trading.py"
replace_once(trading_path, "from uuid import uuid4\n\n", "")
replace_once(trading_path, "from app.security import enforce_order_safety\n", "")
replace_once(
    trading_path,
    '''def submit_order(request: CreateOrderRequest, command_id: str | None = None) -> OrderResponse:
    settings = get_settings()
    order_id = str(uuid4())
    command_id = command_id or str(uuid4())
    created_at = now_iso()

    if request.order_type == "limit" and request.price is None:
        raise HTTPException(status_code=422, detail="Limit orders require price")

    enforce_order_safety(
        request.account_id,
        request.instrument_id,
        request.quantity,
        request.price,
    )

    with connection() as db:
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side,
                order_type, quantity, price, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                command_id,
                request.account_id,
                request.instrument_id,
                request.symbol,
                request.side,
                request.order_type,
                decimal_text(request.quantity),
                decimal_text(request.price) if request.price is not None else None,
                "processing",
                created_at,
                created_at,
            ),
        )

    command = {
        "command_id": command_id,
        "platform_order_id": order_id,
        "account_id": request.account_id,
        "instrument_id": request.instrument_id,
        "symbol": request.symbol,
        "side": request.side,
        "order_type": request.order_type,
        "quantity": decimal_text(request.quantity),
        "price": decimal_text(request.price) if request.price is not None else None,
    }

    try:
        response = httpx.post(
            f"{settings.runtime_base_url}/commands/orders",
            json=command,
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
        events = response.json()
    except httpx.HTTPError:
        mark_order_result_unknown(order_id)
        return get_order_response(order_id)

    apply_execution_events(
        order_id,
        request,
        events,
        expected_command_id=command_id,
    )
    return get_order_response(order_id)
''',
    '''def submit_order(request: CreateOrderRequest, command_id: str | None = None) -> OrderResponse:
    """Compatibility entry point for the deprecated raw order endpoint."""

    from app.trade_command_execution import submit_order_through_runtime

    return submit_order_through_runtime(
        request,
        mode="legacy",
        command_id=command_id,
    )
''',
)

(TESTS / "test_order_submission_orchestration.py").write_text(
    '''from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


class FakeRuntimeResponse:
    def __init__(self, payload: dict[str, object], events: list[dict[str, object]]) -> None:
        self.payload = payload
        self.events = events

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, object]]:
        return self.events


def acknowledged_event(payload: dict[str, object]) -> dict[str, object]:
    return {
        "event_id": "submission-ack-001",
        "command_id": payload["command_id"],
        "platform_order_id": payload["platform_order_id"],
        "event_type": "order_acknowledged",
        "external_order_id": "external-submission-001",
        "fill_price": None,
        "fill_quantity": None,
        "occurred_at": "2026-07-24T00:00:00+00:00",
        "reason": None,
    }


def test_legacy_order_endpoint_preserves_raw_runtime_payload(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "legacy-submission.db")
    captured: dict[str, object] = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return FakeRuntimeResponse(json, [acknowledged_event(json)])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/orders",
            json={
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "1.25",
                "price": "100",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"
    assert set(captured) == {
        "command_id",
        "platform_order_id",
        "account_id",
        "instrument_id",
        "symbol",
        "side",
        "order_type",
        "quantity",
        "price",
    }
    assert captured["account_id"] == ACCOUNT_ID
    assert captured["instrument_id"] == INSTRUMENT_ID
    assert captured["quantity"] == "1.25"
    assert captured["price"] == "100"


def test_trade_command_keeps_v1_payload_and_marks_invalid_events_unknown(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "v1-submission.db")
    captured: dict[str, object] = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return FakeRuntimeResponse(json, [{"unexpected": "event"}])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/commands",
            json={
                "idempotencyKey": "unified-submission-v1-001",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "market",
                "quantity": "0.01",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "result_unknown"
    assert captured["contract_name"] == "runtime-command"
    assert captured["contract_version"] == "1.0"
    assert captured["payload_version"] == "1.0"
    assert captured["strategy_instance_id"] == STRATEGY_ID
    assert captured["reduce_only"] is False
''',
    encoding="utf-8",
)

(TESTS / "test_architecture_order_submission.py").write_text(
    '''import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "trade_command_execution.py"
COMPATIBILITY_PATH = APP_ROOT / "trading.py"


def function_names(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_trade_command_execution_is_the_single_submission_owner() -> None:
    owner_source = OWNER_PATH.read_text(encoding="utf-8")
    compatibility_source = COMPATIBILITY_PATH.read_text(encoding="utf-8")

    assert owner_source.count("INSERT INTO orders") == 1
    assert compatibility_source.count("INSERT INTO orders") == 0
    assert owner_source.count("/commands/orders") == 1
    assert compatibility_source.count("/commands/orders") == 0
    assert owner_source.count("httpx.post(") == 1
    assert compatibility_source.count("httpx.post(") == 0


def test_legacy_and_v1_entry_points_delegate_to_the_owner() -> None:
    owner_functions = function_names(OWNER_PATH)
    compatibility_source = COMPATIBILITY_PATH.read_text(encoding="utf-8")

    assert "submit_order_through_runtime" in owner_functions
    assert "submit_trade_command_order" in owner_functions
    assert "from app.trade_command_execution import submit_order_through_runtime" in compatibility_source
    assert 'mode="legacy"' in compatibility_source


def test_owner_retains_explicit_legacy_and_v1_modes() -> None:
    source = OWNER_PATH.read_text(encoding="utf-8")

    assert 'SubmissionMode = Literal["legacy", "v1"]' in source
    assert 'mode="v1"' in source
    assert '"contract_name"' not in COMPATIBILITY_PATH.read_text(encoding="utf-8")
''',
    encoding="utf-8",
)

ownership = ROOT / "docs/architecture/OWNERSHIP.md"
replace_once(
    ownership,
    "| Operational fill projection | `platform-backend/app/trading.py` | Low-latency `positions` and `pnl_results` updates | Formal accounting authority |\n",
    "| Platform order submission orchestration | `platform-backend/app/trade_command_execution.py` | Single local Order creation, Safety enforcement, legacy/V1 Runtime dispatch, unknown-result handling and Event handoff | Event projection, reconciliation or formal accounting |\n"
    "| Operational fill projection | `platform-backend/app/trading.py` | Low-latency `positions` and `pnl_results` updates plus explicit legacy submission compatibility export | Authoritative order submission or formal accounting |\n",
)

architecture = ROOT / "docs/architecture/README.md"
replace_once(
    architecture,
    "- Platform 收到无法验证的 Event 时保留 `result_unknown`，不得解释为确定失败或自动重下。\n",
    "- Platform 收到无法验证的 Event 时保留 `result_unknown`，不得解释为确定失败或自动重下。\n"
    "- `platform-backend/app/trade_command_execution.py` 是本地 Order 创建、Safety、Runtime 提交和未知结果处理的唯一编排 Owner。\n"
    "- `platform-backend/app/trading.py::submit_order` 只保留 deprecated 兼容入口；legacy raw payload 与 TradeCommand V1 payload 由 Owner 显式区分。\n",
)

checker = ROOT / "scripts/check-documentation-consistency.py"
replace_once(
    checker,
    '    "Operational fill projection": "platform-backend/app/trading.py",\n',
    '    "Platform order submission orchestration": "platform-backend/app/trade_command_execution.py",\n'
    '    "Operational fill projection": "platform-backend/app/trading.py",\n',
)

state = ROOT / "docs/codex/current-state.md"
replace_once(
    state,
    "No engineering code workstream is active by default after PR #62 merges.",
    "Issue #63 / Draft PR #64 is the only active engineering workstream: Platform order-submission orchestration unification.",
)

changelog = ROOT / "CHANGELOG.md"
entry = '''### Unified Platform order submission orchestration — Issue #63 / PR #64

- Made `platform-backend/app/trade_command_execution.py` the single local Order/Safety/Runtime submission implementation.
- Reduced `platform-backend/app/trading.py::submit_order` to a deprecated compatibility delegate.
- Preserved the exact legacy raw payload keys and the typed TradeCommand V1 Strategy/version/`reduceOnly` payload.
- Added payload-equivalence, invalid-V1-event `result_unknown` and sole-owner architecture checks.
- Preserved APIs, Order/Fill persistence, Event application, operational projections, Runtime contracts and both Live Write defaults.

'''
marker = "## Unreleased\n\n"
content = changelog.read_text(encoding="utf-8")
if entry not in content:
    if marker not in content:
        raise SystemExit("Changelog Unreleased marker not found")
    changelog.write_text(content.replace(marker, marker + entry, 1), encoding="utf-8")

task = ROOT / "tasks/issue-63-order-submission-orchestration.md"
replace_once(task, "- PR:\n", "- PR: #64\n")
replace_once(
    task,
    "- Done: compatibility audit, Issue and branch.\n"
    "- Current: implementation and direct tests.\n"
    "- Next: full CI, final review and merge.\n",
    "- Done: compatibility audit, Issue/branch/PR and implementation design.\n"
    "- Current: single-owner implementation, payload tests and architecture checks.\n"
    "- Next: full CI, final review and merge.\n",
)

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-63-apply.yml"
if workflow.exists():
    workflow.unlink()
