from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

pytestmark = pytest.mark.unit


def test_read_local_json_uses_configured_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "public/v1/macro/dashboard.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schemaVersion": "1.0"}), encoding="utf-8")
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    assert read_local_json("public/v1/macro/dashboard.json") == {"schemaVersion": "1.0"}


def test_read_local_json_rejects_path_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    with pytest.raises(ResearchProviderError, match="local_data_path_outside_root"):
        read_local_json("../outside.json")


def test_concurrent_json_writes_use_distinct_temporary_paths(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from app.research_local_data import write_local_json

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: write_local_json(f"raw/{n}.json", {"n": n}), range(32)))
    assert [read_local_json(f"raw/{n}.json")["n"] for n in range(32)] == list(range(32))
    assert not list(tmp_path.rglob("*.tmp"))
