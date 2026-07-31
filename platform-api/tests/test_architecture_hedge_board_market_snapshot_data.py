from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
MODULE = ROOT / "platform-web/src/views/hedgeBoard/nativeData/marketSnapshotTables.ts"
EXPECTED_SOURCE_SHA256 = "20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a"
EXPECTED_CANONICAL_SHA256 = "580983d83781cb7f0731dd39837d75b16eaf24be18751367432aa605fa0acc92"
HASH_PATTERN = re.compile(
    r"export const MARKET_SNAPSHOT_SOURCE_SHA256\s*=\s*"
    r"['\"]([0-9a-f]{64})['\"];"
)


def canonicalize_typescript(payload: str) -> str:
    output: list[str] = []
    quote: str | None = None
    escaped = False

    for character in payload:
        if quote is not None:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue

        if character in {"'", '"', "`"}:
            quote = character
            output.append(character)
        elif not character.isspace():
            output.append(character)

    assert quote is None
    return "".join(output)


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
    assert module.count("export const MARKET_SNAPSHOT_SOURCE_SHA256") == 1

    hash_match = HASH_PATTERN.search(module)
    assert hash_match is not None
    assert hash_match.group(1) == EXPECTED_SOURCE_SHA256

    body, separator, _ = module.partition(
        "\nexport const MARKET_SNAPSHOT_SOURCE_SHA256"
    )
    assert separator
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
    canonical = canonicalize_typescript(normalized)
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == EXPECTED_CANONICAL_SHA256

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
