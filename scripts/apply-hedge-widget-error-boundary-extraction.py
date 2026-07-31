#!/usr/bin/env python3
"""One-shot extraction of the hedge-board widget error boundary."""

from __future__ import annotations

from pathlib import Path

PAGE_PATH = Path("platform-web/src/views/hedgeBoard/index.vue")
IMPORT_LINE = "  import WidgetErrorBoundary from './components/WidgetErrorBoundary';\n"
IMPORT_MARKER = "  import TerminalDetailPanel from './components/TerminalDetailPanel.vue';\n"
START_MARKER = "  const WidgetErrorBoundary = defineComponent({\n"
END_MARKER = "  const MetricStrip = defineComponent({\n"


def main() -> None:
    source = PAGE_PATH.read_text(encoding="utf-8-sig")
    if IMPORT_LINE in source and START_MARKER not in source:
        print("Widget error boundary extraction is already applied.")
        return

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

    PAGE_PATH.write_text(source, encoding="utf-8")
    print("WidgetErrorBoundary extracted behind the existing component contract.")


if __name__ == "__main__":
    main()
