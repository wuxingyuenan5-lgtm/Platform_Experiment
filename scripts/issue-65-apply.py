from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "platform-backend"
APP = BACKEND / "app"
TESTS = BACKEND / "tests"
sys.path.insert(0, str(BACKEND))

from app import venue_reconciliation as legacy  # noqa: E402
from app.main import app  # noqa: E402

MODEL_NAMES = [
    "VenueReconciliationRunRequest",
    "VenueReconciliationRunResponse",
    "ReconciliationDifferenceResponse",
    "ResolveDifferenceRequest",
    "OrderVenueReconciliationResponse",
]


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


model_schema_hashes = {
    name: canonical_hash(getattr(legacy, name).model_json_schema()) for name in MODEL_NAMES
}
openapi = app.openapi()
reconciliation_openapi = {
    "schemas": {
        name: openapi["components"]["schemas"][name]
        for name in MODEL_NAMES
    },
    "paths": {
        path: value
        for path, value in openapi["paths"].items()
        if "reconciliation" in path
    },
}
openapi_hash = canonical_hash(reconciliation_openapi)


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise SystemExit(f"expected exactly one match in {path}: {old[:100]!r}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


(APP / "venue_reconciliation_schemas.py").write_text(
    '''from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DifferenceType = Literal[
    "missing_local",
    "missing_external",
    "quantity_mismatch",
    "price_mismatch",
    "currency_mismatch",
    "status_mismatch",
]
DifferenceStatus = Literal["open", "resolved", "accepted"]


class VenueReconciliationRunRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    actor: str = Field(min_length=1, max_length=128)


class VenueReconciliationRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    idempotency_key: str = Field(alias="idempotencyKey")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    run_type: str = Field(alias="runType")
    source: str
    status: str
    order_count: int = Field(alias="orderCount")
    fill_count: int = Field(alias="fillCount")
    position_count: int = Field(alias="positionCount")
    balance_count: int = Field(alias="balanceCount")
    fact_count: int = Field(alias="factCount")
    difference_count: int = Field(alias="differenceCount")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class ReconciliationDifferenceResponse(BaseModel):
    difference_id: str = Field(alias="differenceId")
    run_id: str = Field(alias="runId")
    difference_key: str = Field(alias="differenceKey")
    difference_type: DifferenceType = Field(alias="differenceType")
    entity_type: str = Field(alias="entityType")
    local_reference: str | None = Field(default=None, alias="localReference")
    external_reference: str | None = Field(default=None, alias="externalReference")
    local_value: dict[str, object] = Field(alias="localValue")
    external_value: dict[str, object] = Field(alias="externalValue")
    status: DifferenceStatus
    resolution_actor: str | None = Field(default=None, alias="resolutionActor")
    resolution_reason: str | None = Field(default=None, alias="resolutionReason")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    created_at: datetime = Field(alias="createdAt")


class ResolveDifferenceRequest(BaseModel):
    status: Literal["resolved", "accepted"]
    actor: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class OrderVenueReconciliationResponse(BaseModel):
    order_id: str = Field(alias="orderId")
    command_id: str = Field(alias="commandId")
    source: str
    external_order_id: str | None = Field(default=None, alias="externalOrderId")
    status_before: str = Field(alias="statusBefore")
    status_after: str = Field(alias="statusAfter")
    recovered: bool
    imported_fact_ids: list[str] = Field(alias="importedFactIds")
    difference_ids: list[str] = Field(alias="differenceIds")
    reconciled_at: datetime = Field(alias="reconciledAt")


__all__ = [
    "DifferenceStatus",
    "DifferenceType",
    "OrderVenueReconciliationResponse",
    "ReconciliationDifferenceResponse",
    "ResolveDifferenceRequest",
    "VenueReconciliationRunRequest",
    "VenueReconciliationRunResponse",
]
''',
    encoding="utf-8",
)

venue_path = APP / "venue_reconciliation.py"
replace_once(venue_path, "from typing import Literal\n", "")
replace_once(venue_path, "from pydantic import BaseModel, Field\n\n", "")
replace_once(
    venue_path,
    '''DifferenceType = Literal[
    "missing_local",
    "missing_external",
    "quantity_mismatch",
    "price_mismatch",
    "currency_mismatch",
    "status_mismatch",
]
DifferenceStatus = Literal["open", "resolved", "accepted"]

''',
    "",
)
replace_once(
    venue_path,
    '''class VenueReconciliationRunRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    actor: str = Field(min_length=1, max_length=128)


class VenueReconciliationRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    idempotency_key: str = Field(alias="idempotencyKey")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    run_type: str = Field(alias="runType")
    source: str
    status: str
    order_count: int = Field(alias="orderCount")
    fill_count: int = Field(alias="fillCount")
    position_count: int = Field(alias="positionCount")
    balance_count: int = Field(alias="balanceCount")
    fact_count: int = Field(alias="factCount")
    difference_count: int = Field(alias="differenceCount")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class ReconciliationDifferenceResponse(BaseModel):
    difference_id: str = Field(alias="differenceId")
    run_id: str = Field(alias="runId")
    difference_key: str = Field(alias="differenceKey")
    difference_type: DifferenceType = Field(alias="differenceType")
    entity_type: str = Field(alias="entityType")
    local_reference: str | None = Field(default=None, alias="localReference")
    external_reference: str | None = Field(default=None, alias="externalReference")
    local_value: dict[str, object] = Field(alias="localValue")
    external_value: dict[str, object] = Field(alias="externalValue")
    status: DifferenceStatus
    resolution_actor: str | None = Field(default=None, alias="resolutionActor")
    resolution_reason: str | None = Field(default=None, alias="resolutionReason")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    created_at: datetime = Field(alias="createdAt")


class ResolveDifferenceRequest(BaseModel):
    status: Literal["resolved", "accepted"]
    actor: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class OrderVenueReconciliationResponse(BaseModel):
    order_id: str = Field(alias="orderId")
    command_id: str = Field(alias="commandId")
    source: str
    external_order_id: str | None = Field(default=None, alias="externalOrderId")
    status_before: str = Field(alias="statusBefore")
    status_after: str = Field(alias="statusAfter")
    recovered: bool
    imported_fact_ids: list[str] = Field(alias="importedFactIds")
    difference_ids: list[str] = Field(alias="differenceIds")
    reconciled_at: datetime = Field(alias="reconciledAt")


''',
    "",
)
replace_once(
    venue_path,
    '''from app.trading import (
    apply_execution_events,
    get_order_response,
    get_order_row,
    reconcile_order,
    request_from_order_row,
    synchronize_trade_command_status,
)

''',
    '''from app.trading import (
    apply_execution_events,
    get_order_response,
    get_order_row,
    reconcile_order,
    request_from_order_row,
    synchronize_trade_command_status,
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

__all__ = [
    "DifferenceStatus",
    "DifferenceType",
    "OrderVenueReconciliationResponse",
    "ReconciliationDifferenceResponse",
    "ResolveDifferenceRequest",
    "VenueReconciliationRunRequest",
    "VenueReconciliationRunResponse",
]

''',
)

schema_constants = json.dumps(model_schema_hashes, indent=4, sort_keys=True)
(TESTS / "test_venue_reconciliation_schemas.py").write_text(
    f'''import hashlib
import json

from app import venue_reconciliation as compatibility
from app import venue_reconciliation_schemas as schemas
from app.main import app

MODEL_NAMES = {MODEL_NAMES!r}
EXPECTED_MODEL_SCHEMA_HASHES = {schema_constants}
EXPECTED_RECONCILIATION_OPENAPI_HASH = "{openapi_hash}"


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_compatibility_exports_are_identical_schema_objects() -> None:
    for name in MODEL_NAMES:
        assert getattr(compatibility, name) is getattr(schemas, name)
    assert compatibility.DifferenceType is schemas.DifferenceType
    assert compatibility.DifferenceStatus is schemas.DifferenceStatus


def test_model_json_schemas_match_pre_extraction_goldens() -> None:
    actual = {{
        name: canonical_hash(getattr(schemas, name).model_json_schema())
        for name in MODEL_NAMES
    }}

    assert actual == EXPECTED_MODEL_SCHEMA_HASHES


def test_reconciliation_openapi_fragment_matches_pre_extraction_golden() -> None:
    openapi = app.openapi()
    fragment = {{
        "schemas": {{
            name: openapi["components"]["schemas"][name]
            for name in MODEL_NAMES
        }},
        "paths": {{
            path: value
            for path, value in openapi["paths"].items()
            if "reconciliation" in path
        }},
    }}

    assert canonical_hash(fragment) == EXPECTED_RECONCILIATION_OPENAPI_HASH
''',
    encoding="utf-8",
)

(TESTS / "test_architecture_venue_reconciliation_schemas.py").write_text(
    '''import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "venue_reconciliation_schemas.py"
COMPATIBILITY_PATH = APP_ROOT / "venue_reconciliation.py"
MODEL_NAMES = {
    "VenueReconciliationRunRequest",
    "VenueReconciliationRunResponse",
    "ReconciliationDifferenceResponse",
    "ResolveDifferenceRequest",
    "OrderVenueReconciliationResponse",
}


def class_names(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.ClassDef)
    }


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_schema_owner_is_the_only_model_definition_location() -> None:
    owners = {
        path.name: class_names(path) & MODEL_NAMES
        for path in APP_ROOT.glob("*.py")
        if class_names(path) & MODEL_NAMES
    }

    assert owners == {"venue_reconciliation_schemas.py": MODEL_NAMES}


def test_compatibility_module_imports_the_schema_owner() -> None:
    source = COMPATIBILITY_PATH.read_text(encoding="utf-8")

    assert "from app.venue_reconciliation_schemas import (" in source
    assert "class VenueReconciliationRunRequest" not in source
    assert "DifferenceType = Literal[" not in source


def test_schema_owner_has_no_framework_or_persistence_dependency() -> None:
    imports = imported_modules(OWNER_PATH)

    assert imports <= {"__future__", "datetime", "typing", "pydantic"}
''',
    encoding="utf-8",
)

pyproject = BACKEND / "pyproject.toml"
replace_once(
    pyproject,
    '  "app/trade_command_execution.py",\n',
    '  "app/trade_command_execution.py",\n  "app/venue_reconciliation_schemas.py",\n',
)

ownership = ROOT / "docs/architecture/OWNERSHIP.md"
replace_once(
    ownership,
    "| Platform order submission orchestration | `platform-backend/app/trade_command_execution.py` | Single local Order creation, Safety enforcement, legacy/V1 Runtime dispatch, unknown-result handling and Event handoff | Event projection, reconciliation or formal accounting |\n",
    "| Platform order submission orchestration | `platform-backend/app/trade_command_execution.py` | Single local Order creation, Safety enforcement, legacy/V1 Runtime dispatch, unknown-result handling and Event handoff | Event projection, reconciliation or formal accounting |\n"
    "| Venue Reconciliation public DTOs | `platform-backend/app/venue_reconciliation_schemas.py` | Reconciliation run, difference-resolution and order-reconciliation request/response models plus public status types | SQL, Runtime queries, comparison or route orchestration |\n"
    "| Venue Reconciliation orchestration | `platform-backend/app/venue_reconciliation.py` | Compatibility exports, Runtime queries, FinancialFact import, comparison, difference persistence, audit and routes pending staged extraction | Duplicate public DTO definitions |\n",
)

architecture = ROOT / "docs/architecture/README.md"
replace_once(
    architecture,
    "- `platform-backend/app/trading.py::submit_order` 只保留 deprecated 兼容入口；legacy raw payload 与 TradeCommand V1 payload 由 Owner 显式区分。\n",
    "- `platform-backend/app/trading.py::submit_order` 只保留 deprecated 兼容入口；legacy raw payload 与 TradeCommand V1 payload 由 Owner 显式区分。\n"
    "- `platform-backend/app/venue_reconciliation_schemas.py` 是 Venue Reconciliation 公开 DTO 和差异状态类型的唯一 Owner；原模块只做兼容导出。\n",
)

checker = ROOT / "scripts/check-documentation-consistency.py"
replace_once(
    checker,
    '    "Platform order submission orchestration": "platform-backend/app/trade_command_execution.py",\n',
    '    "Platform order submission orchestration": "platform-backend/app/trade_command_execution.py",\n'
    '    "Venue Reconciliation public DTOs": "platform-backend/app/venue_reconciliation_schemas.py",\n'
    '    "Venue Reconciliation orchestration": "platform-backend/app/venue_reconciliation.py",\n',
)

debt = ROOT / "docs/engineering/TECHNICAL_DEBT.md"
replace_once(
    debt,
    "- Platform execution DTOs, FinancialFact DTOs/Normalization/Repository/Projection Service, shared Position Math, SQLite Connection/Bootstrap/Seeds, Runtime contracts, schema migrations, schema governance and authoritative order submission are selected;\n",
    "- Platform execution DTOs, FinancialFact DTOs/Normalization/Repository/Projection Service, shared Position Math, Venue Reconciliation DTOs, SQLite Connection/Bootstrap/Seeds, Runtime contracts, schema migrations, schema governance and authoritative order submission are selected;\n",
)

state = ROOT / "docs/codex/current-state.md"
replace_once(
    state,
    "No engineering code workstream is active by default after PR #64 merges.",
    "Issue #65 / Draft PR #66 is the only active engineering workstream: Venue Reconciliation public-schema ownership extraction.",
)

changelog = ROOT / "CHANGELOG.md"
entry = '''### Venue Reconciliation public-schema ownership — Issue #65 / PR #66

- Added `platform-backend/app/venue_reconciliation_schemas.py` as the sole owner of reconciliation public DTOs and status Literal types.
- Preserved exact object identity through the existing `app.venue_reconciliation` imports.
- Added pre-extraction JSON Schema and Reconciliation OpenAPI fragment hashes plus sole-definition/purity checks.
- Added progressive Pyright and canonical Ownership coverage.
- Preserved every route, field, alias, validation, SQL statement, reconciliation identity, transaction, Runtime call and both Live Write defaults.

'''
marker = "## Unreleased\n\n"
content = changelog.read_text(encoding="utf-8")
if entry not in content:
    if marker not in content:
        raise SystemExit("Changelog Unreleased marker not found")
    changelog.write_text(content.replace(marker, marker + entry, 1), encoding="utf-8")

task = ROOT / "tasks/issue-65-venue-reconciliation-schemas.md"
replace_once(task, "- PR:\n", "- PR: #66\n")
replace_once(
    task,
    "- Done: Issue and branch created.\n"
    "- Current: model inventory and extraction design.\n"
    "- Next: implementation, direct verification and full CI.\n",
    "- Done: Issue/branch/PR, model inventory and pre-extraction contract snapshots.\n"
    "- Current: schema extraction, compatibility and architecture tests.\n"
    "- Next: full CI, final review and merge.\n",
)

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-65-apply.yml"
if workflow.exists():
    workflow.unlink()
