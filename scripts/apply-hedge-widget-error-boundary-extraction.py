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


def main() -> None:
    source = PAGE_PATH.read_text(encoding="utf-8-sig")
    layout = LAYOUT_PATH.read_text(encoding="utf-8")

    if BROAD_AI_GUARD in layout:
        layout = layout.replace(BROAD_AI_GUARD, TARGETED_AI_GUARD, 1)
    elif TARGETED_AI_GUARD not in layout:
        raise SystemExit("Stock snapshot AI layout guard boundary was not found")

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

    PAGE_PATH.write_text(source, encoding="utf-8")
    LAYOUT_PATH.write_text(layout, encoding="utf-8")
    print("WidgetErrorBoundary extracted and the objective-data guard narrowed.")


if __name__ == "__main__":
    main()
