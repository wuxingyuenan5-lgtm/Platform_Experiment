#!/usr/bin/env python3
"""Validate active documentation entrypoints, links and portability."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote, urlsplit

REQUIRED_ENTRYPOINTS = (
    "README.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/codex/current-state.md",
    "docs/codex/context-map.md",
    "docs/architecture/SYSTEM_MAP.md",
    "docs/architecture/OWNERSHIP.md",
    "docs/operations/RUNBOOK.md",
    "docs/database/README.md",
    "docs/engineering/GIT_WORKFLOW.md",
    "docs/contracts/README.md",
)
EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".turbo",
        ".venv",
        "artifacts",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "outputs",
        "test-results",
        "vendor",
    }
)
EXTERNAL_SCHEMES = frozenset({"data", "http", "https", "javascript", "mailto", "tel"})
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]\n]*\]\((?P<target>[^)\n]+)\)")
FENCED_CODE_PATTERN = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
CURRENT_STATE_ALIASES = re.compile(r"^current[-_]state\.md$", re.IGNORECASE)
START_HERE_ALIASES = re.compile(r"^start[-_]here(?:\.md)?$", re.IGNORECASE)
WORKSTATION_PATH_PATTERNS = (
    (
        "Windows user profile",
        re.compile(
            r"(?i)\b[A-Z]:\\Users\\(?!<user>(?:\\|$)|username(?:\\|$)|%USERNAME%(?:\\|$))"
            r"[^\\\s`]+(?:\\|$)"
        ),
    ),
    (
        "macOS user home",
        re.compile(r"/Users/(?!<user>(?:/|$)|username(?:/|$)|\$\{?USER\}?(?:/|$))[^/\s`]+(?:/|$)"),
    ),
    (
        "Linux user home",
        re.compile(r"/home/(?!<user>(?:/|$)|username(?:/|$)|\$\{?USER\}?(?:/|$))[^/\s`]+(?:/|$)"),
    ),
)


def active_markdown_paths(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.md"))
        if not (set(path.relative_to(root).parts) & EXCLUDED_PARTS)
    ]


def markdown_without_examples(content: str) -> str:
    return HTML_COMMENT_PATTERN.sub("", FENCED_CODE_PATTERN.sub("", content))


def markdown_link_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if not target:
        return None
    if target.startswith("<"):
        closing = target.find(">")
        if closing == -1:
            return None
        target = target[1:closing].strip()
    else:
        target = target.split(maxsplit=1)[0]
    if not target or target.startswith(("#", "//")):
        return None
    if any(marker in target for marker in ("<", ">", "{", "}")):
        return None
    if urlsplit(target).scheme.lower() in EXTERNAL_SCHEMES:
        return None
    return target


def validate_markdown_links(
    root: Path,
    markdown_paths: Iterable[Path] | None = None,
) -> list[str]:
    root = root.resolve()
    paths = active_markdown_paths(root) if markdown_paths is None else sorted(markdown_paths)
    errors: list[str] = []
    for source in paths:
        if not source.is_file():
            continue
        relative_source = source.resolve().relative_to(root).as_posix()
        content = markdown_without_examples(source.read_text(encoding="utf-8"))
        for match in MARKDOWN_LINK_PATTERN.finditer(content):
            target = markdown_link_target(match.group("target"))
            if target is None:
                continue
            link_path = unquote(urlsplit(target).path)
            if not link_path:
                continue
            candidate = (
                root / link_path.lstrip("/")
                if link_path.startswith("/")
                else source.parent / link_path
            ).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                errors.append(
                    f"{relative_source}: local Markdown target escapes repository: {target}"
                )
                continue
            if not candidate.exists():
                errors.append(
                    f"{relative_source}: local Markdown target does not exist: {target}"
                )
    return sorted(errors)


def validate_portable_documentation(
    root: Path,
    markdown_paths: Iterable[Path] | None = None,
) -> list[str]:
    root = root.resolve()
    paths = active_markdown_paths(root) if markdown_paths is None else sorted(markdown_paths)
    errors: list[str] = []
    for source in paths:
        if not source.is_file():
            continue
        relative_source = source.resolve().relative_to(root).as_posix()
        content = markdown_without_examples(source.read_text(encoding="utf-8"))
        for label, pattern in WORKSTATION_PATH_PATTERNS:
            for match in pattern.finditer(content):
                errors.append(
                    f"{relative_source}: workstation-specific {label} path is forbidden: "
                    f"{match.group(0)}"
                )
    return sorted(errors)


def validate_entrypoints(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_ENTRYPOINTS:
        if not (root / relative).is_file():
            errors.append(f"required documentation entrypoint is missing: {relative}")

    current = root / "docs/codex/current-state.md"
    for path in sorted(root.rglob("*")):
        if not path.is_file() or set(path.relative_to(root).parts) & EXCLUDED_PARTS:
            continue
        if START_HERE_ALIASES.fullmatch(path.name):
            errors.append(
                f"parallel documentation entrypoint is forbidden: {path.relative_to(root)}"
            )
        if CURRENT_STATE_ALIASES.fullmatch(path.name) and path.resolve() != current.resolve():
            errors.append(
                f"parallel current-state entrypoint is forbidden: {path.relative_to(root)}"
            )
    return errors


def validate_current_authorities(root: Path) -> list[str]:
    errors: list[str] = []
    current = (root / "docs/codex/current-state.md").read_text(encoding="utf-8")
    required = (
        "Platform `0.10.0`",
        "Platform `0.10.1`",
        "refactor/platform-0-10-1-non-ui-convergence",
        "Draft PR",
        "Live Write",
    )
    for anchor in required:
        if anchor not in current:
            errors.append(f"current-state.md missing required current fact: {anchor}")
    if "<DRAFT_PR>" in current:
        errors.append("current-state.md still contains the Draft PR placeholder")
    return errors


def validate_repository(root: Path) -> list[str]:
    return sorted(
        validate_entrypoints(root)
        + validate_current_authorities(root)
        + validate_markdown_links(root)
        + validate_portable_documentation(root)
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(root)
    if errors:
        print("Documentation consistency checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Documentation consistency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
