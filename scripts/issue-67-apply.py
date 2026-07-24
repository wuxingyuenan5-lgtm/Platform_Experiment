from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "platform-backend"
APP = BACKEND / "app"
TESTS = BACKEND / "tests"


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise SystemExit(f"expected exactly one match in {path}: {old[:100]!r}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


(APP / "venue_reconciliation_policy.py").write_text(
    '''from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.venue_reconciliation_schemas import DifferenceType


@dataclass(frozen=True)
class DifferenceDraft:
    difference_key: str
    difference_type: DifferenceType
    entity_type: str
    local_reference: str | None
    external_reference: str | None
    local_value: dict[str, object]
    external_value: dict[str, object]


_ORDER_UPDATE_STATUSES = {
    "accepted": "acknowledged",
    "rejected": "rejected",
    "canceled": "canceled",
    "unknown": "result_unknown",
}
_ORDER_EXPECTED_STATUSES = {
    **_ORDER_UPDATE_STATUSES,
    "filled": "filled",
}


def external_order_update_status(status: object) -> str | None:
    return _ORDER_UPDATE_STATUSES.get(str(status))


def expected_order_status(status: object) -> str:
    return _ORDER_EXPECTED_STATUSES.get(str(status), "result_unknown")


def order_difference_draft(
    order_id: str,
    difference_type: DifferenceType,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> DifferenceDraft:
    return DifferenceDraft(
        difference_key=f"order:{order_id}:{difference_type}",
        difference_type=difference_type,
        entity_type="order",
        local_reference=order_id,
        external_reference=None,
        local_value=local_value,
        external_value=external_value,
    )


def order_difference_drafts(
    *,
    order_id: str,
    local_status: object,
    local_fill_quantities: list[object],
    external_order: dict[str, object],
    fills: list[dict[str, object]],
) -> list[DifferenceDraft]:
    drafts: list[DifferenceDraft] = []
    if local_status != expected_order_status(external_order["status"]):
        drafts.append(
            order_difference_draft(
                order_id,
                "status_mismatch",
                {"status": local_status},
                {"status": external_order["status"]},
            )
        )

    external_quantity = sum(
        (Decimal(str(fill["quantity"])) for fill in fills),
        Decimal("0"),
    )
    local_quantity = sum(
        (Decimal(str(quantity)) for quantity in local_fill_quantities),
        Decimal("0"),
    )
    if local_quantity != external_quantity:
        drafts.append(
            order_difference_draft(
                order_id,
                "quantity_mismatch",
                {"filledQuantity": format(local_quantity, "f")},
                {"filledQuantity": format(external_quantity, "f")},
            )
        )
    return drafts


def position_difference_drafts(
    *,
    account_id: str,
    local: dict[str, object] | None,
    external: dict[str, object],
    fact_id: str,
) -> list[DifferenceDraft]:
    instrument_id = str(external["instrumentId"])
    external_reference = str(external["externalPositionId"])
    if local is None:
        return [
            DifferenceDraft(
                difference_key=f"position:{instrument_id}:missing_local",
                difference_type="missing_local",
                entity_type="position",
                local_reference=None,
                external_reference=external_reference,
                local_value={},
                external_value=external,
            )
        ]
    if Decimal(str(local["net_quantity"])) != Decimal(str(external["netQuantity"])):
        return [
            DifferenceDraft(
                difference_key=f"position:{instrument_id}:quantity_mismatch",
                difference_type="quantity_mismatch",
                entity_type="position",
                local_reference=f"{account_id}:{instrument_id}",
                external_reference=external_reference,
                local_value={"netQuantity": local["net_quantity"]},
                external_value={"netQuantity": external["netQuantity"], "factId": fact_id},
            )
        ]
    return []


def balance_difference_drafts(
    *,
    account_id: str,
    local: dict[str, object] | None,
    external: dict[str, object],
) -> list[DifferenceDraft]:
    currency = str(external["currency"])
    external_reference = str(external["externalBalanceId"])
    if local is None:
        return [
            DifferenceDraft(
                difference_key=f"balance:{currency}:missing_local",
                difference_type="missing_local",
                entity_type="balance",
                local_reference=account_id,
                external_reference=external_reference,
                local_value={},
                external_value=external,
            )
        ]
    if local["currency"] != external["currency"]:
        return [
            DifferenceDraft(
                difference_key=f"balance:{currency}:currency_mismatch",
                difference_type="currency_mismatch",
                entity_type="balance",
                local_reference=account_id,
                external_reference=external_reference,
                local_value={"currency": local["currency"]},
                external_value={"currency": external["currency"]},
            )
        ]
    if Decimal(str(local["equity"])) != Decimal(str(external["equity"])):
        return [
            DifferenceDraft(
                difference_key=f"balance:{currency}:quantity_mismatch",
                difference_type="quantity_mismatch",
                entity_type="balance",
                local_reference=account_id,
                external_reference=external_reference,
                local_value={"equity": local["equity"]},
                external_value={"equity": external["equity"]},
            )
        ]
    return []


__all__ = [
    "DifferenceDraft",
    "balance_difference_drafts",
    "expected_order_status",
    "external_order_update_status",
    "order_difference_draft",
    "order_difference_drafts",
    "position_difference_drafts",
]
''',
    encoding="utf-8",
)

venue = APP / "venue_reconciliation.py"
replace_once(venue, "from decimal import Decimal\n", "")
replace_once(
    venue,
    '''from app.venue_reconciliation_schemas import (
    DifferenceStatus,
    DifferenceType,
    OrderVenueReconciliationResponse,
    ReconciliationDifferenceResponse,
    ResolveDifferenceRequest,
    VenueReconciliationRunRequest,
    VenueReconciliationRunResponse,
)
''',
    '''from app.venue_reconciliation_policy import (
    DifferenceDraft,
    balance_difference_drafts,
    external_order_update_status,
    order_difference_draft,
    order_difference_drafts,
    position_difference_drafts,
)
from app.venue_reconciliation_schemas import (
    DifferenceStatus,
    DifferenceType,
    OrderVenueReconciliationResponse,
    ReconciliationDifferenceResponse,
    ResolveDifferenceRequest,
    VenueReconciliationRunRequest,
    VenueReconciliationRunResponse,
)
''',
)
replace_once(
    venue,
    '''def update_order_from_external(row, external_order: dict[str, object]) -> None:
    mapping = {
        "accepted": "acknowledged",
        "rejected": "rejected",
        "canceled": "canceled",
        "unknown": "result_unknown",
    }
    local_status = mapping.get(str(external_order["status"]))
    if local_status is None:
        return
''',
    '''def update_order_from_external(row, external_order: dict[str, object]) -> None:
    local_status = external_order_update_status(external_order["status"])
    if local_status is None:
        return
''',
)
replace_once(
    venue,
    '''def compare_order(
    order_id: str,
    local_row,
    external_order: dict[str, object],
    fills: list[dict[str, object]],
) -> list[str]:
    difference_ids: list[str] = []
    expected_status = {
        "accepted": "acknowledged",
        "filled": "filled",
        "rejected": "rejected",
        "canceled": "canceled",
        "unknown": "result_unknown",
    }.get(str(external_order["status"]), "result_unknown")
    if local_row["status"] != expected_status:
        difference_ids.append(
            standalone_order_difference(
                order_id,
                "status_mismatch",
                {"status": local_row["status"]},
                {"status": external_order["status"]},
            )
        )
    external_quantity = sum(Decimal(str(fill["quantity"])) for fill in fills)
    with connection() as db:
        local_fill_rows = db.execute(
            "SELECT quantity FROM fills WHERE order_id = ?",
            (order_id,),
        ).fetchall()
    local_quantity = sum(
        (Decimal(row["quantity"]) for row in local_fill_rows),
        Decimal("0"),
    )
    if local_quantity != external_quantity:
        difference_ids.append(
            standalone_order_difference(
                order_id,
                "quantity_mismatch",
                {"filledQuantity": format(local_quantity, "f")},
                {"filledQuantity": format(external_quantity, "f")},
            )
        )
    return difference_ids
''',
    '''def compare_order(
    order_id: str,
    local_row,
    external_order: dict[str, object],
    fills: list[dict[str, object]],
) -> list[str]:
    with connection() as db:
        local_fill_rows = db.execute(
            "SELECT quantity FROM fills WHERE order_id = ?",
            (order_id,),
        ).fetchall()
    drafts = order_difference_drafts(
        order_id=order_id,
        local_status=local_row["status"],
        local_fill_quantities=[row["quantity"] for row in local_fill_rows],
        external_order=external_order,
        fills=fills,
    )
    return [persist_standalone_order_difference(order_id, draft) for draft in drafts]
''',
)
replace_once(
    venue,
    '''def standalone_order_difference(
    order_id: str,
    difference_type: DifferenceType,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    ensure_schema()
    run_id = f"order-reconcile:{order_id}"
    at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            )
            SELECT ?, ?, ?, tc.strategy_instance_id, o.account_id, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            FROM orders o JOIN trade_commands tc ON tc.id = o.command_id
            WHERE o.id = ?
            """,
            (
                run_id,
                run_id,
                canonical_hash({"orderId": order_id}),
                "order",
                "runtime",
                "completed_with_differences",
                1,
                0,
                0,
                0,
                0,
                1,
                at,
                at,
                order_id,
            ),
        )
    return create_difference(
        run_id,
        f"order:{order_id}:{difference_type}",
        difference_type,
        "order",
        order_id,
        None,
        local_value,
        external_value,
    )
''',
    '''def standalone_order_difference(
    order_id: str,
    difference_type: DifferenceType,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    return persist_standalone_order_difference(
        order_id,
        order_difference_draft(order_id, difference_type, local_value, external_value),
    )


def persist_standalone_order_difference(order_id: str, draft: DifferenceDraft) -> str:
    ensure_schema()
    run_id = f"order-reconcile:{order_id}"
    at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            )
            SELECT ?, ?, ?, tc.strategy_instance_id, o.account_id, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            FROM orders o JOIN trade_commands tc ON tc.id = o.command_id
            WHERE o.id = ?
            """,
            (
                run_id,
                run_id,
                canonical_hash({"orderId": order_id}),
                "order",
                "runtime",
                "completed_with_differences",
                1,
                0,
                0,
                0,
                0,
                1,
                at,
                at,
                order_id,
            ),
        )
    return persist_difference_draft(run_id, draft)
''',
)
replace_once(
    venue,
    '''def compare_position(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
    fact_id: str,
) -> list[str]:
    with connection() as db:
        local = db.execute(
            """
            SELECT net_quantity, average_price
            FROM formal_positions
            WHERE strategy_instance_id = ? AND account_id = ? AND instrument_id = ?
            """,
            (
                request.strategy_instance_id,
                request.account_id,
                external["instrumentId"],
            ),
        ).fetchone()
        if local is None:
            local = db.execute(
                """
                SELECT net_quantity, average_price
                FROM positions
                WHERE account_id = ? AND instrument_id = ?
                """,
                (request.account_id, external["instrumentId"]),
            ).fetchone()
    if local is None:
        return [
            create_difference(
                run_id,
                f"position:{external['instrumentId']}:missing_local",
                "missing_local",
                "position",
                None,
                str(external["externalPositionId"]),
                {},
                external,
            )
        ]
    if Decimal(local["net_quantity"]) != Decimal(str(external["netQuantity"])):
        return [
            create_difference(
                run_id,
                f"position:{external['instrumentId']}:quantity_mismatch",
                "quantity_mismatch",
                "position",
                f"{request.account_id}:{external['instrumentId']}",
                str(external["externalPositionId"]),
                {"netQuantity": local["net_quantity"]},
                {"netQuantity": external["netQuantity"], "factId": fact_id},
            )
        ]
    return []
''',
    '''def compare_position(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
    fact_id: str,
) -> list[str]:
    with connection() as db:
        local_row = db.execute(
            """
            SELECT net_quantity, average_price
            FROM formal_positions
            WHERE strategy_instance_id = ? AND account_id = ? AND instrument_id = ?
            """,
            (
                request.strategy_instance_id,
                request.account_id,
                external["instrumentId"],
            ),
        ).fetchone()
        if local_row is None:
            local_row = db.execute(
                """
                SELECT net_quantity, average_price
                FROM positions
                WHERE account_id = ? AND instrument_id = ?
                """,
                (request.account_id, external["instrumentId"]),
            ).fetchone()
    local = dict(local_row) if local_row is not None else None
    drafts = position_difference_drafts(
        account_id=request.account_id,
        local=local,
        external=external,
        fact_id=fact_id,
    )
    return [persist_difference_draft(run_id, draft) for draft in drafts]
''',
)
replace_once(
    venue,
    '''def compare_balance(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
) -> list[str]:
    with connection() as db:
        local = db.execute(
            """
            SELECT equity, available_balance, currency
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC, created_at DESC
            LIMIT 1
            """,
            (request.account_id,),
        ).fetchone()
    if local is None:
        return [
            create_difference(
                run_id,
                f"balance:{external['currency']}:missing_local",
                "missing_local",
                "balance",
                request.account_id,
                str(external["externalBalanceId"]),
                {},
                external,
            )
        ]
    if local["currency"] != external["currency"]:
        return [
            create_difference(
                run_id,
                f"balance:{external['currency']}:currency_mismatch",
                "currency_mismatch",
                "balance",
                request.account_id,
                str(external["externalBalanceId"]),
                {"currency": local["currency"]},
                {"currency": external["currency"]},
            )
        ]
    if Decimal(local["equity"]) != Decimal(str(external["equity"])):
        return [
            create_difference(
                run_id,
                f"balance:{external['currency']}:quantity_mismatch",
                "quantity_mismatch",
                "balance",
                request.account_id,
                str(external["externalBalanceId"]),
                {"equity": local["equity"]},
                {"equity": external["equity"]},
            )
        ]
    return []
''',
    '''def compare_balance(
    run_id: str,
    request: VenueReconciliationRunRequest,
    external: dict[str, object],
) -> list[str]:
    with connection() as db:
        local_row = db.execute(
            """
            SELECT equity, available_balance, currency
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC, created_at DESC
            LIMIT 1
            """,
            (request.account_id,),
        ).fetchone()
    local = dict(local_row) if local_row is not None else None
    drafts = balance_difference_drafts(
        account_id=request.account_id,
        local=local,
        external=external,
    )
    return [persist_difference_draft(run_id, draft) for draft in drafts]
''',
)
replace_once(
    venue,
    '''def create_difference(
    run_id: str,
''',
    '''def persist_difference_draft(run_id: str, draft: DifferenceDraft) -> str:
    return create_difference(
        run_id,
        draft.difference_key,
        draft.difference_type,
        draft.entity_type,
        draft.local_reference,
        draft.external_reference,
        draft.local_value,
        draft.external_value,
    )


def create_difference(
    run_id: str,
''',
)

(TESTS / "test_venue_reconciliation_policy.py").write_text(
    '''from app.venue_reconciliation_policy import (
    DifferenceDraft,
    balance_difference_drafts,
    expected_order_status,
    external_order_update_status,
    order_difference_drafts,
    position_difference_drafts,
)


def test_external_order_status_mappings_preserve_update_and_comparison_contracts() -> None:
    assert external_order_update_status("accepted") == "acknowledged"
    assert external_order_update_status("rejected") == "rejected"
    assert external_order_update_status("canceled") == "canceled"
    assert external_order_update_status("unknown") == "result_unknown"
    assert external_order_update_status("filled") is None
    assert expected_order_status("filled") == "filled"
    assert expected_order_status("unexpected") == "result_unknown"


def test_order_difference_drafts_preserve_status_then_quantity_order() -> None:
    drafts = order_difference_drafts(
        order_id="order-1",
        local_status="acknowledged",
        local_fill_quantities=["0.1"],
        external_order={"status": "filled"},
        fills=[{"quantity": "0.2000000000000000000000000001"}],
    )

    assert drafts == [
        DifferenceDraft(
            difference_key="order:order-1:status_mismatch",
            difference_type="status_mismatch",
            entity_type="order",
            local_reference="order-1",
            external_reference=None,
            local_value={"status": "acknowledged"},
            external_value={"status": "filled"},
        ),
        DifferenceDraft(
            difference_key="order:order-1:quantity_mismatch",
            difference_type="quantity_mismatch",
            entity_type="order",
            local_reference="order-1",
            external_reference=None,
            local_value={"filledQuantity": "0.1"},
            external_value={"filledQuantity": "0.2000000000000000000000000001"},
        ),
    ]


def test_order_difference_drafts_return_empty_for_exact_decimal_match() -> None:
    assert order_difference_drafts(
        order_id="order-2",
        local_status="filled",
        local_fill_quantities=["0.1", "0.2000000000000000000000000001"],
        external_order={"status": "filled"},
        fills=[
            {"quantity": "0.1"},
            {"quantity": "0.2000000000000000000000000001"},
        ],
    ) == []


def test_position_difference_drafts_cover_missing_mismatch_and_match() -> None:
    external = {
        "instrumentId": "instrument-1",
        "externalPositionId": "external-position-1",
        "netQuantity": "2.5",
    }
    assert position_difference_drafts(
        account_id="account-1",
        local=None,
        external=external,
        fact_id="fact-1",
    ) == [
        DifferenceDraft(
            difference_key="position:instrument-1:missing_local",
            difference_type="missing_local",
            entity_type="position",
            local_reference=None,
            external_reference="external-position-1",
            local_value={},
            external_value=external,
        )
    ]
    assert position_difference_drafts(
        account_id="account-1",
        local={"net_quantity": "2.4", "average_price": "100"},
        external=external,
        fact_id="fact-1",
    ) == [
        DifferenceDraft(
            difference_key="position:instrument-1:quantity_mismatch",
            difference_type="quantity_mismatch",
            entity_type="position",
            local_reference="account-1:instrument-1",
            external_reference="external-position-1",
            local_value={"netQuantity": "2.4"},
            external_value={"netQuantity": "2.5", "factId": "fact-1"},
        )
    ]
    assert position_difference_drafts(
        account_id="account-1",
        local={"net_quantity": "2.500", "average_price": "100"},
        external=external,
        fact_id="fact-1",
    ) == []


def test_balance_difference_drafts_preserve_precedence_and_values() -> None:
    external = {
        "externalBalanceId": "external-balance-1",
        "currency": "USD",
        "equity": "100.25",
    }
    assert balance_difference_drafts(
        account_id="account-1",
        local=None,
        external=external,
    ) == [
        DifferenceDraft(
            difference_key="balance:USD:missing_local",
            difference_type="missing_local",
            entity_type="balance",
            local_reference="account-1",
            external_reference="external-balance-1",
            local_value={},
            external_value=external,
        )
    ]
    assert balance_difference_drafts(
        account_id="account-1",
        local={"currency": "EUR", "equity": "99"},
        external=external,
    ) == [
        DifferenceDraft(
            difference_key="balance:USD:currency_mismatch",
            difference_type="currency_mismatch",
            entity_type="balance",
            local_reference="account-1",
            external_reference="external-balance-1",
            local_value={"currency": "EUR"},
            external_value={"currency": "USD"},
        )
    ]
    assert balance_difference_drafts(
        account_id="account-1",
        local={"currency": "USD", "equity": "100.2"},
        external=external,
    ) == [
        DifferenceDraft(
            difference_key="balance:USD:quantity_mismatch",
            difference_type="quantity_mismatch",
            entity_type="balance",
            local_reference="account-1",
            external_reference="external-balance-1",
            local_value={"equity": "100.2"},
            external_value={"equity": "100.25"},
        )
    ]
    assert balance_difference_drafts(
        account_id="account-1",
        local={"currency": "USD", "equity": "100.250"},
        external=external,
    ) == []
''',
    encoding="utf-8",
)

(TESTS / "test_architecture_venue_reconciliation_policy.py").write_text(
    '''import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "venue_reconciliation_policy.py"
ORCHESTRATION_PATH = APP_ROOT / "venue_reconciliation.py"
POLICY_FUNCTIONS = {
    "balance_difference_drafts",
    "expected_order_status",
    "external_order_update_status",
    "order_difference_draft",
    "order_difference_drafts",
    "position_difference_drafts",
}


def function_names(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_difference_policy_is_the_only_decision_function_owner() -> None:
    owner_functions = function_names(OWNER_PATH)
    orchestration_functions = function_names(ORCHESTRATION_PATH)

    assert POLICY_FUNCTIONS <= owner_functions
    assert not (POLICY_FUNCTIONS & orchestration_functions)


def test_orchestration_imports_policy_and_keeps_external_effects() -> None:
    source = ORCHESTRATION_PATH.read_text(encoding="utf-8")

    assert "from app.venue_reconciliation_policy import (" in source
    assert "persist_difference_draft" in source
    assert "connection()" in source
    assert "httpx.get(" in source
    assert "INSERT OR IGNORE INTO reconciliation_differences" in source


def test_policy_has_no_framework_database_or_network_dependency() -> None:
    imports = imported_modules(OWNER_PATH)
    source = OWNER_PATH.read_text(encoding="utf-8")

    assert imports <= {
        "__future__",
        "dataclasses",
        "decimal",
        "app.venue_reconciliation_schemas",
    }
    assert "fastapi" not in source
    assert "httpx" not in source
    assert "connection" not in source
    assert "SELECT " not in source
    assert "INSERT " not in source
    assert "UPDATE " not in source
''',
    encoding="utf-8",
)

pyproject = BACKEND / "pyproject.toml"
replace_once(
    pyproject,
    '  "app/venue_reconciliation_schemas.py",\n',
    '  "app/venue_reconciliation_policy.py",\n  "app/venue_reconciliation_schemas.py",\n',
)

ownership = ROOT / "docs/architecture/OWNERSHIP.md"
replace_once(
    ownership,
    "| Venue Reconciliation public DTOs | `platform-backend/app/venue_reconciliation_schemas.py` | Reconciliation run, difference-resolution and order-reconciliation request/response models plus public status types | SQL, Runtime queries, comparison or route orchestration |\n"
    "| Venue Reconciliation orchestration | `platform-backend/app/venue_reconciliation.py` | Compatibility exports, Runtime queries, FinancialFact import, comparison, difference persistence, audit and routes pending staged extraction | Duplicate public DTO definitions |\n",
    "| Venue Reconciliation public DTOs | `platform-backend/app/venue_reconciliation_schemas.py` | Reconciliation run, difference-resolution and order-reconciliation request/response models plus public status types | SQL, Runtime queries, comparison or route orchestration |\n"
    "| Venue Reconciliation difference policy | `platform-backend/app/venue_reconciliation_policy.py` | Pure external-status mapping and immutable Order/Position/Balance difference-draft decisions | SQL, Runtime queries, persistence, audit or routes |\n"
    "| Venue Reconciliation orchestration | `platform-backend/app/venue_reconciliation.py` | Compatibility exports, Runtime/SQLite data retrieval, FinancialFact import, difference persistence, audit and routes pending staged extraction | Duplicate DTO or difference-policy definitions |\n",
)

architecture = ROOT / "docs/architecture/README.md"
replace_once(
    architecture,
    "- `platform-backend/app/venue_reconciliation_schemas.py` 是 Venue Reconciliation 公开 DTO 和差异状态类型的唯一 Owner；原模块只做兼容导出。\n",
    "- `platform-backend/app/venue_reconciliation_schemas.py` 是 Venue Reconciliation 公开 DTO 和差异状态类型的唯一 Owner；原模块只做兼容导出。\n"
    "- `platform-backend/app/venue_reconciliation_policy.py` 是外部订单状态映射与 Order/Position/Balance 差异草稿判定的纯 Policy Owner；它不得读取数据库、调用 Runtime 或写入 Difference。\n",
)

checker = ROOT / "scripts/check-documentation-consistency.py"
replace_once(
    checker,
    '    "Venue Reconciliation public DTOs": "platform-backend/app/venue_reconciliation_schemas.py",\n',
    '    "Venue Reconciliation public DTOs": "platform-backend/app/venue_reconciliation_schemas.py",\n'
    '    "Venue Reconciliation difference policy": "platform-backend/app/venue_reconciliation_policy.py",\n',
)

debt = ROOT / "docs/engineering/TECHNICAL_DEBT.md"
replace_once(
    debt,
    "shared Position Math, Venue Reconciliation DTOs, SQLite Connection/Bootstrap/Seeds",
    "shared Position Math, Venue Reconciliation DTOs/Difference Policy, SQLite Connection/Bootstrap/Seeds",
)

state = ROOT / "docs/codex/current-state.md"
replace_once(
    state,
    "No engineering code workstream is active by default after PR #66 merges.",
    "Issue #67 / Draft PR #68 is the only active engineering workstream: Venue Reconciliation Difference Policy extraction.",
)

changelog = ROOT / "CHANGELOG.md"
entry = '''### Venue Reconciliation Difference Policy ownership — Issue #67 / PR #68

- Added `platform-backend/app/venue_reconciliation_policy.py` as the pure status-mapping and Order/Position/Balance difference-draft owner.
- Kept all SQLite reads, Runtime calls, FinancialFact imports, Difference persistence, audit and routes in the existing orchestration module.
- Added exact Golden drafts for status/quantity, missing/mismatched positions and missing/currency/equity balance cases.
- Added sole-owner, dependency-purity, Ownership and progressive Pyright checks.
- Preserved every Difference key/type/value/order, SQL statement, transaction, API and both Live Write defaults.

'''
marker = "## Unreleased\n\n"
content = changelog.read_text(encoding="utf-8")
if entry not in content:
    if marker not in content:
        raise SystemExit("Changelog Unreleased marker not found")
    changelog.write_text(content.replace(marker, marker + entry, 1), encoding="utf-8")

task = ROOT / "tasks/issue-67-venue-reconciliation-policy.md"
replace_once(task, "- PR:\n", "- PR: #68\n")
replace_once(
    task,
    "- Done: boundary audit, Issue and branch.\n"
    "- Current: implementation and Golden design.\n"
    "- Next: direct verification, full CI and merge.\n",
    "- Done: boundary audit, Issue/branch/PR and pure-policy design.\n"
    "- Current: implementation, exact Golden drafts and architecture checks.\n"
    "- Next: full CI, final review and merge.\n",
)

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-67-apply.yml"
if workflow.exists():
    workflow.unlink()
