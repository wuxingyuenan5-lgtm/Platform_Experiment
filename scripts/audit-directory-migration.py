#!/usr/bin/env python3
"""Inventory legacy top-level directory references before/after the Platform rename.

This is intentionally read-only. It distinguishes active repository contracts from
historical records so the rename does not mechanically rewrite archived evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

RENAMES = {
    "admin-risk": "platform-web",
    "platform-backend": "platform-api",
}

ACTIVE_ROOT_FILES = {
    ".gitignore",
    ".ignore",
    "AGENTS.md",
    "PLAN.md",
    "README.md",
}

HISTORICAL_SEGMENTS = {
    "archive",
    "archived",
    "audit",
    "audits",
    "reviews",
    "superseded",
}


@dataclass(frozen=True)
class Reference:
    legacy_name: str
    replacement: str
    path: str
    line: int
    category: str
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--mode",
        choices=("inventory", "post-rename"),
        default="inventory",
        help="post-rename fails when an active reference still uses a legacy name",
    )
    parser.add_argument("--fail-on-unclassified", action="store_true")
    parser.add_argument(
        "--target",
        choices=("all", *RENAMES),
        default="all",
        help="rename target enforced by post-rename mode",
    )
    return parser.parse_args()


def tracked_files(root: Path) -> Iterable[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    for item in result.stdout.split(b"\0"):
        if item:
            yield root / item.decode("utf-8", errors="surrogateescape")


def classify(path: str) -> str:
    normalized = path.replace("\\", "/")
    parts = set(Path(normalized).parts)

    if normalized.startswith("tasks/") or normalized == "CHANGELOG.md":
        return "historical_record"
    if parts & HISTORICAL_SEGMENTS:
        return "historical_record"
    if normalized.startswith(("projects/", "references/", "00-人工可读目录/")):
        return "external_or_legacy_dependency"
    if normalized in {
        "scripts/audit-directory-migration.py",
        "scripts/apply-platform-web-directory-migration.py",
        ".github/workflows/platform-web-directory-migration.yml",
        "docs/architecture/PLATFORM_DIRECTORY_MIGRATION_PLAN.md",
    }:
        return "migration_governance"
    if normalized.startswith(".github/"):
        return "active_ci"
    if normalized.startswith(("scripts/", "deploy/")):
        return "active_tooling"
    if normalized in ACTIVE_ROOT_FILES:
        return "active_root_contract"
    if normalized.startswith("docs/"):
        return "current_documentation"
    if normalized.startswith(
        ("admin-risk/", "platform-web/", "platform-backend/", "platform-api/")
    ):
        return "active_service_tree"
    return "unclassified"


def collect(root: Path) -> list[Reference]:
    references: list[Reference] = []
    for file_path in tracked_files(root):
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = file_path.relative_to(root).as_posix()
        category = classify(relative)
        for line_number, line in enumerate(content.splitlines(), start=1):
            for legacy_name, replacement in RENAMES.items():
                if legacy_name in line:
                    references.append(
                        Reference(
                            legacy_name=legacy_name,
                            replacement=replacement,
                            path=relative,
                            line=line_number,
                            category=category,
                            text=line.strip(),
                        )
                    )
    return references


def summarize(root: Path, references: list[Reference]) -> dict[str, object]:
    by_name: dict[str, object] = {}
    for legacy_name, replacement in RENAMES.items():
        items = [item for item in references if item.legacy_name == legacy_name]
        category_lines = Counter(item.category for item in items)
        category_files: dict[str, set[str]] = defaultdict(set)
        for item in items:
            category_files[item.category].add(item.path)
        by_name[legacy_name] = {
            "replacement": replacement,
            "reference_lines": len(items),
            "files": len({item.path for item in items}),
            "categories": {
                category: {
                    "reference_lines": category_lines[category],
                    "files": len(category_files[category]),
                }
                for category in sorted(category_lines)
            },
            "legacy_directory_exists": (root / legacy_name).is_dir(),
            "replacement_directory_exists": (root / replacement).is_dir(),
        }
    return {
        "root": str(root),
        "renames": by_name,
        "unclassified_files": sorted(
            {item.path for item in references if item.category == "unclassified"}
        ),
    }


def render_markdown(summary: dict[str, object], references: list[Reference]) -> str:
    lines = [
        "# Platform directory migration inventory",
        "",
        "This report is generated from tracked UTF-8 text files. Historical records are",
        "separated from active repository contracts and are not automatically rewritten.",
        "",
        "## Summary",
        "",
        "| Legacy path | Replacement | Files | Reference lines | Legacy dir | New dir |",
        "|---|---|---:|---:|---|---|",
    ]
    renames = summary["renames"]
    assert isinstance(renames, dict)
    for legacy_name, raw in renames.items():
        assert isinstance(raw, dict)
        lines.append(
            f"| `{legacy_name}` | `{raw['replacement']}` | {raw['files']} | "
            f"{raw['reference_lines']} | {raw['legacy_directory_exists']} | "
            f"{raw['replacement_directory_exists']} |"
        )

    lines.extend(["", "## Category counts", ""])
    for legacy_name, raw in renames.items():
        assert isinstance(raw, dict)
        lines.extend(
            [
                f"### `{legacy_name}` → `{raw['replacement']}`",
                "",
                "| Category | Files | Reference lines |",
                "|---|---:|---:|",
            ]
        )
        categories = raw["categories"]
        assert isinstance(categories, dict)
        for category, counts in categories.items():
            assert isinstance(counts, dict)
            lines.append(
                f"| `{category}` | {counts['files']} | {counts['reference_lines']} |"
            )
        lines.append("")

    lines.extend(["## Active files", ""])
    active_categories = {
        "active_ci",
        "active_root_contract",
        "active_service_tree",
        "active_tooling",
        "current_documentation",
    }
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in references:
        if item.category in active_categories:
            grouped[(item.legacy_name, item.category)].add(item.path)
    for (legacy_name, category), paths in sorted(grouped.items()):
        lines.append(f"### `{legacy_name}` / `{category}`")
        lines.append("")
        lines.extend(f"- `{path}`" for path in sorted(paths))
        lines.append("")

    unclassified = summary["unclassified_files"]
    assert isinstance(unclassified, list)
    lines.extend(["## Unclassified", ""])
    if unclassified:
        lines.extend(f"- `{path}`" for path in unclassified)
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    references = collect(root)
    summary = summarize(root, references)

    if args.format == "json":
        payload = {
            "summary": summary,
            "references": [asdict(item) for item in references],
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        rendered = render_markdown(summary, references)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    unclassified = summary["unclassified_files"]
    assert isinstance(unclassified, list)
    if args.fail_on_unclassified and unclassified:
        return 1

    if args.mode == "post-rename":
        active_categories = {
            "active_ci",
            "active_root_contract",
            "active_service_tree",
            "active_tooling",
            "current_documentation",
        }
        selected = set(RENAMES) if args.target == "all" else {args.target}
        active_legacy = [
            item
            for item in references
            if item.legacy_name in selected and item.category in active_categories
        ]
        directory_failures = [
            legacy_name
            for legacy_name, replacement in RENAMES.items()
            if legacy_name in selected
            if (root / legacy_name).exists() or not (root / replacement).is_dir()
        ]
        if active_legacy or directory_failures:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
