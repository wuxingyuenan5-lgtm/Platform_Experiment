from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CURRENT_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


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
    paths = dict.fromkeys(
        (
            *version_checker.MAINTAINED_VERSION_PATHS,
            *version_checker.VERSION_USAGE_PATHS,
        )
    )
    for relative in paths:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


@pytest.mark.parametrize(
    ("relative_path", "stale"),
    [
        (
            "platform-api/app/application.py",
            'PLATFORM_VERSION = "0.6.0"',
        ),
        (
            "execution-runtime/app/version.py",
            'PLATFORM_VERSION = "0.5.0"',
        ),
    ],
)
def test_runtime_version_drift_is_rejected(
    tmp_path: Path,
    relative_path: str,
    stale: str,
) -> None:
    copy_version_fixture(tmp_path)
    path = tmp_path / relative_path
    source = path.read_text(encoding="utf-8")
    current = f'PLATFORM_VERSION = "{CURRENT_VERSION}"'
    assert current in source
    path.write_text(source.replace(current, stale, 1), encoding="utf-8")

    with pytest.raises(
        SystemExit,
        match=rf"Version drift from VERSION={re.escape(CURRENT_VERSION)}",
    ):
        version_checker.check_versions(tmp_path)


@pytest.mark.parametrize(
    "relative_path",
    [
        "execution-runtime/app/main.py",
        "execution-runtime/app/system_routes.py",
    ],
)
def test_runtime_version_consumers_must_use_formal_owner(
    tmp_path: Path,
    relative_path: str,
) -> None:
    copy_version_fixture(tmp_path)
    path = tmp_path / relative_path
    source = path.read_text(encoding="utf-8")
    path.write_text(
        source.replace(
            "from app.version import PLATFORM_VERSION",
            "# formal version owner import removed",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="Version source usage is missing"):
        version_checker.check_versions(tmp_path)


def test_runtime_rejects_duplicate_platform_version_owner(tmp_path: Path) -> None:
    copy_version_fixture(tmp_path)
    main_path = tmp_path / "execution-runtime/app/main.py"
    main_path.write_text(
        f'{main_path.read_text(encoding="utf-8")}\n'
        f'PLATFORM_VERSION = "{CURRENT_VERSION}"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="must have exactly one owner"):
        version_checker.check_versions(tmp_path)
