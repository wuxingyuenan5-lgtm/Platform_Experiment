#!/usr/bin/env python3
"""Mechanically extract the inline Hedge Board TradingView widget."""

from __future__ import annotations

import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
COMPONENT_PATH = ROOT / "platform-web/src/views/hedgeBoard/components/TradingViewWidget.ts"

START_MARKER = "  const TradingViewWidget = defineComponent({\n"
END_MARKER = "  function buildRangeOverview("
IMPORT_ANCHOR = "  import TerminalDetailPanel from './components/TerminalDetailPanel.vue';\n"
COMPONENT_IMPORT = "  import TradingViewWidget from './components/TradingViewWidget';\n"

COMPONENT_IMPORTS = """import {
  defineComponent,
  h,
  onBeforeUnmount,
  onMounted,
  type PropType,
  ref,
  watch,
} from 'vue';
import type { WidgetConfig } from '../nativeData/dashboardClean';

"""


def main() -> None:
    source = INDEX_PATH.read_text(encoding="utf-8")

    if COMPONENT_PATH.exists():
        if START_MARKER in source:
            raise SystemExit("TradingViewWidget component exists but inline owner remains")
        if COMPONENT_IMPORT not in source:
            raise SystemExit("TradingViewWidget component exists but index import is missing")
        print("TradingViewWidget extraction is already applied.")
        return

    if source.count(START_MARKER) != 1:
        raise SystemExit("Expected exactly one inline TradingViewWidget owner")
    if source.count(END_MARKER) != 1:
        raise SystemExit("Expected exactly one buildRangeOverview boundary")
    if source.count(IMPORT_ANCHOR) != 1:
        raise SystemExit("Expected exactly one TradingView import anchor")
    if COMPONENT_IMPORT in source:
        raise SystemExit("TradingViewWidget import already exists without component file")

    start = source.index(START_MARKER)
    end = source.index(END_MARKER, start)
    inline_component = source[start:end]
    if "name: 'TradingViewWidget'" not in inline_component:
        raise SystemExit("Inline extraction block does not contain TradingViewWidget")
    if "const TradingViewWidget" not in inline_component:
        raise SystemExit("Inline extraction block is incomplete")

    component_body = textwrap.dedent(inline_component).rstrip() + "\n\nexport default TradingViewWidget;\n"
    component_content = COMPONENT_IMPORTS + component_body

    updated = source[:start] + source[end:]
    updated = updated.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + COMPONENT_IMPORT, 1)
    if updated.count("onBeforeUnmount") == 1:
        updated = updated.replace("    onBeforeUnmount,\n", "", 1)

    if START_MARKER in updated or "const TradingViewWidget = defineComponent" in updated:
        raise SystemExit("Inline TradingViewWidget owner was not fully removed")
    if updated.count(COMPONENT_IMPORT) != 1:
        raise SystemExit("TradingViewWidget import was not installed exactly once")
    if ":trading-view-widget=\"TradingViewWidget\"" not in updated:
        raise SystemExit("HedgeResearchModule TradingView contract is missing")

    COMPONENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPONENT_PATH.write_text(component_content, encoding="utf-8")
    INDEX_PATH.write_text(updated, encoding="utf-8")
    print("Extracted TradingViewWidget without changing its render contract.")


if __name__ == "__main__":
    main()
