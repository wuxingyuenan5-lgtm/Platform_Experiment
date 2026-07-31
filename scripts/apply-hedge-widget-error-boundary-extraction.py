#!/usr/bin/env python3
"""One-shot extraction of the hedge-board widget error boundary."""

from __future__ import annotations

from pathlib import Path

PAGE_PATH = Path("platform-web/src/views/hedgeBoard/index.vue")
LAYOUT_PATH = Path("platform-web/scripts/verify-hedge-board-layout.cjs")
IMPORT_LINE = "  import WidgetErrorBoundary from './components/WidgetErrorBoundary';\n"
IMPORT_MARKER = "  import TerminalDetailPanel from './components/TerminalDetailPanel.vue';\n"
START_MARKER = "  const WidgetErrorBoundary = defineComponent({\n"
END_MARKER = "  const MetricStrip = defineComponent({\n"
BROAD_AI_GUARD = "    !stockSnapshotSource.toLowerCase().includes('ai'),\n"
TARGETED_AI_GUARD = (
    "    !/\\bAI\\b|人工智能|智能分析|AI建议|买卖建议/i.test(stockSnapshotSource),\n"
)
WIDGET_PATH_LINE = (
    "const widgetErrorBoundaryPath = path.join(\n"
    "  viewRoot,\n"
    "  'components',\n"
    "  'WidgetErrorBoundary.ts',\n"
    ");\n"
)
WIDGET_SOURCE_LINE = (
    "const widgetErrorBoundarySource = fs.readFileSync(widgetErrorBoundaryPath, 'utf8');\n"
)
WIDGET_EXISTS_LINE = (
    "assert(fs.existsSync(widgetErrorBoundaryPath), "
    "'Expected WidgetErrorBoundary component to exist.');\n"
)
WIDGET_ASSERTIONS = """assert(
  hedgeBoardSource.includes(
    "import WidgetErrorBoundary from './components/WidgetErrorBoundary';",
  ) &&
    hedgeBoardSource.includes(':widget-error-boundary="WidgetErrorBoundary"') &&
    !hedgeBoardSource.includes('const WidgetErrorBoundary = defineComponent'),
  'Hedge board must delegate widget error isolation to the external component.',
);
assert(
  widgetErrorBoundarySource.includes("name: 'WidgetErrorBoundary'") &&
    widgetErrorBoundarySource.includes('widgetTitle') &&
    widgetErrorBoundarySource.includes('onErrorCaptured') &&
    widgetErrorBoundarySource.includes('return false') &&
    widgetErrorBoundarySource.includes("class: 'local-empty'") &&
    widgetErrorBoundarySource.includes("minHeight: '360px'") &&
    widgetErrorBoundarySource.includes(
      '模块 "${props.widgetTitle}" 渲染失败，已自动跳过，不影响其他内容浏览。',
    ),
  'WidgetErrorBoundary must preserve the original error isolation, root class and fallback copy.',
);
"""


def main() -> None:
    source = PAGE_PATH.read_text(encoding="utf-8-sig")
    layout = LAYOUT_PATH.read_text(encoding="utf-8")

    if BROAD_AI_GUARD in layout:
        layout = layout.replace(BROAD_AI_GUARD, TARGETED_AI_GUARD, 1)
    elif TARGETED_AI_GUARD not in layout:
        raise SystemExit("Stock snapshot AI layout guard boundary was not found")

    if WIDGET_PATH_LINE not in layout:
        marker = (
            "const terminalDetailPanelPath = path.join("
            "viewRoot, 'components', 'TerminalDetailPanel.vue');\n"
        )
        if marker not in layout:
            raise SystemExit("Terminal detail path boundary was not found")
        layout = layout.replace(marker, marker + WIDGET_PATH_LINE, 1)

    if WIDGET_SOURCE_LINE not in layout:
        marker = (
            "const terminalDetailPanelSource = "
            "fs.readFileSync(terminalDetailPanelPath, 'utf8');\n"
        )
        if marker not in layout:
            raise SystemExit("Terminal detail source boundary was not found")
        layout = layout.replace(marker, marker + WIDGET_SOURCE_LINE, 1)

    if WIDGET_EXISTS_LINE not in layout:
        marker = (
            "assert(fs.existsSync(terminalDetailPanelPath), "
            "'Expected TerminalDetailPanel component to exist.');\n"
        )
        if marker not in layout:
            raise SystemExit("Terminal detail existence boundary was not found")
        layout = layout.replace(marker, marker + WIDGET_EXISTS_LINE, 1)

    if WIDGET_ASSERTIONS not in layout:
        marker = """assert(
  hedgeBoardSource.includes('TerminalDetailPanel') && hedgeBoardSource.includes('TerminalDetailPanel from'),
  'Hedge board local detail widgets must use TerminalDetailPanel.',
);
"""
        if marker not in layout:
            raise SystemExit("Terminal detail assertion boundary was not found")
        layout = layout.replace(marker, marker + WIDGET_ASSERTIONS, 1)

    if IMPORT_LINE not in source or START_MARKER in source:
        if IMPORT_MARKER not in source:
            raise SystemExit("TerminalDetailPanel import boundary was not found")
        if START_MARKER not in source or END_MARKER not in source:
            raise SystemExit("Inline WidgetErrorBoundary boundary was not found")

        source = source.replace(IMPORT_MARKER, IMPORT_MARKER + IMPORT_LINE, 1)
        source = source.replace("    onErrorCaptured,\n", "", 1)
        source = source.replace("    useSlots,\n", "", 1)

        start = source.index(START_MARKER)
        end = source.index(END_MARKER, start)
        source = source[:start] + source[end:]

    required = (
        IMPORT_LINE.strip(),
        ':widget-error-boundary="WidgetErrorBoundary"',
        "const MetricStrip = defineComponent",
        "const TradingViewWidget = defineComponent",
        "const LocalChartWidget = defineComponent",
    )
    if any(value not in source for value in required):
        raise SystemExit("Hedge-board component contract moved unexpectedly")

    forbidden = (
        "const WidgetErrorBoundary = defineComponent",
        "onErrorCaptured",
        "useSlots",
    )
    if any(value in source for value in forbidden):
        raise SystemExit("Hedge-board page retained widget boundary implementation details")
    if TARGETED_AI_GUARD not in layout or BROAD_AI_GUARD in layout:
        raise SystemExit("Stock snapshot objective-data guard was not narrowed correctly")
    if any(
        value not in layout
        for value in (
            WIDGET_PATH_LINE,
            WIDGET_SOURCE_LINE,
            WIDGET_EXISTS_LINE,
            WIDGET_ASSERTIONS,
        )
    ):
        raise SystemExit("Permanent WidgetErrorBoundary layout contracts were not installed")

    PAGE_PATH.write_text(source, encoding="utf-8")
    LAYOUT_PATH.write_text(layout, encoding="utf-8")
    print("WidgetErrorBoundary extraction and permanent contracts are applied.")


if __name__ == "__main__":
    main()
