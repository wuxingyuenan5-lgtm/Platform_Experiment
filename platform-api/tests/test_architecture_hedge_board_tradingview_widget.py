from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
COMPONENT = ROOT / "platform-web/src/views/hedgeBoard/components/TradingViewWidget.ts"


@pytest.mark.architecture
def test_tradingview_widget_has_one_pure_frontend_owner() -> None:
    index = INDEX.read_text(encoding="utf-8")
    component = COMPONENT.read_text(encoding="utf-8")

    assert "import TradingViewWidget from './components/TradingViewWidget';" in index
    assert "const TradingViewWidget = defineComponent" not in index
    assert ":trading-view-widget=\"TradingViewWidget\"" in index

    for contract in (
        "name: 'TradingViewWidget'",
        "type: Object as PropType<WidgetConfig>",
        "ResizeObserver",
        "IntersectionObserver",
        "window.requestAnimationFrame",
        "verifyTimers = [180, 520, 1100, 1900]",
        "repairAttempts < 3",
        "threshold: 0.2",
        "该外部图表当前加载失败，页面主体已保留，可继续浏览其他模块。",
        "class: 'widget-frame'",
        "class: 'local-empty'",
        "export default TradingViewWidget",
    ):
        assert contract in component

    for forbidden_dependency in (
        "vue-router",
        "hedgeResearch",
        "marketData",
        "researchModules",
        "loadTradingToolBoardCatalog",
        "localStorage",
        "fetch(",
        "axios",
    ):
        assert forbidden_dependency not in component
