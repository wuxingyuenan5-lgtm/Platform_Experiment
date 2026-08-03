from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "platform-api/app"
ALLOWLIST = ROOT / "docs/architecture/non-repository-sql-allowlist.json"
DIRECT_SQL = re.compile(
    r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE)\b",
    re.IGNORECASE,
)


def test_non_repository_direct_sql_has_no_new_owner() -> None:
    policy = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    allowed = set(policy["files"])
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in APP_ROOT.glob("*.py")
        if "repository" not in path.stem
        and DIRECT_SQL.search(path.read_text(encoding="utf-8"))
    }

    unexpected = sorted(actual - allowed)
    assert unexpected == [], f"New non-Repository direct SQL owners: {unexpected}"
    assert all(item["owner"] and item["reason"] for item in policy["files"].values())
