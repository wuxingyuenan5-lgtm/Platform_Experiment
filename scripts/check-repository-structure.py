"""Fail CI when repository structure or architectural safety boundaries regress."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "platform-api" / "app"
RUNTIME_APP = ROOT / "execution-runtime" / "app"
TEST_ROOTS = (
    ROOT / "platform-api" / "tests",
    ROOT / "execution-runtime" / "tests",
)
WORKFLOW_ROOT = ROOT / ".github" / "workflows"

FORBIDDEN_BACKEND_IMPORTS = {
    "MetaTrader5",
    "binance",
    "ccxt",
    "ib_insync",
    "pybit",
}
FORBIDDEN_TEST_NAME = re.compile(
    r"^test_.+_(?:backup|copy|final|new|old|temp|tmp)\.py$",
    re.IGNORECASE,
)
FORBIDDEN_WORKFLOW_NAME = re.compile(
    r"(?:^|[-_])(?:capture|debug|fix-once|one-time|once)(?:[-_]|\.)",
    re.IGNORECASE,
)
ALLOWED_COMPOSITION_CALLS = {"add_middleware", "include_router"}
EXECUTION_SCHEMA_NAMES = {
    "BatchLegRequest",
    "BatchLegResponse",
    "CreateExecutionBatchRequest",
    "CreateOrderRequest",
    "CreateStrategyRunRequest",
    "ExecutionBatchResponse",
    "OrderResponse",
    "PnlResponse",
    "PositionResponse",
    "StrategyRunResponse",
    "StrategyV1ReadinessResponse",
}
OPERATIONAL_PROJECTION_WRITE_ANCHORS = {
    "INSERT INTO positions",
    "INSERT INTO pnl_results",
}
FORMAL_PROJECTION_WRITES = {
    "INSERT INTO financial_facts",
    "INSERT INTO formal_positions",
    "UPDATE formal_positions",
    "INSERT INTO formal_pnl_results",
    "UPDATE formal_pnl_results",
}
OPERATIONAL_PROJECTION_READS = {
    "FROM positions",
    "FROM pnl_results",
}
FINANCIAL_REPOSITORY_SQL_ANCHORS = {
    "CREATE TABLE IF NOT EXISTS financial_facts",
    "INSERT INTO financial_facts",
    "INSERT INTO formal_positions",
    "INSERT INTO formal_pnl_results",
    "INSERT INTO formal_strategy_nav_snapshots",
}
FINANCIAL_SERVICE_SQL_PREFIXES = (
    "CREATE TABLE",
    "CREATE INDEX",
    "SELECT ",
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
)
CANONICAL_CONTEXT_FILES = (
    ROOT / "docs" / "codex" / "context-map.md",
    ROOT / "docs" / "codex" / "current-state.md",
    ROOT / "docs" / "codex" / "task-template.md",
    ROOT / "docs" / "architecture" / "SYSTEM_MAP.md",
    ROOT / "docs" / "engineering" / "TECHNICAL_DEBT.md",
)
FORBIDDEN_PARALLEL_CONTEXT_PATHS = (
    ROOT / "docs" / "START-HERE.md",
    ROOT / "docs" / "context",
    ROOT / "tasks" / "TASK_TEMPLATE.md",
)
DDL_OWNER_PATHS = (
    "platform-api/app/database_bootstrap.py",
    "platform-api/app/credential_security.py",
    "platform-api/app/disaster_recovery.py",
    "platform-api/app/eod_reconciliation_repository.py",
    "platform-api/app/execution_risk.py",
    "platform-api/app/financial_fact_repository.py",
    "platform-api/app/live_trading_sessions.py",
    "platform-api/app/live_venue_accounting.py",
    "platform-api/app/production_monitoring.py",
    "platform-api/app/venue_reconciliation_repository.py",
    "execution-runtime/app/journal.py",
    "execution-runtime/app/live_route_store.py",
    "execution-runtime/app/venue_store.py",
)
RUNTIME_CONTRACT_FIELDS = {
    "command": [
        "contract_name",
        "contract_version",
        "payload_version",
        "command_id",
        "platform_order_id",
        "strategy_instance_id",
        "account_id",
        "instrument_id",
        "symbol",
        "side",
        "order_type",
        "execution_policy",
        "quantity",
        "price",
        "reduce_only",
        "position_id",
        "received_at",
    ],
    "event": [
        "contract_name",
        "contract_version",
        "payload_version",
        "event_id",
        "command_id",
        "platform_order_id",
        "event_type",
        "external_order_id",
        "fill_price",
        "fill_quantity",
        "occurred_at",
        "reason",
    ],
}


def parsed_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_top_levels(path: Path) -> set[str]:
    tree = parsed_module(path)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return imports


def string_literals(path: Path) -> list[str]:
    return [
        node.value
        for node in ast.walk(parsed_module(path))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def check_backend_venue_boundary(errors: list[str]) -> None:
    for path in sorted(BACKEND_APP.rglob("*.py")):
        forbidden = imported_top_levels(path) & FORBIDDEN_BACKEND_IMPORTS
        if forbidden:
            relative = path.relative_to(ROOT)
            errors.append(
                f"{relative}: backend imports venue SDK(s) {sorted(forbidden)}; "
                "external execution belongs in execution-runtime"
            )


def is_allowed_composition_call(node: ast.Expr) -> bool:
    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return True
    if not isinstance(node.value, ast.Call):
        return False
    function = node.value.func
    return (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "app"
        and function.attr in ALLOWED_COMPOSITION_CALLS
    )


def check_composition_root(errors: list[str]) -> None:
    path = BACKEND_APP / "main.py"
    tree = parsed_module(path)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and is_allowed_composition_call(node):
            continue
        if isinstance(node, ast.Assign) and all(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        errors.append(
            "platform-api/app/main.py: composition root may only import, "
            "wire routers/middleware, and define __all__"
        )
        break


def check_execution_schema_boundary(errors: list[str]) -> None:
    compatibility_path = BACKEND_APP / "schemas.py"
    compatibility_tree = parsed_module(compatibility_path)
    duplicate_types = {
        node.name
        for node in compatibility_tree.body
        if isinstance(node, ast.ClassDef) and node.name in EXECUTION_SCHEMA_NAMES
    }
    if duplicate_types:
        errors.append(
            "platform-api/app/schemas.py: execution API schemas must be re-exported "
            f"from execution_schemas.py, not redefined: {sorted(duplicate_types)}"
        )

    import_names: set[str] = set()
    for node in compatibility_tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "app.execution_schemas":
            import_names.update(alias.name for alias in node.names)
    missing_exports = EXECUTION_SCHEMA_NAMES - import_names
    if missing_exports:
        errors.append(
            "platform-api/app/schemas.py: missing compatibility exports from "
            f"execution_schemas.py: {sorted(missing_exports)}"
        )


def check_financial_fact_repository_boundary(errors: list[str]) -> None:
    service_path = BACKEND_APP / "financial_facts.py"
    repository_path = BACKEND_APP / "financial_fact_repository.py"
    if not repository_path.is_file():
        errors.append(
            "platform-api/app/financial_fact_repository.py: "
            "FinancialFact persistence owner is missing"
        )
        return

    service_source = service_path.read_text(encoding="utf-8")
    service_tree = parsed_module(service_path)
    direct_database_import = any(
        isinstance(node, ast.ImportFrom) and node.module == "app.database"
        for node in ast.walk(service_tree)
    )
    if direct_database_import or "connection()" in service_source:
        errors.append(
            "platform-api/app/financial_facts.py: service must not access the database directly"
        )

    forbidden_sql = {
        prefix
        for literal in string_literals(service_path)
        for prefix in FINANCIAL_SERVICE_SQL_PREFIXES
        if prefix in literal.upper()
    }
    if forbidden_sql:
        errors.append(
            "platform-api/app/financial_facts.py: SQL belongs in financial_fact_repository.py: "
            f"{sorted(forbidden_sql)}"
        )

    repository_source = repository_path.read_text(encoding="utf-8")
    missing_sql = {
        anchor for anchor in FINANCIAL_REPOSITORY_SQL_ANCHORS if anchor not in repository_source
    }
    if missing_sql:
        errors.append(
            "platform-api/app/financial_fact_repository.py: "
            f"required persistence anchors missing: {sorted(missing_sql)}"
        )


def check_projection_boundaries(errors: list[str]) -> None:
    trading_path = BACKEND_APP / "trading.py"
    trading_source = trading_path.read_text(encoding="utf-8")
    trading_functions = {
        node.name
        for node in parsed_module(trading_path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if "record_fill_and_update_operational_projections" not in trading_functions:
        errors.append(
            "platform-api/app/trading.py: fill projection function must be named "
            "record_fill_and_update_operational_projections"
        )
    if "record_fill_and_update_projections" in trading_functions:
        errors.append(
            "platform-api/app/trading.py: ambiguous projection function name is forbidden"
        )
    missing_operational_writes = OPERATIONAL_PROJECTION_WRITE_ANCHORS - {
        statement
        for statement in OPERATIONAL_PROJECTION_WRITE_ANCHORS
        if statement in trading_source
    }
    if missing_operational_writes:
        errors.append(
            "platform-api/app/trading.py: expected operational projection writes are missing: "
            f"{sorted(missing_operational_writes)}"
        )
    forbidden_formal_writes = {
        statement for statement in FORMAL_PROJECTION_WRITES if statement in trading_source
    }
    if forbidden_formal_writes:
        errors.append(
            "platform-api/app/trading.py: trading flow must not write formal accounting tables: "
            f"{sorted(forbidden_formal_writes)}"
        )

    financial_source = (BACKEND_APP / "financial_facts.py").read_text(encoding="utf-8")
    repository_source = (BACKEND_APP / "financial_fact_repository.py").read_text(
        encoding="utf-8"
    )
    forbidden_operational_reads = {
        statement
        for statement in OPERATIONAL_PROJECTION_READS
        if statement in financial_source or statement in repository_source
    }
    if forbidden_operational_reads:
        errors.append(
            "formal accounting must not read operational projection tables: "
            f"{sorted(forbidden_operational_reads)}"
        )


def check_context_governance(errors: list[str]) -> None:
    for path in CANONICAL_CONTEXT_FILES:
        if not path.is_file():
            errors.append(f"{path.relative_to(ROOT)}: canonical context document is missing")
    for path in FORBIDDEN_PARALLEL_CONTEXT_PATHS:
        if path.exists():
            errors.append(
                f"{path.relative_to(ROOT)}: parallel project entry/context/template is forbidden; "
                "update docs/codex instead"
            )

    task_files = sorted((ROOT / "tasks").glob("issue-*.md"))
    invalid = [
        str(path.relative_to(ROOT))
        for path in task_files
        if re.fullmatch(r"issue-\d+-[a-z0-9][a-z0-9-]*\.md", path.name) is None
    ]
    if invalid:
        errors.append(f"Task packets must use issue-<number>-<slug>.md: {invalid}")


def check_persistence_governance(errors: list[str]) -> None:
    guide = ROOT / "docs" / "database" / "README.md"
    migration_module = BACKEND_APP / "schema_migrations.py"
    governance_module = BACKEND_APP / "schema_governance.py"
    for path in (guide, migration_module, governance_module):
        if not path.is_file():
            errors.append(f"{path.relative_to(ROOT)}: persistence governance file is missing")
    if not guide.is_file():
        return

    guide_source = guide.read_text(encoding="utf-8")
    for owner in DDL_OWNER_PATHS:
        path = ROOT / owner
        if not path.is_file():
            errors.append(f"{owner}: registered DDL owner does not exist")
        documented_owner = owner.removeprefix("platform-api/").removeprefix(
            "execution-runtime/"
        )
        if f"`{documented_owner}`" not in guide_source:
            errors.append(f"docs/database/README.md: missing DDL owner {owner}")

    if migration_module.is_file():
        source = migration_module.read_text(encoding="utf-8")
        required = ("schema_migrations", "existing-platform-schema-baseline", "checksum")
        missing = [anchor for anchor in required if anchor not in source]
        if missing:
            errors.append(
                "platform-api/app/schema_migrations.py: migration ledger anchors missing: "
                f"{missing}"
            )


def check_runtime_contract_governance(errors: list[str]) -> None:
    snapshot_path = ROOT / "docs" / "contracts" / "runtime-v1.json"
    platform_contract = BACKEND_APP / "runtime_contracts.py"
    runtime_contract = RUNTIME_APP / "runtime_contracts.py"
    for path in (snapshot_path, platform_contract, runtime_contract):
        if not path.is_file():
            errors.append(f"{path.relative_to(ROOT)}: runtime contract governance file is missing")
    if not snapshot_path.is_file():
        return

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"docs/contracts/runtime-v1.json: invalid JSON: {exc}")
        return
    for kind, fields in RUNTIME_CONTRACT_FIELDS.items():
        contract = snapshot.get(kind)
        if not isinstance(contract, dict):
            errors.append(f"docs/contracts/runtime-v1.json: missing {kind} contract")
            continue
        if contract.get("contractVersion") != "1.0" or contract.get("payloadVersion") != "1.0":
            errors.append(f"docs/contracts/runtime-v1.json: {kind} must remain explicit V1")
        if contract.get("fields") != fields:
            errors.append(
                f"docs/contracts/runtime-v1.json: {kind} field snapshot drifted; "
                "change the version and compatibility tests intentionally"
            )


def check_test_names(errors: list[str]) -> None:
    for root in TEST_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if FORBIDDEN_TEST_NAME.match(path.name):
                errors.append(
                    f"{path.relative_to(ROOT)}: temporary/versioned test suffix is forbidden; "
                    "merge the scenario into the canonical suite or use a domain-specific name"
                )


def check_workflow_names(errors: list[str]) -> None:
    for path in sorted(WORKFLOW_ROOT.glob("*.yml")):
        if FORBIDDEN_WORKFLOW_NAME.search(path.name):
            errors.append(
                f"{path.relative_to(ROOT)}: temporary diagnostic workflow must not be committed"
            )


def main() -> int:
    errors: list[str] = []
    check_backend_venue_boundary(errors)
    check_composition_root(errors)
    check_execution_schema_boundary(errors)
    check_financial_fact_repository_boundary(errors)
    check_projection_boundaries(errors)
    check_context_governance(errors)
    check_persistence_governance(errors)
    check_runtime_contract_governance(errors)
    check_test_names(errors)
    check_workflow_names(errors)
    if errors:
        print("Repository structure check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Repository structure check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
