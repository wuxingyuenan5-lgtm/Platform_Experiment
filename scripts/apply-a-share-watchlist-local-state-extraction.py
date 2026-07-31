#!/usr/bin/env python3
"""One-shot extraction of A-share watchlist local persistence responsibilities."""

from __future__ import annotations

from pathlib import Path

COMPOSABLE_PATH = Path(
    "platform-web/src/views/hedgeBoard/aShare/useAShareResearch.ts"
)
LAYOUT_PATH = Path("platform-web/scripts/verify-hedge-board-layout.cjs")
IMPORT_MARKER = "import { copyText } from '@/utils/copyTextToClipboard';\n"
LOCAL_IMPORTS = """import {
  normalizeStockCode,
  normalizeWatchlistItems,
  readWatchlist,
  readWatchlistDirty,
  writeWatchlist,
  writeWatchlistDirty,
  type WatchlistItem,
} from './aShareWatchlistLocalState';

export { normalizeStockCode };
export type { WatchlistItem };
"""
START_MARKER = "export interface WatchlistItem {\n"
END_MARKER = "function shanghaiDateStamp("
OLD_WATCH_BLOCK = """  watch(
    watchlist,
    (value) => {
      if (typeof window === 'undefined') return;
      try {
        window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(value));
      } catch {
        // Keep the in-memory watchlist usable when browser storage is unavailable.
      }
    },
    { deep: true },
  );
"""
NEW_WATCH_BLOCK = """  watch(
    watchlist,
    (value) => {
      writeWatchlist(value);
    },
    { deep: true },
  );
"""
LOCAL_PATH_LINE = """const aShareWatchlistLocalStatePath = path.join(
  viewRoot,
  'aShare',
  'aShareWatchlistLocalState.ts',
);
"""
LOCAL_SOURCE_LINE = (
    "const aShareWatchlistLocalStateSource = "
    "fs.readFileSync(aShareWatchlistLocalStatePath, 'utf8');\n"
)
LOCAL_EXISTS_LINE = (
    "assert(fs.existsSync(aShareWatchlistLocalStatePath), "
    "'Expected A-share watchlist local state adapter to exist.');\n"
)
OLD_WATCHLIST_ASSERTION = """assert(
  aShareResearchComposableSource.includes('export function normalizeStockCode') &&
    aShareResearchComposableSource.includes("if (stored === null) return [...DEFAULT_WATCHLIST]") &&
    !aShareResearchComposableSource.includes('!Array.isArray(payload) || !payload.length') &&
    aShareResearchComposableSource.includes('const groupIndexes = watchlist.value.reduce<number[]>'),
  'A-share watchlists must preserve stored empty arrays, normalize stock codes and reorder within groups.',
);
"""
NEW_WATCHLIST_ASSERTION = """assert(
  aShareResearchComposableSource.includes("from './aShareWatchlistLocalState'") &&
    aShareResearchComposableSource.includes('export { normalizeStockCode };') &&
    aShareResearchComposableSource.includes('export type { WatchlistItem };') &&
    aShareResearchComposableSource.includes('const groupIndexes = watchlist.value.reduce<number[]>') &&
    !aShareResearchComposableSource.includes('window.localStorage'),
  'A-share composable must delegate local watchlist persistence while preserving its public API and group moves.',
);
assert(
  aShareWatchlistLocalStateSource.includes('export function normalizeStockCode') &&
    aShareWatchlistLocalStateSource.includes("if (stored === null) return [...DEFAULT_WATCHLIST]") &&
    !aShareWatchlistLocalStateSource.includes('!Array.isArray(payload) || !payload.length') &&
    aShareWatchlistLocalStateSource.includes("const WATCHLIST_STORAGE_KEY = 'vg_a_share_watchlist_v1'") &&
    aShareWatchlistLocalStateSource.includes(
      "const WATCHLIST_DIRTY_STORAGE_KEY = 'vg_a_share_watchlist_dirty_v1'",
    ) &&
    aShareWatchlistLocalStateSource.includes('export function normalizeWatchlistItems') &&
    aShareWatchlistLocalStateSource.includes('export function readWatchlist') &&
    aShareWatchlistLocalStateSource.includes('export function writeWatchlist') &&
    aShareWatchlistLocalStateSource.includes('export function readWatchlistDirty') &&
    aShareWatchlistLocalStateSource.includes('export function writeWatchlistDirty'),
  'A-share local watchlist adapter must preserve code normalization, empty persistence, storage keys and dirty state.',
);
"""


def main() -> None:
    source = COMPOSABLE_PATH.read_text(encoding="utf-8-sig")
    layout = LAYOUT_PATH.read_text(encoding="utf-8")

    if LOCAL_IMPORTS not in source:
        if IMPORT_MARKER not in source:
            raise SystemExit("A-share composable import boundary was not found")
        source = source.replace(IMPORT_MARKER, IMPORT_MARKER + LOCAL_IMPORTS, 1)

    if START_MARKER in source:
        if END_MARKER not in source:
            raise SystemExit("A-share local state end boundary was not found")
        start = source.index(START_MARKER)
        end = source.index(END_MARKER, start)
        source = source[:start] + source[end:]

    if OLD_WATCH_BLOCK in source:
        source = source.replace(OLD_WATCH_BLOCK, NEW_WATCH_BLOCK, 1)
    elif NEW_WATCH_BLOCK not in source:
        raise SystemExit("A-share watchlist persistence watch boundary was not found")

    composable_path_marker = (
        "const aShareResearchComposablePath = "
        "path.join(viewRoot, 'aShare', 'useAShareResearch.ts');\n"
    )
    if LOCAL_PATH_LINE not in layout:
        if composable_path_marker not in layout:
            raise SystemExit("A-share composable path boundary was not found")
        layout = layout.replace(
            composable_path_marker,
            composable_path_marker + LOCAL_PATH_LINE,
            1,
        )

    composable_source_marker = (
        "const aShareResearchComposableSource = "
        "fs.readFileSync(aShareResearchComposablePath, 'utf8');\n"
    )
    if LOCAL_SOURCE_LINE not in layout:
        if composable_source_marker not in layout:
            raise SystemExit("A-share composable source boundary was not found")
        layout = layout.replace(
            composable_source_marker,
            composable_source_marker + LOCAL_SOURCE_LINE,
            1,
        )

    a_share_exists_marker = (
        "assert(fs.existsSync(aSharePagePath), "
        "'Expected dedicated A-share research page to exist.');\n"
    )
    if LOCAL_EXISTS_LINE not in layout:
        if a_share_exists_marker not in layout:
            raise SystemExit("A-share page existence boundary was not found")
        layout = layout.replace(
            a_share_exists_marker,
            a_share_exists_marker + LOCAL_EXISTS_LINE,
            1,
        )

    if OLD_WATCHLIST_ASSERTION in layout:
        layout = layout.replace(
            OLD_WATCHLIST_ASSERTION,
            NEW_WATCHLIST_ASSERTION,
            1,
        )
    elif NEW_WATCHLIST_ASSERTION not in layout:
        raise SystemExit("A-share watchlist layout assertion boundary was not found")

    layout = layout.replace(
        "aShareResearchComposableSource.includes('WATCHLIST_DIRTY_STORAGE_KEY')",
        "aShareWatchlistLocalStateSource.includes('WATCHLIST_DIRTY_STORAGE_KEY')",
        1,
    )

    required_source = (
        "from './aShareWatchlistLocalState'",
        "export { normalizeStockCode };",
        "export type { WatchlistItem };",
        "const watchlist = ref<WatchlistItem[]>(readWatchlist());",
        "readWatchlistDirty()",
        "writeWatchlistDirty(true)",
        "writeWatchlist(value);",
        "error.code !== 'watchlist_version_conflict'",
        "let watchlistSaveQueue: Promise<void> = Promise.resolve();",
    )
    if any(value not in source for value in required_source):
        raise SystemExit("A-share watchlist state contract moved unexpectedly")

    forbidden_source = (
        "const WATCHLIST_STORAGE_KEY",
        "const WATCHLIST_DIRTY_STORAGE_KEY",
        "const DEFAULT_WATCHLIST",
        "window.localStorage",
        START_MARKER.strip(),
    )
    if any(value in source for value in forbidden_source):
        raise SystemExit("A-share composable retained local persistence implementation details")

    required_layout = (
        LOCAL_PATH_LINE,
        LOCAL_SOURCE_LINE,
        LOCAL_EXISTS_LINE,
        NEW_WATCHLIST_ASSERTION,
        "aShareWatchlistLocalStateSource.includes('WATCHLIST_DIRTY_STORAGE_KEY')",
    )
    if any(value not in layout for value in required_layout):
        raise SystemExit("Permanent A-share local watchlist contracts were not installed")

    COMPOSABLE_PATH.write_text(source, encoding="utf-8")
    LAYOUT_PATH.write_text(layout, encoding="utf-8")
    print("A-share watchlist local state extraction and contracts are applied.")


if __name__ == "__main__":
    main()
