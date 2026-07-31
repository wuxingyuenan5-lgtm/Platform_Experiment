from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
MODULE = ROOT / "platform-web/src/views/hedgeBoard/nativeData/marketSnapshotTables.ts"
EXPECTED_SOURCE_SHA256 = "20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a"


@pytest.mark.architecture
def test_market_snapshot_tables_have_one_static_data_owner() -> None:
    index = INDEX.read_text(encoding="utf-8")
    module = MODULE.read_text(encoding="utf-8")

    assert "from './nativeData/marketSnapshotTables'" in index
    assert "interface SnapshotTableRow" not in index
    assert "interface SnapshotTableGroup" not in index
    assert "const LOCAL_MARKET_DETAIL_TABLES" not in index
    assert "void [LOCAL_MARKET_DETAIL_TABLES, GroupedBarChart, SnapshotDetailTable];" in index

    assert "export interface SnapshotTableRow" in module
    assert "export interface SnapshotTableGroup" in module
    assert "export const LOCAL_MARKET_DETAIL_TABLES" in module
    assert (
        f'export const MARKET_SNAPSHOT_SOURCE_SHA256 = "{EXPECTED_SOURCE_SHA256}";'
        in module
    )

    body, _ = module.split(
        "\nexport const MARKET_SNAPSHOT_SOURCE_SHA256",
        maxsplit=1,
    )
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
