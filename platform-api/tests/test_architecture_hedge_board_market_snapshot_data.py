from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
LOCAL_WIDGET = ROOT / "platform-web/src/views/hedgeBoard/charts/LocalChartWidget.ts"
TERMINAL_CONFIG = ROOT / "platform-web/src/views/hedgeBoard/nativeData/marketTerminal.ts"
PAGE_COMPOSABLE = ROOT / "platform-web/src/views/hedgeBoard/composables/useHedgeBoardPage.ts"
GOLD_PANEL = ROOT / "platform-web/src/views/hedgeBoard/components/GoldMarketDetailPanel.vue"
CRYPTO_PANEL = ROOT / "platform-web/src/views/hedgeBoard/components/CryptoMarketDetailPanel.vue"
LEGACY_MODULE = ROOT / "platform-web/src/views/hedgeBoard/nativeData/marketSnapshotTables.ts"


@pytest.mark.architecture
def test_market_snapshot_tables_have_one_active_owner() -> None:
    index = INDEX.read_text(encoding="utf-8")
    local_widget = LOCAL_WIDGET.read_text(encoding="utf-8")
    terminal_config = TERMINAL_CONFIG.read_text(encoding="utf-8")
    page_composable = PAGE_COMPOSABLE.read_text(encoding="utf-8")
    gold_panel = GOLD_PANEL.read_text(encoding="utf-8")
    crypto_panel = CRYPTO_PANEL.read_text(encoding="utf-8")

    assert not LEGACY_MODULE.exists()
    for legacy_symbol in (
        "SnapshotTableRow",
        "SnapshotTableGroup",
        "LOCAL_MARKET_DETAIL_TABLES",
        "GroupedBarChart",
        "SnapshotDetailTable",
    ):
        assert legacy_symbol not in index
        assert legacy_symbol not in local_widget

    assert "import TerminalDetailPanel" in local_widget
    assert "marketTerminalConfigs" not in local_widget
    assert "case 'gold-market-detail-table':" in local_widget
    assert "case 'crypto-market-detail-table':" in local_widget
    assert "marketTerminalConfigs" in page_composable
    assert "marketTerminalConfigs.gold" in gold_panel
    assert "marketTerminalConfigs.crypto" in crypto_panel
    assert "detailColumns" in terminal_config
    assert "detailGroups" in terminal_config
