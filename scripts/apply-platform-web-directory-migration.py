#!/usr/bin/env python3
"""Apply the one-time admin-risk to platform-web mechanical directory migration."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

LEGACY = "admin-risk"
REPLACEMENT = "platform-web"
ACTIVE_CATEGORIES = {
    "active_ci",
    "active_root_contract",
    "active_service_tree",
    "active_tooling",
    "current_documentation",
}

PLAN_CONTENT = """# 项目推进计划

## 权威入口

- 当前工程状态：`docs/codex/current-state.md`
- 系统性优化主线：GitHub Issue #136
- 总体方案：`docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md`
- 目录迁移方案：`docs/architecture/PLATFORM_DIRECTORY_MIGRATION_PLAN.md`

## 当前阶段

Phase A全仓审计、Phase B上下文减负和Phase C全平台视觉门禁均已完成。当前进入独立命名与目录治理阶段，先迁移Platform Web，再迁移Platform API；每个目录Gate均须通过完整CI、浏览器E2E和四档视觉基线。

## 约束

- 目录重命名不得与业务逻辑或模块重构混在同一提交；
- `execution-runtime`保持独立且不改名；
- `projects/risk-control`在真实服务器、MySQL和用户数据依赖确认前不得删除或机械迁移；
- Draft PR保持Open、Draft、Unmerged，未经所有者明确批准不得修改`main`。
"""


def run(*args: str, cwd: Path, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )


def replace_active_reference(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    output: list[str] = []
    for line in content.splitlines():
        if LEGACY in line:
            line = line.replace(LEGACY, REPLACEMENT).rstrip()
        output.append(line)
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def inventory(root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "directory-migration.json"
        run(
            sys.executable,
            "scripts/audit-directory-migration.py",
            "--root",
            ".",
            "--format",
            "json",
            "--output",
            str(output),
            "--fail-on-unclassified",
            cwd=root,
        )
        return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    legacy_root = root / LEGACY
    replacement_root = root / REPLACEMENT

    if not legacy_root.exists() and replacement_root.is_dir():
        print("Platform Web directory is already migrated; no changes required.")
        return 0
    if not legacy_root.is_dir() or replacement_root.exists():
        raise RuntimeError("Expected legacy frontend directory only before migration")

    before = inventory(root)
    references = before["references"]
    assert isinstance(references, list)
    active_paths = sorted(
        {
            str(reference["path"])
            for reference in references
            if reference["legacy_name"] == LEGACY
            and reference["category"] in ACTIVE_CATEGORIES
        }
    )

    run("git", "mv", LEGACY, REPLACEMENT, cwd=root)
    for raw_path in active_paths:
        path = Path(raw_path)
        if raw_path.startswith(f"{LEGACY}/"):
            path = Path(REPLACEMENT) / path.relative_to(LEGACY)
        replace_active_reference(root / path)

    package_path = replacement_root / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["name"] = "vg-platform-web"
    package_path.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    (root / "PLAN.md").write_text(PLAN_CONTENT, encoding="utf-8")
    master_plan = root / "docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md"
    content = master_plan.read_text(encoding="utf-8")
    content = content.replace(
        "2. `platform-web → platform-web`；",
        "2. 前端顶层目录统一为 `platform-web`；",
    )
    master_plan.write_text(content, encoding="utf-8")

    run("git", "add", "-A", cwd=root)
    run(
        sys.executable,
        "scripts/audit-directory-migration.py",
        "--root",
        ".",
        "--mode",
        "post-rename",
        "--target",
        LEGACY,
        "--fail-on-unclassified",
        cwd=root,
    )
    print(f"Platform Web migration staged with {len(active_paths)} active files updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
