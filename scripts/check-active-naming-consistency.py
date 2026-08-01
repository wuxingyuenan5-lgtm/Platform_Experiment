#!/usr/bin/env python3
"""Reject legacy product naming from the active Platform surface."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = Path("config/legacy-naming-allowlist.json")
ALLOWED_CATEGORIES = {
    "external-production-compatibility",
    "historical-release",
    "third-party-attribution",
    "compatibility-test",
    "real-business-term",
}

SCAN_ROOTS = (
    "README.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/codex",
    "docs/architecture",
    "docs/contracts",
    "docs/operations",
    "docs/database",
    "docs/technical",
    "docs/product",
    "00-人工可读目录",
    "platform-web/src",
    "platform-web/package.json",
    "platform-web/internal",
    "platform-web/index.html",
    "platform-web/.env.platform.example",
    "platform-web/vite.config.ts",
    "platform-web/README.md",
    "platform-web/README.zh-CN.md",
    "platform-web/playwright.hedge-board.config.ts",
    "platform-web/playwright.platform-visual.config.ts",
    "platform-web/playwright.user-system.config.ts",
    "platform-api/app",
    "platform-api/AGENTS.md",
    "platform-api/README.md",
    "platform-api/pyproject.toml",
    "platform-api/.env.example",
    "platform-api/scripts",
    "platform-api/tests",
    "execution-runtime/app",
    "execution-runtime/README.md",
    "execution-runtime/pyproject.toml",
    "execution-runtime/.env.live.example",
    "execution-runtime/tests",
    "scripts",
    ".github/workflows",
    ".env.example",
)
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".less",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "archive",
    "artifacts",
    "audit",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "outputs",
    "playwright-report",
    "projects",
    "releases",
    "tasks",
    "test-results",
    "vendor",
}
EXCLUDED_NAME_TOKENS = ("PLAN", "HANDOFF", "AUDIT", "SUPERSEDED", "RELEASE_NOTE")
EXCLUDED_EXACT_PATHS = {
    "config/legacy-naming-allowlist.json",
    "scripts/check-active-naming-consistency.py",
}

FORBIDDEN_PATTERNS = (
    ("RTA", re.compile(r"(?<![A-Za-z0-9_])RTA(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("rta-office", re.compile(r"rta-office", re.IGNORECASE)),
    ("rta_", re.compile(r"rta_", re.IGNORECASE)),
    ("rta-", re.compile(r"rta-", re.IGNORECASE)),
    ("old private-fund product name", re.compile(r"私募交易风控平台|私募风控平台")),
    ("admin-risk", re.compile(r"admin-risk", re.IGNORECASE)),
    ("platform-backend", re.compile(r"platform-backend", re.IGNORECASE)),
    ("risk-control-platform", re.compile(r"risk-control-platform", re.IGNORECASE)),
    ("risk-web", re.compile(r"risk-web", re.IGNORECASE)),
    ("old service name", re.compile(r"Platform Backend")),
    (
        "old runtime service name",
        re.compile(
            r"(?<!Platform )(?<!Variable-Global )(?<!Variable Global )Execution Runtime",
            re.IGNORECASE,
        ),
    ),
    ("old project name", re.compile(r"Platform Experiment")),
    ("legacy VG environment variable", re.compile(r"\bVG_[A-Z0-9_]+\b")),
)


class AllowlistEntry(NamedTuple):
    pattern: str
    path: str
    category: str
    reason: str
    owner: str
    removal_condition: str

    @property
    def regex(self) -> re.Pattern[str]:
        return re.compile(self.pattern, re.IGNORECASE)


def _iter_paths(root: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    for relative in SCAN_ROOTS:
        candidate = root / relative
        candidates = [candidate] if candidate.is_file() else candidate.rglob("*") if candidate.is_dir() else []
        for path in candidates:
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            rel = path.relative_to(root).as_posix()
            if rel in EXCLUDED_EXACT_PATHS:
                continue
            if set(path.relative_to(root).parts) & EXCLUDED_PARTS:
                continue
            if any(token in path.name.upper() for token in EXCLUDED_NAME_TOKENS):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".env.example", ".env.live.example"}:
                continue
            yield path


LEGAL_BRAND_PATTERNS = {
    "全球变量金融平台": re.compile(r"全球变量金融平台"),
    "Variable-Global": re.compile(r"Variable-Global", re.IGNORECASE),
    "Variable Global": re.compile(r"Variable Global", re.IGNORECASE),
}


def count_legal_brand_hits(root: Path = ROOT) -> dict[str, int]:
    counts = {label: 0 for label in LEGAL_BRAND_PATTERNS}
    for path in _iter_paths(root):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in LEGAL_BRAND_PATTERNS.items():
            counts[label] += sum(1 for _ in pattern.finditer(content))
    return counts


def load_allowlist(root: Path = ROOT) -> list[AllowlistEntry]:
    path = root / ALLOWLIST_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("legacy naming allowlist must contain an entries list")
    entries: list[AllowlistEntry] = []
    for raw in raw_entries:
        required = {"pattern", "path", "category", "reason", "owner", "removalCondition"}
        if not isinstance(raw, dict) or set(raw) != required:
            raise ValueError(f"invalid allowlist entry fields: {raw}")
        path_value = str(raw["path"])
        if any(marker in path_value for marker in ("*", "?", "[", "]")):
            raise ValueError(f"allowlist path must be exact: {path_value}")
        category = str(raw["category"])
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"invalid allowlist category: {category}")
        for field in ("reason", "owner", "removalCondition"):
            if not str(raw[field]).strip():
                raise ValueError(f"allowlist {field} must be non-empty: {path_value}")
        re.compile(str(raw["pattern"]), re.IGNORECASE)
        entries.append(
            AllowlistEntry(
                pattern=str(raw["pattern"]),
                path=path_value,
                category=category,
                reason=str(raw["reason"]),
                owner=str(raw["owner"]),
                removal_condition=str(raw["removalCondition"]),
            )
        )
    return entries


def _is_allowed(relative: str, value: str, entries: Iterable[AllowlistEntry]) -> bool:
    return any(entry.path == relative and entry.regex.search(value) for entry in entries)


def scan_repository(root: Path = ROOT, entries: list[AllowlistEntry] | None = None) -> list[str]:
    allowlist = load_allowlist(root) if entries is None else entries
    errors: list[str] = []
    for path in _iter_paths(root):
        relative = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(content):
                value = match.group(0)
                if _is_allowed(relative, value, allowlist):
                    continue
                line = content.count("\n", 0, match.start()) + 1
                errors.append(f"{relative}:{line}: forbidden {label}: {value}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        errors = scan_repository(args.root.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Active naming consistency check failed: {exc}")
        return 1
    if errors:
        print("Active naming consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    counts = count_legal_brand_hits(args.root.resolve())
    print("Active Platform naming is consistent; Legacy identifiers are precisely allowlisted.")
    print(
        "Formal brand protection: "
        f"全球变量金融平台={counts['全球变量金融平台']}, "
        f"Variable-Global={counts['Variable-Global']}, "
        f"Variable Global={counts['Variable Global']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
