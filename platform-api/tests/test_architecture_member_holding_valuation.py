from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.architecture
def test_member_holding_valuation_is_pure_and_service_retains_security_boundaries() -> None:
    service = (ROOT / "app" / "member_holding_service.py").read_text(encoding="utf-8")
    valuation_path = ROOT / "app" / "member_holding_valuation.py"
    valuation = valuation_path.read_text(encoding="utf-8")

    imported = imported_modules(valuation_path)
    assert not {
        name
        for name in imported
        if name.startswith(("sqlite3", "fastapi", "app.database", "app.auth"))
    }

    assert "build_holding_response" in service
    assert "HoldingValuationError" in service
    assert "def _parse_aware" not in service
    assert "calculate_holding(" not in service
    assert "parse_non_negative_decimal(\n            holding.share_quantity" not in service

    for retained_call in (
        "assert_recent_reauthentication",
        'db.execute("BEGIN IMMEDIATE")',
        "_assert_member_target",
        "insert_audit_event",
        "get_fund",
        "get_latest_available_nav",
        "upsert_member_holding",
        "insert_fund_nav",
    ):
        assert retained_call in service

    for valuation_contract in (
        "def build_holding_response",
        "calculate_holding(",
        'nav_status: NavStatus = "unavailable"',
        'nav_status = "stale" if current - nav_valuation_time > stale_after else "available"',
        '"fund_nav_currency_mismatch"',
        '"fund_nav_timestamp_invalid"',
        "cumulative_return / cumulative_invested",
    ):
        source = valuation if valuation_contract != "cumulative_return / cumulative_invested" else (
            ROOT / "app" / "member_holding_decimal.py"
        ).read_text(encoding="utf-8")
        assert valuation_contract in source
