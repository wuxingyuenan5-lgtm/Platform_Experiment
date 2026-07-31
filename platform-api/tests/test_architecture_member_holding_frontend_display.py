from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MEMBER_PANEL = ROOT / "platform-web/src/views/account/components/HoldingsPanel.vue"
ADMIN_PANEL = ROOT / "platform-web/src/views/users/components/UserHoldingsPanel.vue"
DECIMAL_DISPLAY = ROOT / "platform-web/src/utils/decimalDisplay.ts"


@pytest.mark.architecture
def test_member_holding_views_share_decimal_display_owner() -> None:
    member = MEMBER_PANEL.read_text(encoding="utf-8")
    admin = ADMIN_PANEL.read_text(encoding="utf-8")
    owner = DECIMAL_DISPLAY.read_text(encoding="utf-8")

    for view in (member, admin):
        assert "@/utils/decimalDisplay" in view
        assert "formatDecimalString" in view
        assert "formatMoneyString" in view
        assert "formatSignedMoneyString" in view
        assert "decimalDirection" in view

    assert "function splitDecimal" not in admin
    assert "integer.replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',')" not in admin
    assert "value === '0'" not in admin

    assert "export function decimalDirection" in owner
    assert "^0+(?:\\.0+)?$" in owner
    assert "decimalDirection(value) === 'zero'" in owner


@pytest.mark.architecture
def test_member_summary_never_silently_aggregates_partial_valuation() -> None:
    member = MEMBER_PANEL.read_text(encoding="utf-8")

    assert "const hasCompleteValuation = computed" in member
    assert "holdings.value.every(" in member
    assert "isDecimal(item.marketValue)" in member
    assert "isDecimal(item.cumulativeReturn)" in member
    assert "canAggregate.value && hasCompleteValuation.value" in member

    assert ".map((item) => item.marketValue).filter(isDecimal)" not in member
    assert ".map((item) => item.cumulativeReturn).filter(isDecimal)" not in member
