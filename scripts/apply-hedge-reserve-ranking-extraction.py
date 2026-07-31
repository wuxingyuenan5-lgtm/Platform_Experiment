#!/usr/bin/env python3
"""One-shot extraction of the hedge-board reserve ranking component."""

from __future__ import annotations

from pathlib import Path

PAGE_PATH = Path("platform-web/src/views/hedgeBoard/index.vue")
LAYOUT_PATH = Path("platform-web/scripts/verify-hedge-board-layout.cjs")
IMPORT_LINE = "  import ReserveRanking from './components/ReserveRanking';\n"
IMPORT_MARKER = "  import MetricStrip from './components/MetricStrip';\n"
START_MARKER = "  const ReserveRanking = defineComponent({\n"
END_MARKER = "  const SnapshotDetailTable = defineComponent({\n"
RESERVE_PATH_LINE = (
    "const reserveRankingPath = path.join(viewRoot, 'components', 'ReserveRanking.ts');\n"
)
RESERVE_SOURCE_LINE = (
    "const reserveRankingSource = fs.readFileSync(reserveRankingPath, 'utf8');\n"
)
RESERVE_EXISTS_LINE = (
    "assert(fs.existsSync(reserveRankingPath), 'Expected ReserveRanking component to exist.');\n"
)
RESERVE_ASSERTIONS = """assert(
  hedgeBoardSource.includes("import ReserveRanking from './components/ReserveRanking';") &&
    !hedgeBoardSource.includes('const ReserveRanking = defineComponent'),
  'Hedge board must delegate reserve ranking rendering to the external component.',
);
assert(
  reserveRankingSource.includes("name: 'ReserveRanking'") &&
    reserveRankingSource.includes('type: Array as PropType<ReserveRankingRow[]>') &&
    reserveRankingSource.includes("class: 'reserve-module'") &&
    reserveRankingSource.includes('Math.max(...props.rows.map') &&
    reserveRankingSource.includes('key: `${row.label}-${row.value}`') &&
    reserveRankingSource.includes("row.value >= 0 ? '#148b6a' : '#dc2626'") &&
    reserveRankingSource.includes("minWidth: props.diverging && row.value < 0 ? '12px' : undefined") &&
    reserveRankingSource.includes("formatSigned(row.value) + ' 吨'"),
  'ReserveRanking must preserve props, scaling, tones, item key and displayed value.',
);
"""


def main() -> None:
    source = PAGE_PATH.read_text(encoding="utf-8-sig")
    layout = LAYOUT_PATH.read_text(encoding="utf-8")

    if IMPORT_LINE not in source or START_MARKER in source:
        if IMPORT_MARKER not in source:
            raise SystemExit("MetricStrip import boundary was not found")
        if START_MARKER not in source or END_MARKER not in source:
            raise SystemExit("Inline ReserveRanking boundary was not found")
        source = source.replace(IMPORT_MARKER, IMPORT_MARKER + IMPORT_LINE, 1)
        start = source.index(START_MARKER)
        end = source.index(END_MARKER, start)
        source = source[:start] + source[end:]

    if RESERVE_PATH_LINE not in layout:
        marker = "const metricStripPath = path.join(viewRoot, 'components', 'MetricStrip.ts');\n"
        if marker not in layout:
            raise SystemExit("MetricStrip path boundary was not found")
        layout = layout.replace(marker, marker + RESERVE_PATH_LINE, 1)

    if RESERVE_SOURCE_LINE not in layout:
        marker = "const metricStripSource = fs.readFileSync(metricStripPath, 'utf8');\n"
        if marker not in layout:
            raise SystemExit("MetricStrip source boundary was not found")
        layout = layout.replace(marker, marker + RESERVE_SOURCE_LINE, 1)

    if RESERVE_EXISTS_LINE not in layout:
        marker = (
            "assert(fs.existsSync(metricStripPath), "
            "'Expected MetricStrip component to exist.');\n"
        )
        if marker not in layout:
            raise SystemExit("MetricStrip existence boundary was not found")
        layout = layout.replace(marker, marker + RESERVE_EXISTS_LINE, 1)

    if RESERVE_ASSERTIONS not in layout:
        marker = """assert(
  !hedgeBoardSource.includes("from './nativeData/dashboard'") &&
"""
        if marker not in layout:
            raise SystemExit("Legacy dashboard assertion boundary was not found")
        layout = layout.replace(marker, RESERVE_ASSERTIONS + marker, 1)

    required = (
        IMPORT_LINE.strip(),
        "h(ReserveRanking",
        "const SnapshotDetailTable = defineComponent",
        "const LocalChartWidget = defineComponent",
    )
    if any(value not in source for value in required):
        raise SystemExit("Hedge-board reserve ranking contract moved unexpectedly")
    if START_MARKER in source:
        raise SystemExit("Hedge-board page retained inline ReserveRanking implementation")
    if any(
        value not in layout
        for value in (
            RESERVE_PATH_LINE,
            RESERVE_SOURCE_LINE,
            RESERVE_EXISTS_LINE,
            RESERVE_ASSERTIONS,
        )
    ):
        raise SystemExit("Permanent ReserveRanking layout contracts were not installed")

    PAGE_PATH.write_text(source, encoding="utf-8")
    LAYOUT_PATH.write_text(layout, encoding="utf-8")
    print("ReserveRanking extraction and permanent contracts are applied.")


if __name__ == "__main__":
    main()
