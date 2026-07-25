from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_maintained_release_versions_match_root_version() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/check-version-consistency.py")],
        cwd=ROOT,
        check=True,
    )
