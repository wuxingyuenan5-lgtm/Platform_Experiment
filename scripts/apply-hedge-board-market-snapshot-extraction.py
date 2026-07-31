#!/usr/bin/env python3
"""Mechanically extract Hedge Board static market snapshot tables."""

from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
MODULE_PATH = ROOT / "platform-web/src/views/hedgeBoard/nativeData/marketSnapshotTables.ts"
TEST_PATH = ROOT / "platform-api/tests/test_architecture_hedge_board_market_snapshot_data.py"

TYPE_START = "  interface SnapshotTableRow {\n"
TYPE_END = "  const CHART_WIDTH = 760;\n"
DATA_START = "  const LOCAL_MARKET_DETAIL_TABLES: Record<\n"
DATA_END = "  const BTC_ETF_FLOW_ROWS: DualChartRow[] = [\n"
IMPORT_ANCHOR = "  import { marketData } from './nativeData/generated/marketData';\n"
MODULE_IMPORT = """  import {
    LOCAL_MARKET_DETAIL_TABLES,
    type SnapshotTableGroup,
    type SnapshotTableRow,
  } from './nativeData/marketSnapshotTables';
"""
HASH_NAME = "MARKET_SNAPSHOT_SOURCE_SHA256"


def build_test(expected_hash: str) -> str:
    return f'''from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
MODULE = ROOT / "platform-web/src/views/hedgeBoard/nativeData/marketSnapshotTables.ts"
EXPECTED_SOURCE_SHA256 = "{expected_hash}"


@pytest.mark.architecture
def test_market_snapshot_tables_have_one_static_data_owner() -> None:
    index = INDEX.read_text(encoding="utf-8")
    module = MODULE.read_text(encoding="utf-8")

    assert "from './nativeData/marketSnapshotTables'" in index
    assert "interface SnapshotTableRow" not in index
    assert "interface SnapshotTableGroup" not in index
    assert "const LOCAL_MARKET_DETAIL_TABLES" not in index

    assert "export interface SnapshotTableRow" in module
    assert "export interface SnapshotTableGroup" in module
    assert "export const LOCAL_MARKET_DETAIL_TABLES" in module
    assert f'export const {{HASH_NAME}} = "{{EXPECTED_SOURCE_SHA256}}";' in module

    body, _ = module.split("\\nexport const {HASH_NAME}", maxsplit=1)
    normalized = body.replace(
        "export interface SnapshotTableRow",
        "interface SnapshotTableRow",
        1,
    ).replace(
        "export interface SnapshotTableGroup",
        "interface SnapshotTableGroup",
        1,
    ).replace(
        "export const LOCAL_MARKET_DETAIL_TABLES",
        "const LOCAL_MARKET_DETAIL_TABLES",
        1,
    )
    assert hashlib.sha256(normalized.encode("utf-8")).hexdigest() == EXPECTED_SOURCE_SHA256

    for forbidden_dependency in (
        "from '",
        'from "',
        "fetch(",
        "axios",
        "localStorage",
        "vue-router",
        "hedgeResearch",
    ):
        assert forbidden_dependency not in module
'''


def main() -> None:
    source = INDEX_PATH.read_text(encoding="utf-8")

    if MODULE_PATH.exists() and TEST_PATH.exists():
        if TYPE_START in source or DATA_START in source:
            raise SystemExit("Snapshot module exists but inline owner remains")
        if MODULE_IMPORT not in source:
            raise SystemExit("Snapshot module exists but index import is missing")
        print("Market snapshot extraction is already applied.")
        return

    for marker in (TYPE_START, TYPE_END, DATA_START, DATA_END, IMPORT_ANCHOR):
        if source.count(marker) != 1:
            raise SystemExit(f"Expected exactly one extraction marker: {marker!r}")
    if MODULE_IMPORT in source:
        raise SystemExit("Snapshot module import already exists without generated files")

    type_start = source.index(TYPE_START)
    type_end = source.index(TYPE_END, type_start)
    type_block = textwrap.dedent(source[type_start:type_end]).rstrip()

    without_types = source[:type_start] + source[type_end:]
    data_start = without_types.index(DATA_START)
    data_end = without_types.index(DATA_END, data_start)
    data_block = textwrap.dedent(without_types[data_start:data_end]).rstrip()

    normalized_payload = f"{type_block}\n\n{data_block}\n"
    source_hash = hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()

    exported_types = type_block.replace(
        "interface SnapshotTableRow",
        "export interface SnapshotTableRow",
        1,
    ).replace(
        "interface SnapshotTableGroup",
        "export interface SnapshotTableGroup",
        1,
    )
    exported_data = data_block.replace(
        "const LOCAL_MARKET_DETAIL_TABLES",
        "export const LOCAL_MARKET_DETAIL_TABLES",
        1,
    )
    module_body = f"{exported_types}\n\n{exported_data}\n"
    module_content = (
        module_body
        + f'\nexport const {HASH_NAME} = "{source_hash}";\n'
    )

    updated = without_types[:data_start] + without_types[data_end:]
    updated = updated.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + MODULE_IMPORT, 1)

    if TYPE_START in updated or DATA_START in updated:
        raise SystemExit("Inline snapshot owner was not fully removed")
    if updated.count(MODULE_IMPORT) != 1:
        raise SystemExit("Snapshot import was not installed exactly once")
    if "LOCAL_MARKET_DETAIL_TABLES[widget.kind]" not in updated:
        raise SystemExit("LocalChartWidget snapshot lookup contract is missing")

    MODULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODULE_PATH.write_text(module_content, encoding="utf-8")
    TEST_PATH.write_text(build_test(source_hash), encoding="utf-8")
    INDEX_PATH.write_text(updated, encoding="utf-8")
    print(f"Extracted market snapshot tables with source SHA-256 {source_hash}")


if __name__ == "__main__":
    main()
