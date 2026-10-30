#!/usr/bin/env python3
"""Validate durable active documentation authorities, links and repository paths."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote, urlsplit

REQUIRED_ENTRYPOINTS = (
    "README.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/PROJECT.md",
    "docs/BASELINE.md",
    "docs/architecture/SYSTEM_MAP.md",
    "docs/architecture/OWNERSHIP.md",
    "docs/operations/RUNBOOK.md",
    "docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md",
    "docs/database/README.md",
    "docs/engineering/GIT_WORKFLOW.md",
    "docs/contracts/README.md",
)
EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".codex",
        ".codex-cleanup-quarantine",
        ".workbuddy",
        ".mypy_cache",
        ".pytest_cache",
        ".pytest-basetemp",
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
        "tmp",
        "vendor",
    }
)
EXTERNAL_SCHEMES = frozenset({"data", "http", "https", "javascript", "mailto", "tel"})
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]\n]*\]\((?P<target>[^)\n]+)\)")
BACKTICK_MARKDOWN_PATTERN = re.compile(r"`(?P<target>[^`\n]+\.md(?:#[^`\s]+)?)`")
FENCED_CODE_PATTERN = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
CURRENT_STATE_ALIASES = re.compile(r"^current[-_]state\.md$", re.IGNORECASE)
START_HERE_ALIASES = re.compile(r"^start[-_]here(?:\.md)?$", re.IGNORECASE)
HISTORICAL_CONTEXT = re.compile(
    r"历史|过时|已退役|已替代|已完成|已归档|非当前|historical|retired|superseded|completed|archived|not current",
    re.IGNORECASE,
)
ACTIVE_STATUS_PATTERN = re.compile(
    r"^(?:状态：`?active`?|Status:\s*active)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
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
        re.compile(
            r"/Users/(?!<user>(?:/|$)|username(?:/|$)|\$\{?USER\}?(?:/|$))[^/\s`]+(?:/|$)"
        ),
    ),
    (
        "Linux user home",
        re.compile(
            r"/home/(?!<user>(?:/|$)|username(?:/|$)|\$\{?USER\}?(?:/|$))[^/\s`]+(?:/|$)"
        ),
    ),
)


def markdown_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory, directory_names, file_names in root.walk():
        directory_names[:] = [
            name for name in directory_names if name not in EXCLUDED_PARTS
        ]
        paths.extend(directory / name for name in file_names if name.endswith(".md"))
    return sorted(paths)


def markdown_without_examples(content: str) -> str:
    return HTML_COMMENT_PATTERN.sub("", FENCED_CODE_PATTERN.sub("", content))


def candidate_version(root: Path) -> str:
    version_path = root / "VERSION"
    if not version_path.is_file():
        return ""
    return version_path.read_text(encoding="utf-8").strip()


def next_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return version
    major, minor, patch = (int(part) for part in parts)
    return f"{major}.{minor}.{patch + 1}"


def is_active_authority(root: Path, path: Path, content: str) -> bool:
    relative = path.relative_to(root).as_posix()
    if relative in REQUIRED_ENTRYPOINTS:
        return True
    if relative.startswith("docs/workstreams/"):
        return path.resolve() in active_workstream_paths(root)
    header = "\n".join(content.splitlines()[:20])
    return ACTIVE_STATUS_PATTERN.search(header) is not None


def active_workstream_paths(root: Path) -> set[Path]:
    """Use the existing cockpit links, without a second registry or status syntax."""
    project = root / "docs/PROJECT.md"
    if not project.is_file():
        return set()
    content = markdown_without_examples(project.read_text(encoding="utf-8"))
    stage_root = (root / "docs/workstreams").resolve()
    paths: set[Path] = set()
    for match in MARKDOWN_LINK_PATTERN.finditer(content):
        target = markdown_link_target(match.group("target"))
        if target is None:
            continue
        candidate = resolve_repository_target(root, project, target)
        if candidate and candidate.parent == stage_root and candidate.suffix == ".md":
            paths.add(candidate)
    return paths


def validate_workstreams(root: Path) -> list[str]:
    declared = active_workstream_paths(root)
    present = {path.resolve() for path in (root / "docs/workstreams").glob("*.md")}
    errors = [
        f"{path.relative_to(root.resolve()).as_posix()}: workstream is not linked "
        "from PROJECT.md"
        for path in sorted(present - declared)
    ]
    errors.extend(
        f"docs/PROJECT.md: declared workstream is missing: "
        f"{path.relative_to(root.resolve()).as_posix()}"
        for path in sorted(declared - present)
    )
    return errors


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


def resolve_repository_target(root: Path, source: Path, target: str) -> Path | None:
    path_text = unquote(urlsplit(target).path).split("#", 1)[0]
    if not path_text:
        return None
    if path_text.startswith("/"):
        return (root / path_text.lstrip("/")).resolve()
    relative_source = source.resolve().relative_to(root.resolve()).as_posix()
    if path_text.startswith("docs/") and relative_source.startswith(
        "platform-web/docs/"
    ):
        root_candidate = (root / path_text).resolve()
        if root_candidate.exists():
            return root_candidate
        return (root / "platform-web" / path_text).resolve()
    if path_text.startswith(
        ("docs/", "tasks/", "projects/", "platform-web/", "README.md", "AGENTS.md")
    ):
        return (root / path_text).resolve()
    return (source.parent / path_text).resolve()


def validate_markdown_links(root: Path, paths: Iterable[Path]) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    for source in sorted(paths):
        content = markdown_without_examples(source.read_text(encoding="utf-8"))
        relative_source = source.resolve().relative_to(root).as_posix()
        for match in MARKDOWN_LINK_PATTERN.finditer(content):
            target = markdown_link_target(match.group("target"))
            if target is None:
                continue
            candidate = resolve_repository_target(root, source, target)
            if candidate is None:
                continue
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


def validate_backticked_paths(root: Path, active_paths: Iterable[Path]) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    for source in sorted(active_paths):
        content = markdown_without_examples(source.read_text(encoding="utf-8"))
        relative_source = source.resolve().relative_to(root).as_posix()
        for match in BACKTICK_MARKDOWN_PATTERN.finditer(content):
            target = match.group("target")
            path_part = target.split("#", 1)[0]
            if any(character in target for character in "*?{}<>"):
                continue
            if "/" not in path_part and not path_part.startswith(
                ("README.md", "AGENTS.md")
            ):
                continue
            candidate = resolve_repository_target(root, source, target)
            if candidate is None:
                continue
            try:
                candidate.relative_to(root)
            except ValueError:
                errors.append(
                    f"{relative_source}: backticked Markdown path escapes repository: {target}"
                )
                continue
            if not candidate.exists():
                errors.append(
                    f"{relative_source}: backticked repository Markdown path does not exist: {target}"
                )
    return sorted(errors)


def validate_portable_documentation(root: Path, paths: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for source in sorted(paths):
        relative_source = source.relative_to(root).as_posix()
        content = markdown_without_examples(source.read_text(encoding="utf-8"))
        for label, pattern in WORKSTATION_PATH_PATTERNS:
            for match in pattern.finditer(content):
                errors.append(
                    f"{relative_source}: workstation-specific {label} path is forbidden: {match.group(0)}"
                )
    return sorted(errors)


def validate_entrypoints(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_ENTRYPOINTS:
        if not (root / relative).is_file():
            errors.append(f"required documentation entrypoint is missing: {relative}")
    current = root / "docs/BASELINE.md"
    for path in markdown_paths(root):
        if START_HERE_ALIASES.fullmatch(path.name):
            errors.append(
                f"parallel documentation entrypoint is forbidden: {path.relative_to(root)}"
            )
        if (
            CURRENT_STATE_ALIASES.fullmatch(path.name)
            and path.resolve() != current.resolve()
        ):
            errors.append(
                f"parallel current-state entrypoint is forbidden: {path.relative_to(root)}"
            )
    return errors


def validate_project_cockpit(root: Path) -> list[str]:
    project_path = root / "docs/PROJECT.md"
    if not project_path.is_file():
        return []  # The entrypoint check reports the missing file.
    project = project_path.read_text(encoding="utf-8")
    errors: list[str] = []
    version = candidate_version(root)
    for line in project.splitlines():
        match = re.search(r"Platform\s+`?(\d+\.\d+\.\d+)`?\s*(?:候选|candidate)", line)
        if (
            match
            and not HISTORICAL_CONTEXT.search(line)
            and match.group(1) not in {version, next_patch_version(version)}
        ):
            errors.append(
                f"PROJECT.md contains stale candidate version: {match.group(1)}"
            )
    return errors


def migration_review_notes(root: Path) -> list[str]:
    """Prompt a content review without imposing a heading format or blocking work."""
    source = root / "platform-api/app/schema_migrations.py"
    guide = root / "docs/database/README.md"
    if not source.is_file() or not guide.is_file():
        return []  # Missing required entrypoints are reported separately.
    versions = [
        keyword.value.value
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Migration"
        for keyword in node.keywords
        if keyword.arg == "version"
        and isinstance(keyword.value, ast.Constant)
        and type(keyword.value.value) is int
    ]
    if not versions:
        return []
    latest = max(versions)
    mentions = re.findall(
        r"(?:迁移(?:版本)?|migration|schema(?:\s+version)?|version)\s*[:：`v ]*(\d+)",
        guide.read_text(encoding="utf-8"),
        re.IGNORECASE | re.MULTILINE,
    )
    documented = {int(value) for value in mentions}
    if latest not in documented:
        return [f"review whether migration {latest} needs a database-guide update"]
    return []


def validate_repository(root: Path) -> list[str]:
    all_paths = markdown_paths(root)
    active_paths = [
        path
        for path in all_paths
        if is_active_authority(root, path, path.read_text(encoding="utf-8"))
    ]
    return sorted(
        validate_entrypoints(root)
        + validate_project_cockpit(root)
        + validate_workstreams(root)
        + validate_markdown_links(root, all_paths)
        + validate_backticked_paths(root, active_paths)
        + validate_portable_documentation(root, all_paths)
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(root)
    for note in migration_review_notes(root):
        print(f"Documentation review note: {note}")
    if errors:
        print("Documentation consistency checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Documentation consistency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
