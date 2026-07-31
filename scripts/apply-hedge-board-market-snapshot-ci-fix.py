#!/usr/bin/env python3
"""Apply the bounded CI-only cleanup for Hedge Board market snapshot extraction."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
TEST_PATH = ROOT / "platform-api/tests/test_architecture_hedge_board_market_snapshot_data.py"

OLD_IMPORT = """  import {
    LOCAL_MARKET_DETAIL_TABLES,
    type SnapshotTableGroup,
    type SnapshotTableRow,
  } from './nativeData/marketSnapshotTables';
"""
NEW_IMPORT = """  import {
    LOCAL_MARKET_DETAIL_TABLES,
    type SnapshotTableGroup,
  } from './nativeData/marketSnapshotTables';
"""

OLD_HASH_ASSERTION = """    assert (
        f'export const MARKET_SNAPSHOT_SOURCE_SHA256 = \"{EXPECTED_SOURCE_SHA256}\";'
        in module
    )
"""
NEW_HASH_ASSERTION = """    hash_match = re.search(
        r\"export const MARKET_SNAPSHOT_SOURCE_SHA256\\s*=\\s*['\\\"]([0-9a-f]{64})['\\\"];\",
        module,
    )
    assert hash_match is not None
    assert hash_match.group(1) == EXPECTED_SOURCE_SHA256
"""


def replace_once(content: str, old: str, new: str, label: str) -> str:
    if new in content and old not in content:
        return content
    if content.count(old) != 1:
        raise SystemExit(f"Expected exactly one {label} block")
    return content.replace(old, new, 1)


def main() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")
    index = replace_once(index, OLD_IMPORT, NEW_IMPORT, "snapshot import")

    test = TEST_PATH.read_text(encoding="utf-8")
    if "import re\n" not in test:
        if test.count("import hashlib\n") != 1:
            raise SystemExit("Expected exactly one hashlib import")
        test = test.replace("import hashlib\n", "import hashlib\nimport re\n", 1)
    test = replace_once(test, OLD_HASH_ASSERTION, NEW_HASH_ASSERTION, "hash assertion")

    INDEX_PATH.write_text(index, encoding="utf-8")
    TEST_PATH.write_text(test, encoding="utf-8")
    print("Applied format-independent snapshot hash guard and removed unused type import.")


if __name__ == "__main__":
    main()
