from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_version_checker():
    path = ROOT / "scripts/check-version-consistency.py"
    spec = importlib.util.spec_from_file_location("check_version_consistency", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


version_checker = load_version_checker()


def test_maintained_release_versions_match_root_version() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/check-version-consistency.py")],
        cwd=ROOT,
        check=True,
    )


def copy_version_fixture(tmp_path: Path) -> None:
    for relative in (*version_checker.MAINTAINED_VERSION_PATHS, *version_checker.VERSION_USAGE_PATHS):
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


@pytest.mark.parametrize(
    ("relative_path", "current", "stale"),
    [
        ("platform-api/app/application.py", 'PLATFORM_VERSION = "0.9.3"', 'PLATFORM_VERSION = "0.6.0"'),
        ("execution-runtime/app/main.py", 'PLATFORM_VERSION = "0.9.3"', 'PLATFORM_VERSION = "0.5.0"'),
    ],
)
def test_runtime_version_drift_is_rejected(
    tmp_path: Path,
    relative_path: str,
    current: str,
    stale: str,
) -> None:
    copy_version_fixture(tmp_path)
    path = tmp_path / relative_path
    path.write_text(path.read_text(encoding="utf-8").replace(current, stale, 1), encoding="utf-8")

    with pytest.raises(SystemExit, match="Version drift from VERSION=0.9.3"):
        version_checker.check_versions(tmp_path)
