#!/usr/bin/env python3
"""One-shot extraction of the hedge-board metric strip."""

from __future__ import annotations

from pathlib import Path

PAGE_PATH = Path("platform-web/src/views/hedgeBoard/index.vue")
LAYOUT_PATH = Path("platform-web/scripts/verify-hedge-board-layout.cjs")
IMPORT_LINE = "  import MetricStrip from './components/MetricStrip';\n"
IMPORT_MARKER = "  import WidgetErrorBoundary from './components/WidgetErrorBoundary';\n"
START_MARKER = "  const MetricStrip = defineComponent({\n"
END_MARKER = "  function buildRangeOverview("
METRIC_PATH_LINE = (
    "const metricStripPath = path.join(viewRoot, 'components', 'MetricStrip.ts');\n"
)
METRIC_SOURCE_LINE = "const metricStripSource = fs.readFileSync(metricStripPath, 'utf8');\n"
METRIC_EXISTS_LINE = (
    "assert(fs.existsSync(metricStripPath), 'Expected MetricStrip component to exist.');\n"
)
METRIC_ASSERTIONS = """assert(
  hedgeBoardSource.includes("import MetricStrip from './components/MetricStrip';") &&
    !hedgeBoardSource.includes('const MetricStrip = defineComponent'),
  'Hedge board must delegate metric strip rendering to the external component.',
);
assert(
  metricStripSource.includes("name: 'MetricStrip'") &&
    metricStripSource.includes('type: Array as PropType<Array<[string, string]>>') &&
    metricStripSource.includes("class: 'metric-strip'") &&
    metricStripSource.includes('props.metrics.map') &&
    metricStripSource.includes("h('article'") &&
    metricStripSource.includes('key: `${label}-${value}`') &&
    metricStripSource.includes("h('span', label)") &&
    metricStripSource.includes("h('strong', value)"),
  'MetricStrip must preserve its prop type, root class, item hierarchy and stable key.',
);
"""


def main() -> None:
    source = PAGE_PATH.read_text(encoding="utf-8-sig")
    layout = LAYOUT_PATH.read_text(encoding="utf-8")

    if IMPORT_LINE not in source or START_MARKER in source:
        if IMPORT_MARKER not in source:
            raise SystemExit("WidgetErrorBoundary import boundary was not found")
        if START_MARKER not in source or END_MARKER not in source:
            raise SystemExit("Inline MetricStrip boundary was not found")
        source = source.replace(IMPORT_MARKER, IMPORT_MARKER + IMPORT_LINE, 1)
        start = source.index(START_MARKER)
        end = source.index(END_MARKER, start)
        source = source[:start] + source[end:]

    if METRIC_PATH_LINE not in layout:
        marker = """const widgetErrorBoundaryPath = path.join(
  viewRoot,
  'components',
  'WidgetErrorBoundary.ts',
);
"""
        if marker not in layout:
            raise SystemExit("WidgetErrorBoundary path boundary was not found")
        layout = layout.replace(marker, marker + METRIC_PATH_LINE, 1)

    if METRIC_SOURCE_LINE not in layout:
        marker = (
            "const widgetErrorBoundarySource = "
            "fs.readFileSync(widgetErrorBoundaryPath, 'utf8');\n"
        )
        if marker not in layout:
            raise SystemExit("WidgetErrorBoundary source boundary was not found")
        layout = layout.replace(marker, marker + METRIC_SOURCE_LINE, 1)

    if METRIC_EXISTS_LINE not in layout:
        marker = (
            "assert(fs.existsSync(widgetErrorBoundaryPath), "
            "'Expected WidgetErrorBoundary component to exist.');\n"
        )
        if marker not in layout:
            raise SystemExit("WidgetErrorBoundary existence boundary was not found")
        layout = layout.replace(marker, marker + METRIC_EXISTS_LINE, 1)

    if METRIC_ASSERTIONS not in layout:
        marker = """assert(
  !hedgeBoardSource.includes("from './nativeData/dashboard'") &&
"""
        if marker not in layout:
            raise SystemExit("Legacy dashboard assertion boundary was not found")
        layout = layout.replace(marker, METRIC_ASSERTIONS + marker, 1)

    required = (
        IMPORT_LINE.strip(),
        "h(MetricStrip",
        "function buildRangeOverview",
        "const LocalChartWidget = defineComponent",
    )
    if any(value not in source for value in required):
        raise SystemExit("Hedge-board metric strip contract moved unexpectedly")
    if START_MARKER in source:
        raise SystemExit("Hedge-board page retained the inline MetricStrip implementation")
    if any(
        value not in layout
        for value in (
            METRIC_PATH_LINE,
            METRIC_SOURCE_LINE,
            METRIC_EXISTS_LINE,
            METRIC_ASSERTIONS,
        )
    ):
        raise SystemExit("Permanent MetricStrip layout contracts were not installed")

    PAGE_PATH.write_text(source, encoding="utf-8")
    LAYOUT_PATH.write_text(layout, encoding="utf-8")
    print("MetricStrip extraction and permanent contracts are applied.")


if __name__ == "__main__":
    main()
