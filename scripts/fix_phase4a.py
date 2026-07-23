from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"marker not found in {path}: {old[:100]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


# Persist the complete batch request boundary so idempotent replays can detect
# payload conflicts rather than silently returning an unrelated execution.
replace_once(
    "platform-backend/app/phase4_risk.py",
    """    average_fill_price TEXT,
    contract_multiplier TEXT NOT NULL,
    base_exposure TEXT NOT NULL,
""",
    """    average_fill_price TEXT,
    contract_multiplier TEXT NOT NULL,
    time_in_force TEXT NOT NULL,
    reduce_only INTEGER NOT NULL,
    position_idx INTEGER NOT NULL,
    max_deviation INTEGER,
    allow_partial_fill INTEGER NOT NULL,
    max_slippage_bps TEXT,
    base_exposure TEXT NOT NULL,
""",
)
replace_once(
    "platform-backend/app/phase4_risk.py",
    """    existing = find_batch(request.idempotency_key)
    if existing:
        return get_execution_batch(existing)
""",
    """    existing = find_batch(request.idempotency_key)
    if existing:
        assert_batch_request_matches(existing, request)
        return get_execution_batch(existing)
""",
)
replace_once(
    "platform-backend/app/phase4_risk.py",
    """                INSERT INTO execution_batch_leg_metrics (
                    batch_id, role, filled_quantity, average_fill_price,
                    contract_multiplier, base_exposure, notional,
                    repair_order_id, repair_status
                ) VALUES (?, ?, NULL, NULL, ?, '0', '0', NULL, NULL)
                """,
                (batch_id, leg.role, decimal_text(contract_multiplier)),
""",
    """                INSERT INTO execution_batch_leg_metrics (
                    batch_id, role, filled_quantity, average_fill_price,
                    contract_multiplier, time_in_force, reduce_only,
                    position_idx, max_deviation, allow_partial_fill,
                    max_slippage_bps, base_exposure, notional,
                    repair_order_id, repair_status
                ) VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, '0', '0', NULL, NULL)
                """,
                (
                    batch_id,
                    leg.role,
                    decimal_text(contract_multiplier),
                    leg.time_in_force,
                    int(leg.reduce_only),
                    leg.position_idx,
                    leg.max_deviation,
                    int(request.allow_partial_fill and leg.allow_partial_fill),
                    decimal_text(leg.max_slippage_bps)
                    if leg.max_slippage_bps is not None
                    else None,
                ),
""",
)
replace_once(
    "platform-backend/app/phase4_risk.py",
    """def find_batch(key: str) -> str | None:
""",
    """def assert_batch_request_matches(
    batch_id: str,
    request: CreateExecutionBatchRequest,
) -> None:
    with connection() as db:
        batch = db.execute(
            """
            SELECT strategy_instance_id, account_id, strategy_key, direction
            FROM execution_batches WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        risk = db.execute(
            "SELECT * FROM execution_batch_risk_profiles WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()
        legs = db.execute(
            """
            SELECT l.role, l.account_id, l.instrument_id, l.symbol, l.side,
                   l.order_type, l.quantity, l.price,
                   m.time_in_force, m.reduce_only, m.position_idx,
                   m.max_deviation, m.allow_partial_fill, m.max_slippage_bps
            FROM execution_batch_legs l
            JOIN execution_batch_leg_metrics m
              ON m.batch_id = l.batch_id AND m.role = l.role
            WHERE l.batch_id = ?
            """,
            (batch_id,),
        ).fetchall()

    default_account_id = request.account_id or request.legs[0].account_id
    if batch is None or risk is None:
        raise HTTPException(status_code=409, detail="Existing batch is incomplete")
    batch_matches = (
        batch["strategy_instance_id"] == request.strategy_instance_id
        and batch["account_id"] == default_account_id
        and batch["strategy_key"] == request.strategy_key
        and batch["direction"] == request.direction
        and risk["max_leg_delay_ms"] == request.max_leg_delay_ms
        and Decimal(risk["max_residual_notional"]) == request.max_residual_notional
        and bool(risk["allow_partial_fill"]) == request.allow_partial_fill
        and bool(risk["emergency_flatten"]) == request.emergency_flatten
        and risk["disposition_policy"] == request.disposition_policy
    )
    stored = {row["role"]: row for row in legs}
    if not batch_matches or set(stored) != {leg.role for leg in request.legs}:
        raise_batch_conflict()

    for leg in request.legs:
        row = stored[leg.role]
        account_id = leg.account_id or default_account_id
        stored_price = Decimal(row["price"]) if row["price"] is not None else None
        stored_slippage = (
            Decimal(row["max_slippage_bps"])
            if row["max_slippage_bps"] is not None
            else None
        )
        leg_matches = (
            row["account_id"] == account_id
            and row["instrument_id"] == leg.instrument_id
            and row["symbol"] == leg.symbol
            and row["side"] == leg.side
            and row["order_type"] == leg.order_type
            and Decimal(row["quantity"]) == leg.quantity
            and stored_price == leg.price
            and row["time_in_force"] == leg.time_in_force
            and bool(row["reduce_only"]) == leg.reduce_only
            and row["position_idx"] == leg.position_idx
            and row["max_deviation"] == leg.max_deviation
            and bool(row["allow_partial_fill"])
            == (request.allow_partial_fill and leg.allow_partial_fill)
            and stored_slippage == leg.max_slippage_bps
        )
        if not leg_matches:
            raise_batch_conflict()


def raise_batch_conflict() -> None:
    raise HTTPException(
        status_code=409,
        detail="Idempotency key is already used by a different execution batch payload",
    )


def find_batch(key: str) -> str | None:
""",
)

# Phase 4 replaces the ambiguous manual state with an explicit unresolved-risk
# state. Existing observability tests continue to require manual intervention.
for path in (
    "platform-backend/tests/test_execution_batches.py",
    "platform-backend/tests/test_ops_observability.py",
):
    file = Path(path)
    file.write_text(
        file.read_text(encoding="utf-8").replace(
            'assert batch["status"] == "manual_intervention"',
            'assert batch["status"] == "risk_unresolved"',
        ),
        encoding="utf-8",
    )

# The legacy testnet execution test must explicitly opt into the independent
# Demo gate. The monkeypatch restores the default after the test.
replace_once(
    "platform-backend/tests/test_execution_batches_v1.py",
    """    get_settings().database_path = str(tmp_path / "batch-idempotency.db")
    monkeypatch.setattr(
""",
    """    get_settings().database_path = str(tmp_path / "batch-idempotency.db")
    monkeypatch.setattr(get_settings(), "demo_trading_enabled", True)
    monkeypatch.setattr(
""",
)

# Keep the new goldens independent of a locally running Runtime and avoid
# assigning a nonexistent rejected order through a foreign key.
path = "platform-backend/tests/test_phase4_risk.py"
text = Path(path).read_text(encoding="utf-8")
text = text.replace(
    "from pathlib import Path\n",
    "from pathlib import Path\nfrom uuid import uuid4\n",
    1,
)
text = text.replace(
    'STRATEGY = "strategy_funding_arbitrage_instance_default"\n',
    '''STRATEGY = "strategy_funding_arbitrage_instance_default"


def filled_runtime_response(command: dict[str, object]) -> object:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_acknowledged",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "occurred_at": "2026-07-23T00:00:00+00:00",
                },
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_filled",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": command.get("price") or "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-07-23T00:00:01+00:00",
                },
            ]

    return FakeResponse()
''',
    1,
)
text = text.replace(
    "def test_phase4_batch_is_hedged_and_idempotent(tmp_path: Path) -> None:\n",
    """def test_phase4_batch_is_hedged_and_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
""",
    1,
)
text = text.replace(
    '    get_settings().database_path = str(tmp_path / "hedged.db")\n',
    '''    get_settings().database_path = str(tmp_path / "hedged.db")
    monkeypatch.setattr(
        "app.trading.httpx.post",
        lambda *args, **kwargs: filled_runtime_response(kwargs["json"]),
    )
''',
    1,
)
text = text.replace(
    '            elif len(calls) == 2:\n                status, order_id = "rejected", "o2"\n',
    '            elif len(calls) == 2:\n                status, order_id = "rejected", None\n',
    1,
)
Path(path).write_text(text, encoding="utf-8")
