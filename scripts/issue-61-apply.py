from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "platform-backend/app"
TESTS = ROOT / "platform-backend/tests"


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise SystemExit(f"expected one match in {path}: {old[:80]!r}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


(APP / "position_math.py").write_text(
    '''from __future__ import annotations

from decimal import Decimal


def calculate_position_update(
    *,
    old_quantity: Decimal,
    old_average: Decimal | None,
    signed_fill: Decimal,
    fill_price: Decimal,
) -> tuple[Decimal, Decimal | None, Decimal]:
    """Apply one signed fill and return quantity, average price and realized PnL."""

    if old_quantity == 0 or old_quantity * signed_fill > 0:
        new_quantity = old_quantity + signed_fill
        old_notional = abs(old_quantity) * (old_average or Decimal("0"))
        new_notional = abs(signed_fill) * fill_price
        new_average = (old_notional + new_notional) / abs(new_quantity)
        return new_quantity, new_average, Decimal("0")

    closing_quantity = min(abs(old_quantity), abs(signed_fill))
    direction = Decimal("1") if old_quantity > 0 else Decimal("-1")
    realized_pnl = closing_quantity * (fill_price - (old_average or fill_price)) * direction
    new_quantity = old_quantity + signed_fill

    if new_quantity == 0:
        return new_quantity, None, realized_pnl
    if old_quantity * new_quantity > 0:
        return new_quantity, old_average, realized_pnl
    return new_quantity, fill_price, realized_pnl
''',
    encoding="utf-8",
)

trading_path = APP / "trading.py"
replace_once(
    trading_path,
    "from app.database import connection\nfrom app.schemas import CreateOrderRequest, OrderResponse\n",
    "from app.database import connection\n"
    "from app.position_math import calculate_position_update\n"
    "from app.schemas import CreateOrderRequest, OrderResponse\n",
)
replace_once(
    trading_path,
    '''\n\ndef calculate_position_update(\n    *,\n    old_quantity: Decimal,\n    old_average: Decimal | None,\n    signed_fill: Decimal,\n    fill_price: Decimal,\n) -> tuple[Decimal, Decimal | None, Decimal]:\n    if old_quantity == 0 or old_quantity * signed_fill > 0:\n        new_quantity = old_quantity + signed_fill\n        old_notional = abs(old_quantity) * (old_average or Decimal("0"))\n        new_notional = abs(signed_fill) * fill_price\n        new_average = (old_notional + new_notional) / abs(new_quantity)\n        return new_quantity, new_average, Decimal("0")\n\n    closing_quantity = min(abs(old_quantity), abs(signed_fill))\n    direction = Decimal("1") if old_quantity > 0 else Decimal("-1")\n    realized_pnl = closing_quantity * (fill_price - (old_average or fill_price)) * direction\n    new_quantity = old_quantity + signed_fill\n\n    if new_quantity == 0:\n        return new_quantity, None, realized_pnl\n    if old_quantity * new_quantity > 0:\n        return new_quantity, old_average, realized_pnl\n    return new_quantity, fill_price, realized_pnl\n''',
    "",
)

projection_path = APP / "financial_projection_service.py"
replace_once(
    projection_path,
    "from app.financial_fact_normalization import decimal_text, utc_iso\n",
    "from app.financial_fact_normalization import decimal_text, utc_iso\n"
    "from app.position_math import calculate_position_update\n",
)
replace_once(
    projection_path,
    '''\n\ndef calculate_position_update(\n    *,\n    old_quantity: Decimal,\n    old_average: Decimal | None,\n    signed_fill: Decimal,\n    fill_price: Decimal,\n) -> tuple[Decimal, Decimal | None, Decimal]:\n    if old_quantity == 0 or old_quantity * signed_fill > 0:\n        new_quantity = old_quantity + signed_fill\n        old_notional = abs(old_quantity) * (old_average or Decimal("0"))\n        new_notional = abs(signed_fill) * fill_price\n        new_average = (old_notional + new_notional) / abs(new_quantity)\n        return new_quantity, new_average, Decimal("0")\n\n    closing_quantity = min(abs(old_quantity), abs(signed_fill))\n    direction = Decimal("1") if old_quantity > 0 else Decimal("-1")\n    realized_pnl = closing_quantity * (fill_price - (old_average or fill_price)) * direction\n    new_quantity = old_quantity + signed_fill\n    if new_quantity == 0:\n        return new_quantity, None, realized_pnl\n    if old_quantity * new_quantity > 0:\n        return new_quantity, old_average, realized_pnl\n    return new_quantity, fill_price, realized_pnl\n''',
    "",
)

(TESTS / "test_position_calculation.py").write_text(
    '''from decimal import Decimal

import pytest

from app.position_math import calculate_position_update


@pytest.mark.parametrize(
    ("old_quantity", "old_average", "signed_fill", "fill_price", "expected"),
    [
        (
            Decimal("0"),
            None,
            Decimal("2"),
            Decimal("100"),
            (Decimal("2"), Decimal("100"), Decimal("0")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("1"),
            Decimal("130"),
            (Decimal("3"), Decimal("110"), Decimal("0")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("-1"),
            Decimal("110"),
            (Decimal("1"), Decimal("100"), Decimal("10")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("-2"),
            Decimal("110"),
            (Decimal("0"), None, Decimal("20")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("-3"),
            Decimal("90"),
            (Decimal("-1"), Decimal("90"), Decimal("-20")),
        ),
        (
            Decimal("0"),
            None,
            Decimal("-2"),
            Decimal("100"),
            (Decimal("-2"), Decimal("100"), Decimal("0")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("-1"),
            Decimal("70"),
            (Decimal("-3"), Decimal("90"), Decimal("0")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("1"),
            Decimal("90"),
            (Decimal("-1"), Decimal("100"), Decimal("10")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("2"),
            Decimal("110"),
            (Decimal("0"), None, Decimal("-20")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("3"),
            Decimal("90"),
            (Decimal("1"), Decimal("90"), Decimal("20")),
        ),
    ],
)
def test_calculate_position_update(
    old_quantity: Decimal,
    old_average: Decimal | None,
    signed_fill: Decimal,
    fill_price: Decimal,
    expected: tuple[Decimal, Decimal | None, Decimal],
) -> None:
    result = calculate_position_update(
        old_quantity=old_quantity,
        old_average=old_average,
        signed_fill=signed_fill,
        fill_price=fill_price,
    )

    assert result == expected
''',
    encoding="utf-8",
)

(TESTS / "test_architecture_position_math.py").write_text(
    '''import ast
from pathlib import Path

from app import financial_facts
from app import financial_projection_service as formal_projection
from app import position_math
from app import trading

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
OWNER_PATH = APP_ROOT / "position_math.py"


def defined_functions(path: Path) -> set[str]:
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


def test_position_math_is_the_only_function_definition_owner() -> None:
    definitions = [
        path.relative_to(APP_ROOT).as_posix()
        for path in APP_ROOT.glob("*.py")
        if "calculate_position_update" in defined_functions(path)
    ]

    assert definitions == ["position_math.py"]


def test_existing_import_paths_share_the_identical_callable() -> None:
    owner = position_math.calculate_position_update

    assert trading.calculate_position_update is owner
    assert formal_projection.calculate_position_update is owner
    assert financial_facts.calculate_position_update is owner


def test_position_math_has_no_framework_or_persistence_dependency() -> None:
    imports = imported_modules(OWNER_PATH)

    assert imports <= {"__future__", "decimal"}
''',
    encoding="utf-8",
)

(TESTS / "test_architecture_financial_projection_service.py").write_text(
    '''import ast
from pathlib import Path

from app import financial_facts
from app import financial_projection_service as service
from app import position_math

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SERVICE_PATH = APP_ROOT / "financial_projection_service.py"
API_PATH = APP_ROOT / "financial_facts.py"

PROJECTION_FUNCTIONS = {
    "conversion_rate",
    "optional_decimal",
    "rebuild_account_instrument_projection",
    "rebuild_strategy_financials",
    "run_formal_nav_snapshot",
}
REPOSITORY_ORCHESTRATION_CALLS = {
    "list_projection_fact_rows",
    "save_formal_projection",
    "prepare_strategy_rebuild",
    "record_projection_rebuild_audit",
    "list_active_account_rows",
    "load_latest_balance_rows",
    "store_formal_nav_snapshot",
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
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def test_projection_service_is_the_projection_orchestration_owner() -> None:
    service_functions = function_names(SERVICE_PATH)
    api_functions = function_names(API_PATH)
    compatibility_helpers = {
        "calculate_position_update",
        "conversion_rate",
        "optional_decimal",
    }

    assert PROJECTION_FUNCTIONS <= service_functions
    assert "calculate_position_update" not in service_functions
    assert not (compatibility_helpers & api_functions)


def test_api_module_keeps_compatibility_callables() -> None:
    assert service.calculate_position_update is position_math.calculate_position_update
    assert financial_facts.calculate_position_update is position_math.calculate_position_update
    assert financial_facts.conversion_rate is service.conversion_rate
    assert financial_facts.optional_decimal is service.optional_decimal
    assert callable(financial_facts.rebuild_account_instrument_projection)
    assert callable(financial_facts.rebuild_strategy_financials)
    assert callable(financial_facts.run_formal_nav_snapshot)


def test_projection_service_has_no_fastapi_or_config_dependency() -> None:
    imports = imported_modules(SERVICE_PATH)
    assert "fastapi" not in imports
    assert "app.config" not in imports
    assert "app.financial_fact_repository" in imports
    assert "app.financial_fact_normalization" in imports
    assert "app.position_math" in imports


def test_repository_projection_orchestration_is_not_in_api_module() -> None:
    api_source = API_PATH.read_text(encoding="utf-8")
    service_source = SERVICE_PATH.read_text(encoding="utf-8")
    api_calls = {
        call
        for call in REPOSITORY_ORCHESTRATION_CALLS
        if f"repository.{call}" in api_source
    }
    missing_service_calls = {
        call
        for call in REPOSITORY_ORCHESTRATION_CALLS
        if f"repository.{call}" not in service_source
    }

    assert not api_calls
    assert not missing_service_calls
''',
    encoding="utf-8",
)

pyproject = ROOT / "platform-backend/pyproject.toml"
replace_once(
    pyproject,
    '  "app/financial_projection_service.py",\n',
    '  "app/financial_projection_service.py",\n  "app/position_math.py",\n',
)

ownership = ROOT / "docs/architecture/OWNERSHIP.md"
replace_once(
    ownership,
    "| Operational fill projection | `platform-backend/app/trading.py` | "
    "Low-latency `positions` and `pnl_results` updates | Formal accounting authority |\n",
    "| Operational fill projection | `platform-backend/app/trading.py` | "
    "Low-latency `positions` and `pnl_results` updates | Formal accounting authority |\n"
    "| Position calculation policy | `platform-backend/app/position_math.py` | "
    "Pure per-fill net quantity, average price and realized PnL calculation shared by "
    "operational and formal projections | SQL, HTTP, FX, multiplier application or "
    "projection persistence |\n",
)
replace_once(
    ownership,
    "| Formal projection calculations | `platform-backend/app/financial_projection_service.py` | "
    "Average cost, realized/component PnL, formal rebuild and NAV calculations | FastAPI, "
    "configuration or direct SQL |\n",
    "| Formal projection calculations | `platform-backend/app/financial_projection_service.py` | "
    "FinancialFact replay, multiplier/FX application, component PnL, formal rebuild and "
    "NAV orchestration | FastAPI, configuration, direct SQL or duplicate position math |\n",
)

architecture = ROOT / "docs/architecture/README.md"
replace_once(
    architecture,
    "- Pyright 覆盖执行 DTO、FinancialFact DTO/Normalization/Repository/Projection Service、"
    "SQLite Connection/Bootstrap/Seeds、Runtime 契约、迁移账本和权威下单边界。\n",
    "- Pyright 覆盖执行 DTO、FinancialFact DTO/Normalization/Repository/Projection Service、"
    "共享 Position Math、SQLite Connection/Bootstrap/Seeds、Runtime 契约、迁移账本和"
    "权威下单边界。\n",
)
replace_once(
    architecture,
    "- `platform-backend/app/financial_projection_service.py` 负责平均成本、已实现与分项 "
    "PnL、正式重建和 NAV 计算。\n",
    "- `platform-backend/app/position_math.py` 是运营与正式投影共享的逐成交净数量、"
    "平均成本和已实现 PnL 纯计算唯一 Owner。\n"
    "- `platform-backend/app/financial_projection_service.py` 负责 FinancialFact 回放、"
    "Multiplier/FX、分项 PnL、正式重建和 NAV 编排。\n",
)

checker = ROOT / "scripts/check-documentation-consistency.py"
replace_once(
    checker,
    '    "Operational fill projection": "platform-backend/app/trading.py",\n',
    '    "Operational fill projection": "platform-backend/app/trading.py",\n'
    '    "Position calculation policy": "platform-backend/app/position_math.py",\n',
)

debt = ROOT / "docs/engineering/TECHNICAL_DEBT.md"
replace_once(
    debt,
    "- Platform execution DTOs, FinancialFact DTOs/Normalization/Repository/Projection Service, "
    "SQLite Connection/Bootstrap/Seeds, Runtime contracts, schema migrations, schema governance "
    "and authoritative order submission are selected;\n",
    "- Platform execution DTOs, FinancialFact DTOs/Normalization/Repository/Projection Service, "
    "shared Position Math, SQLite Connection/Bootstrap/Seeds, Runtime contracts, schema "
    "migrations, schema governance and authoritative order submission are selected;\n",
)

state = ROOT / "docs/codex/current-state.md"
replace_once(
    state,
    "No engineering code workstream is active by default after PR #60 merges.",
    "Issue #61 / Draft PR #62 is the only active engineering workstream: shared Position Math "
    "ownership extraction.",
)

changelog = ROOT / "CHANGELOG.md"
entry = '''### Shared Position Math ownership — Issue #61 / PR #62

- Added `platform-backend/app/position_math.py` as the pure per-fill quantity, average-price and realized-PnL calculation owner.
- Made operational, formal and FinancialFact compatibility paths reference the identical callable.
- Expanded golden cases across long/short opens, increases, partial/full closes and both flip directions.
- Added sole-definition, purity and compatibility-identity architecture checks and progressive Pyright coverage.
- Preserved every formula result, multiplier/FX treatment, persistence transaction, API, Runtime contract and both Live Write defaults.

'''
marker = "## Unreleased\n\n"
content = changelog.read_text(encoding="utf-8")
if entry not in content:
    if marker not in content:
        raise SystemExit("Changelog Unreleased marker not found")
    changelog.write_text(content.replace(marker, marker + entry, 1), encoding="utf-8")

task = ROOT / "tasks/issue-61-shared-position-math.md"
replace_once(
    task,
    "- `platform-backend/tests/test_position_math.py`\n"
    "- `platform-backend/tests/test_architecture_position_math.py`\n",
    "- `platform-backend/tests/test_position_calculation.py`\n"
    "- `platform-backend/tests/test_architecture_position_math.py`\n"
    "- `platform-backend/tests/test_architecture_financial_projection_service.py`\n",
)
replace_once(
    task,
    "- `docs/architecture/OWNERSHIP.md`\n",
    "- `docs/architecture/OWNERSHIP.md`\n- `docs/architecture/README.md`\n",
)
replace_once(
    task,
    "- `platform-backend/tests/test_architecture_documentation_consistency.py`\n",
    "",
)
replace_once(
    task,
    "- Done: Issue and branch created.\n"
    "- Current: implementation design and source/test inspection.\n"
    "- Next: code extraction and direct verification.\n",
    "- Done: Issue/branch/PR and implementation design.\n"
    "- Current: code extraction, golden tests and architecture checks.\n"
    "- Next: full CI, Diff review and merge.\n",
)
replace_once(task, "- PR:\n", "- PR: #62\n")

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-61-apply.yml"
if workflow.exists():
    workflow.unlink()
