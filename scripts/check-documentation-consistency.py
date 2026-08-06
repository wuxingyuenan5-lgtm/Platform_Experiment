#!/usr/bin/env python3
"""Validate durable active documentation authorities, links and repository paths."""

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
    "docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md",
    "docs/database/README.md",
    "docs/engineering/GIT_WORKFLOW.md",
    "docs/contracts/README.md",
)
CANDIDATE_AUTHORITY_PATHS = (
    "docs/codex/current-state.md",
    "docs/technical/AUTH_RBAC_LIVE_SESSIONS.md",
    "docs/product/PLATFORM_0_10_2_FRONTEND_ACCESS_MATRIX.md",
    "docs/product/ACCEPTANCE_CRITERIA.md",
    "docs/architecture/OWNERSHIP.md",
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
BACKTICK_MARKDOWN_PATTERN = re.compile(r"`(?P<target>[^`\n]+\.md(?:#[^`\s]+)?)`")
FENCED_CODE_PATTERN = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
CURRENT_STATE_ALIASES = re.compile(r"^current[-_]state\.md$", re.IGNORECASE)
START_HERE_ALIASES = re.compile(r"^start[-_]here(?:\.md)?$", re.IGNORECASE)
DELETED_ACTIVE_TREES = re.compile(r"(?:^|/)(?:planning|tasks|projects)/", re.IGNORECASE)
HISTORICAL_CONTEXT = re.compile(
    r"历史|historical|retired|superseded|completed|已完成|已归档|非当前|not current",
    re.IGNORECASE,
)
CURRENT_LEGACY_STATUS = re.compile(
    r"(?:当前阶段|实施计划|适用版本|^#).*?(?:Platform\s+V6|Production\s+Gate|0\.9\.\d+.*Phase|Phase\s*[0-9])",
    re.IGNORECASE,
)
ACTIVE_STATUS_PATTERN = re.compile(
    r"^(?:状态：`active`|Status:\s*active)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
DRAFT_PR_STATUS_PATTERN = re.compile(
    r"状态[^\n]*(?:frozen\s+for\s+)?Draft\s+PR\s*#\d+[^\n]*(?:acceptance)?",
    re.IGNORECASE,
)
CURRENT_STATE_STALE_MARKERS = (
    "Frontend product restoration has not been executed",
    "remains outside the current non-UI scope",
)
CURRENT_STATE_SCOPE_REQUIREMENTS = (
    ("browser access", "浏览器权限", "浏览器访问"),
    ("frontend product restoration", "product restoration", "前端产品恢复", "前端恢复"),
)
AUTH_CONTRACT_PATH = "docs/technical/AUTH_RBAC_LIVE_SESSIONS.md"
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


def markdown_paths(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.md"))
        if not (set(path.relative_to(root).parts) & EXCLUDED_PARTS)
    ]


def markdown_without_examples(content: str) -> str:
    return HTML_COMMENT_PATTERN.sub("", FENCED_CODE_PATTERN.sub("", content))


def candidate_version(root: Path) -> str:
    version_path = root / "VERSION"
    if not version_path.is_file():
        return ""
    return version_path.read_text(encoding="utf-8").strip()


def candidate_authority_paths(root: Path) -> list[Path]:
    return [root / relative for relative in CANDIDATE_AUTHORITY_PATHS]


def is_active_authority(root: Path, path: Path, content: str) -> bool:
    relative = path.relative_to(root).as_posix()
    if relative.startswith("platform-web/docs/archive/"):
        return False
    if relative in REQUIRED_ENTRYPOINTS:
        return True
    header = "\n".join(content.splitlines()[:20])
    return ACTIVE_STATUS_PATTERN.search(header) is not None


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
    if path_text.startswith("docs/") and relative_source.startswith("platform-web/docs/"):
        root_candidate = (root / path_text).resolve()
        if root_candidate.exists():
            return root_candidate
        return (root / "platform-web" / path_text).resolve()
    if path_text.startswith(("docs/", "tasks/", "projects/", "platform-web/", "README.md", "AGENTS.md")):
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
                errors.append(f"{relative_source}: local Markdown target escapes repository: {target}")
                continue
            if not candidate.exists():
                errors.append(f"{relative_source}: local Markdown target does not exist: {target}")
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
            if "/" not in path_part and not path_part.startswith(("README.md", "AGENTS.md")):
                continue
            candidate = resolve_repository_target(root, source, target)
            if candidate is None:
                continue
            try:
                candidate.relative_to(root)
            except ValueError:
                errors.append(f"{relative_source}: backticked Markdown path escapes repository: {target}")
                continue
            if not candidate.exists():
                errors.append(f"{relative_source}: backticked repository Markdown path does not exist: {target}")
    return sorted(errors)


def validate_active_status(root: Path, active_paths: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for source in sorted(active_paths):
        relative = source.relative_to(root).as_posix()
        content = markdown_without_examples(source.read_text(encoding="utf-8"))
        for line_number, line in enumerate(content.splitlines(), start=1):
            if DELETED_ACTIVE_TREES.search(line):
                errors.append(f"{relative}:{line_number}: active document references a retired planning/task/project path")
            if CURRENT_LEGACY_STATUS.search(line) and not HISTORICAL_CONTEXT.search(line):
                errors.append(f"{relative}:{line_number}: old V6/Production Gate/phase text is presented as current")
    return sorted(errors)


def validate_candidate_documentation(
    root: Path,
    paths: Iterable[Path] | None = None,
) -> list[str]:
    errors: list[str] = []
    version = candidate_version(root)
    if not version:
        errors.append("VERSION is missing or empty for candidate documentation validation")

    candidate_paths = list(paths) if paths is not None else candidate_authority_paths(root)
    for source in candidate_paths:
        if not source.is_file():
            errors.append(
                "candidate documentation authority is missing: "
                f"{source.relative_to(root).as_posix()}"
            )

    current_path = root / "docs/codex/current-state.md"
    current = current_path.read_text(encoding="utf-8") if current_path.is_file() else ""
    for marker in CURRENT_STATE_STALE_MARKERS:
        if marker in current:
            errors.append(f"docs/codex/current-state.md contains stale candidate status: {marker}")
    current_folded = current.casefold()
    for alternatives in CURRENT_STATE_SCOPE_REQUIREMENTS:
        if not any(alternative.casefold() in current_folded for alternative in alternatives):
            errors.append(
                f"docs/codex/current-state.md must describe Platform {version} candidate scope: "
                + " or ".join(alternatives)
            )

    auth_path = root / AUTH_CONTRACT_PATH
    if auth_path.is_file() and "verification pending" in auth_path.read_text(encoding="utf-8").casefold():
        errors.append(f"{AUTH_CONTRACT_PATH} contains stale verification status: verification pending")

    for source in sorted(path for path in candidate_paths if path.is_file()):
        relative = source.relative_to(root).as_posix()
        content = markdown_without_examples(source.read_text(encoding="utf-8"))
        for line_number, line in enumerate(content.splitlines(), start=1):
            if DRAFT_PR_STATUS_PATTERN.search(line):
                errors.append(
                    f"{relative}:{line_number}: candidate status must not persist a Draft PR number"
                )
    return sorted(set(errors))


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
    current = root / "docs/codex/current-state.md"
    for path in sorted(root.rglob("*")):
        if not path.is_file() or set(path.relative_to(root).parts) & EXCLUDED_PARTS:
            continue
        if START_HERE_ALIASES.fullmatch(path.name):
            errors.append(f"parallel documentation entrypoint is forbidden: {path.relative_to(root)}")
        if CURRENT_STATE_ALIASES.fullmatch(path.name) and path.resolve() != current.resolve():
            errors.append(f"parallel current-state entrypoint is forbidden: {path.relative_to(root)}")
    return errors


def validate_current_authority(root: Path) -> list[str]:
    current = (root / "docs/codex/current-state.md").read_text(encoding="utf-8")
    version = candidate_version(root)
    errors: list[str] = []
    required = (
        "Stable baseline: Platform `0.10.0`",
        f"Current candidate target: Platform `{version}`",
        "Platform Live Write and Runtime Live Write remain disabled by default",
        "Candidate validation does not mean the candidate is released, deployed or production-ready",
        "remain unverified",
        "must not be assumed",
        "具体活动分支、HEAD和PR状态属于易变Git/GitHub事实",
    )
    for anchor in required:
        if anchor not in current:
            errors.append(f"current-state.md missing durable authority fact: {anchor}")
    volatile = (
        "Active branch:",
        "Current branch:",
        "Active review:",
        "Draft PR",
        "Open/Unmerged",
    )
    for marker in volatile:
        if marker in current:
            errors.append(f"current-state.md must not persist volatile Git/GitHub fact: {marker}")
    if re.search(r"<[A-Z][A-Z0-9_]+>", current):
        errors.append("current-state.md contains an unresolved placeholder")
    return errors


def validate_repository(root: Path) -> list[str]:
    all_paths = markdown_paths(root)
    active_paths = [
        path
        for path in all_paths
        if is_active_authority(root, path, path.read_text(encoding="utf-8"))
    ]
    return sorted(
        validate_entrypoints(root)
        + validate_current_authority(root)
        + validate_candidate_documentation(root)
        + validate_markdown_links(root, all_paths)
        + validate_backticked_paths(root, active_paths)
        + validate_active_status(root, active_paths)
        + validate_portable_documentation(root, all_paths)
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
