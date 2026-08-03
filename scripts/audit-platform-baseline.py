#!/usr/bin/env python3
"""Collect a reproducible Platform 0.9.2 repository baseline.

The collector is intentionally read-only. It uses only the Python standard
library and git metadata already available in the checkout. Outputs are written
outside source directories so they can be uploaded as CI artifacts and compared
again after each optimization phase.
"""

from __future__ import annotations

import ast
import collections
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get("PLATFORM_AUDIT_OUTPUT", ROOT / "audit-output"))

SKIP_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".pnpm-store",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "htmlcov",
    "playwright-report",
    "test-results",
    "__pycache__",
    ".venv",
    "venv",
    "audit-output",
}

TEXT_SUFFIXES = {
    ".py",
    ".pyi",
    ".js",
    ".cjs",
    ".mjs",
    ".ts",
    ".tsx",
    ".vue",
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".scss",
    ".less",
    ".sql",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
    ".env",
}

CODE_SUFFIXES = {
    ".py",
    ".pyi",
    ".js",
    ".cjs",
    ".mjs",
    ".ts",
    ".tsx",
    ".vue",
    ".html",
    ".css",
    ".scss",
    ".less",
    ".sql",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
}

DOC_SUFFIXES = {".md", ".txt"}

LEGACY_TERMS = [
    "RTA",
    "私募",
    "vben",
    "vben-admin",
    "vue-vben-admin",
    "anncwb",
    "platform-web",
    "risk-control",
    "Platform_Experiment",
]

GENERIC_TEMPLATE_TERMS = ["template", "demo", "example"]

PROTECTED_TERMS = [
    "csrf",
    "origin",
    "last ceo",
    "decimal",
    "financial fact",
    "kill switch",
    "two-person",
    "two person",
    "live write",
    "idempot",
    "fok",
    "postonly",
    "post_only",
    "tp/sl",
    "result unknown",
    "reconciliation",
    "last known good",
    "stale",
    "no_data",
    "tls",
]

IGNORE_PATTERNS = {
    "eslint_disable": re.compile(r"eslint-disable"),
    "typescript_ignore": re.compile(r"@ts-ignore|@ts-nocheck"),
    "python_noqa": re.compile(r"#\s*noqa"),
    "python_type_ignore": re.compile(r"#\s*type:\s*ignore"),
    "coverage_ignore": re.compile(r"pragma:\s*no cover"),
    "lint_file_ignore": re.compile(r"ruff:\s*noqa|flake8:\s*noqa"),
}

CURRENT_STATE_NAME_RE = re.compile(
    r"(?:current[-_ ]?state|current[-_ ]?context|status|active[-_ ]?task|handoff)",
    re.IGNORECASE,
)

IMPORT_TS_RE = re.compile(
    r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]"
)

URL_RE = re.compile(r"https?://[^\s)>'\"]+")

TASK_DEFINITIONS: dict[str, dict[str, list[str]]] = {
    "modify_page_style": {
        "path": ["platform-web/src/views/", "platform-web/src/components/", "platform-web/src/styles/"],
        "terms": ["style", "layout", "responsive", "design token"],
    },
    "modify_research_field": {
        "path": [
            "platform-web/src/views/hedgeBoard/",
            "platform-web/src/api/hedgeResearch",
            "platform-api/app/research_",
            "platform-api/app/a_share_",
            "platform-api/tests/test_research",
            "platform-api/tests/test_a_share",
            "docs/technical/RESEARCH",
        ],
        "terms": ["research", "provider", "last known good", "shenwan", "申万"],
    },
    "modify_user_permission": {
        "path": [
            "platform-web/src/access/",
            "platform-web/src/router/guard/",
            "platform-web/src/store/modules/user",
            "platform-api/app/auth",
            "platform-api/app/user_authority",
            "platform-api/app/user_permission",
            "platform-api/app/user_admin_policy",
            "platform-api/tests/test_auth",
            "platform-api/tests/test_user_permission",
            "platform-api/tests/test_user_target_scope",
            "docs/technical/AUTH",
            "docs/technical/USER_SYSTEM",
        ],
        "terms": ["permission", "role", "csrf", "origin", "last ceo"],
    },
    "modify_api_contract": {
        "path": [
            "platform-web/src/api/",
            "platform-api/app/",
            "platform-api/tests/",
            "docs/technical/",
        ],
        "terms": ["route", "schema", "contract", "client"],
    },
    "modify_trading_display": {
        "path": [
            "platform-web/src/views/strategy/",
            "platform-web/src/api/platform/crossSpread",
            "platform-api/app/cross_spread",
            "execution-runtime/app/",
            "platform-api/tests/test_cross_spread",
        ],
        "terms": ["market", "fok", "postonly", "tp/sl", "result unknown"],
    },
    "add_research_provider": {
        "path": [
            "platform-api/app/research_provider",
            "platform-api/app/research_service",
            "platform-api/app/research_cache",
            "platform-api/app/research_data_schema",
            "platform-api/scripts/smoke_research",
            "platform-api/tests/test_research",
            "platform-web/src/api/hedgeResearch",
            "docs/technical/RESEARCH",
            ".github/workflows/research-provider",
        ],
        "terms": ["provider", "ttl", "last known good", "partial", "stale", "error"],
    },
    "fix_browser_e2e": {
        "path": [
            "platform-web/e2e/",
            "platform-web/playwright",
            "platform-web/scripts/verify",
            "platform-api/scripts/seed_",
            ".github/workflows/",
            "docs/operations/",
        ],
        "terms": ["playwright", "fixture", "e2e", "seed"],
    },
}


@dataclass
class FileRecord:
    path: str
    suffix: str
    category: str
    bytes: int
    lines: int
    chars: int
    estimated_tokens: int
    sha256: str


@dataclass
class DependencyRecord:
    manifest: str
    ecosystem: str
    section: str
    name: str
    version: str


def run_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def iter_paths() -> Iterable[Path]:
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = Path(base) / name
            try:
                path.relative_to(OUTPUT)
            except ValueError:
                pass
            else:
                continue
            yield path


def is_text(path: Path) -> bool:
    if path.name.startswith(".env"):
        return True
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in sample


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1", errors="replace")
    except OSError:
        return ""


def category_for(path: Path) -> str:
    suffix = path.suffix.lower()
    rel = path.relative_to(ROOT).as_posix()
    if suffix in DOC_SUFFIXES or rel.startswith("docs/") or rel.startswith("tasks/"):
        return "documentation"
    if "/tests/" in f"/{rel}" or "/e2e/" in f"/{rel}" or path.name.startswith("test_"):
        return "test"
    if rel.startswith(".github/workflows/"):
        return "workflow"
    if suffix in CODE_SUFFIXES:
        return "code"
    if path.name in {"package.json", "pyproject.toml", "pnpm-lock.yaml", "package-lock.json"}:
        return "manifest"
    return "other_text"


def collect_files() -> tuple[list[FileRecord], dict[str, str]]:
    records: list[FileRecord] = []
    contents: dict[str, str] = {}
    for path in iter_paths():
        if not path.is_file() or not is_text(path):
            continue
        rel = path.relative_to(ROOT).as_posix()
        text = read_text(path)
        raw = text.encode("utf-8", errors="replace")
        records.append(
            FileRecord(
                path=rel,
                suffix=path.suffix.lower() or "[none]",
                category=category_for(path),
                bytes=len(raw),
                lines=len(text.splitlines()),
                chars=len(text),
                estimated_tokens=max(1, round(len(text) / 4)),
                sha256=hashlib.sha256(raw).hexdigest(),
            )
        )
        contents[rel] = text
    return records, contents


def top_level(path: str) -> str:
    return path.split("/", 1)[0]


def aggregate(records: list[FileRecord], key: str) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"files": 0, "bytes": 0, "lines": 0, "estimated_tokens": 0}
    )
    for record in records:
        bucket_key = getattr(record, key) if hasattr(record, key) else top_level(record.path)
        bucket = buckets[str(bucket_key)]
        bucket["files"] += 1
        bucket["bytes"] += record.bytes
        bucket["lines"] += record.lines
        bucket["estimated_tokens"] += record.estimated_tokens
    return [
        {key: name, **values}
        for name, values in sorted(
            buckets.items(), key=lambda item: item[1]["lines"], reverse=True
        )
    ]


def parse_dependencies(contents: dict[str, str]) -> list[DependencyRecord]:
    dependencies: list[DependencyRecord] = []
    for path, text in contents.items():
        if path.endswith("package.json"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                for name, version in sorted((data.get(section) or {}).items()):
                    dependencies.append(
                        DependencyRecord(path, "node", section, str(name), str(version))
                    )
        elif path.endswith("pyproject.toml"):
            current_section = ""
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    current_section = stripped.strip("[]")
                    continue
                match = re.match(r"([A-Za-z0-9_.-]+)\s*=\s*['\"]([^'\"]+)['\"]", stripped)
                if match and any(
                    token in current_section.lower()
                    for token in ("dependencies", "poetry.dependencies", "project.optional-dependencies")
                ):
                    dependencies.append(
                        DependencyRecord(path, "python", current_section, match.group(1), match.group(2))
                    )
                if current_section == "project" and stripped.startswith("dependencies"):
                    # Array-form dependencies are collected by quoted entries below.
                    continue
                if current_section.startswith("project"):
                    quoted = re.findall(r"['\"]([A-Za-z0-9_.-]+)(?:[^'\"]*)['\"]", stripped)
                    for item in quoted:
                        if item.lower() not in {"project", "dependencies"}:
                            dependencies.append(
                                DependencyRecord(path, "python", current_section, item, "array-entry")
                            )
    unique: dict[tuple[str, str, str, str], DependencyRecord] = {}
    for item in dependencies:
        unique[(item.manifest, item.section, item.name, item.version)] = item
    return list(unique.values())


def count_terms(contents: dict[str, str], terms: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for term in terms:
        term_re = re.compile(re.escape(term), re.IGNORECASE)
        for path, text in contents.items():
            count = len(term_re.findall(text)) + len(term_re.findall(path))
            if count:
                lines = []
                for index, line in enumerate(text.splitlines(), start=1):
                    if term_re.search(line):
                        lines.append({"line": index, "text": line.strip()[:240]})
                        if len(lines) >= 5:
                            break
                findings.append(
                    {"term": term, "path": path, "count": count, "samples": lines}
                )
    return sorted(findings, key=lambda item: (item["term"].lower(), -item["count"], item["path"]))


def duplicate_files(records: list[FileRecord]) -> list[dict[str, Any]]:
    groups: dict[str, list[FileRecord]] = collections.defaultdict(list)
    for record in records:
        if record.lines >= 4 and record.bytes >= 80:
            groups[record.sha256].append(record)
    return [
        {
            "sha256": digest,
            "files": [item.path for item in group],
            "lines": group[0].lines,
            "bytes_each": group[0].bytes,
        }
        for digest, group in groups.items()
        if len(group) > 1
    ]


def normalized_code_lines(text: str) -> list[str]:
    result: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//", "/*", "*", "<!--")):
            continue
        line = re.sub(r"\s+", " ", line)
        result.append(line)
    return result


def duplicate_blocks(contents: dict[str, str], block_size: int = 10) -> list[dict[str, Any]]:
    index: dict[str, list[tuple[str, int, str]]] = collections.defaultdict(list)
    for path, text in contents.items():
        suffix = Path(path).suffix.lower()
        if suffix not in CODE_SUFFIXES or "/tests/" in f"/{path}" or "/e2e/" in f"/{path}":
            continue
        lines = normalized_code_lines(text)
        for start in range(0, max(0, len(lines) - block_size + 1), block_size):
            block = "\n".join(lines[start : start + block_size])
            if len(block) < 180:
                continue
            digest = hashlib.sha256(block.encode()).hexdigest()
            index[digest].append((path, start + 1, block[:500]))
    results: list[dict[str, Any]] = []
    for digest, occurrences in index.items():
        files = {item[0] for item in occurrences}
        if len(files) > 1:
            results.append(
                {
                    "sha256": digest,
                    "occurrences": [
                        {"path": path, "normalized_line": line, "sample": sample}
                        for path, line, sample in occurrences[:8]
                    ],
                    "distinct_files": len(files),
                }
            )
    return sorted(results, key=lambda item: item["distinct_files"], reverse=True)[:100]


def python_complexity(contents: dict[str, str]) -> list[dict[str, Any]]:
    functions: list[dict[str, Any]] = []
    for path, text in contents.items():
        if not path.endswith(".py"):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                end = getattr(node, "end_lineno", node.lineno)
                branches = sum(
                    isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Match, ast.BoolOp))
                    for child in ast.walk(node)
                )
                functions.append(
                    {
                        "path": path,
                        "name": node.name,
                        "kind": node.__class__.__name__,
                        "start_line": node.lineno,
                        "end_line": end,
                        "lines": end - node.lineno + 1,
                        "branch_nodes": branches,
                    }
                )
    return sorted(functions, key=lambda item: (item["lines"], item["branch_nodes"]), reverse=True)


def ts_imports(contents: dict[str, str]) -> dict[str, Any]:
    edges: list[dict[str, str]] = []
    fan_in: collections.Counter[str] = collections.Counter()
    fan_out: collections.Counter[str] = collections.Counter()
    for path, text in contents.items():
        if Path(path).suffix.lower() not in {".ts", ".tsx", ".js", ".cjs", ".mjs", ".vue"}:
            continue
        for target in IMPORT_TS_RE.findall(text):
            edges.append({"source": path, "target": target})
            fan_out[path] += 1
            fan_in[target] += 1
    return {
        "edge_count": len(edges),
        "top_fan_out": [{"path": path, "count": count} for path, count in fan_out.most_common(50)],
        "top_import_targets": [{"target": path, "count": count} for path, count in fan_in.most_common(50)],
    }


def python_imports(contents: dict[str, str]) -> dict[str, Any]:
    fan_in: collections.Counter[str] = collections.Counter()
    fan_out: collections.Counter[str] = collections.Counter()
    edges: list[dict[str, str]] = []
    for path, text in contents.items():
        if not path.endswith(".py"):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                targets = [node.module or "."]
            for target in targets:
                edges.append({"source": path, "target": target})
                fan_out[path] += 1
                fan_in[target] += 1
    return {
        "edge_count": len(edges),
        "top_fan_out": [{"path": path, "count": count} for path, count in fan_out.most_common(50)],
        "top_import_targets": [{"target": path, "count": count} for path, count in fan_in.most_common(50)],
    }


def git_hotspots() -> list[dict[str, Any]]:
    log = run_git(["log", "--format=", "--name-only", "-n", "500"])
    counter: collections.Counter[str] = collections.Counter(
        line.strip() for line in log.splitlines() if line.strip()
    )
    return [{"path": path, "changes": count} for path, count in counter.most_common(100)]


def workflow_inventory(contents: dict[str, str]) -> list[dict[str, Any]]:
    workflows: list[dict[str, Any]] = []
    for path, text in contents.items():
        if not path.startswith(".github/workflows/") or not path.endswith((".yml", ".yaml")):
            continue
        jobs = len(re.findall(r"^  [A-Za-z0-9_-]+:\s*$", text, re.MULTILINE))
        uses = collections.Counter(re.findall(r"uses:\s*([^\s#]+)", text))
        runs = [line.strip()[5:].strip() for line in text.splitlines() if line.strip().startswith("run:")]
        paths = re.findall(r"^\s+-\s+['\"]?([^'\"\n]+)['\"]?\s*$", text, re.MULTILINE)
        workflows.append(
            {
                "path": path,
                "lines": len(text.splitlines()),
                "job_heading_count": jobs,
                "uses": dict(uses),
                "run_step_count": len(runs),
                "run_samples": runs[:20],
                "path_like_entries": paths[:100],
            }
        )
    return workflows


def current_state_candidates(records: list[FileRecord], contents: dict[str, str]) -> list[dict[str, Any]]:
    candidates = []
    for record in records:
        text = contents[record.path]
        heading_matches = len(re.findall(r"^#{1,3}\s+.*(?:current|当前|状态|context|handoff)", text, re.IGNORECASE | re.MULTILINE))
        if CURRENT_STATE_NAME_RE.search(record.path) or heading_matches:
            candidates.append(
                {
                    "path": record.path,
                    "lines": record.lines,
                    "estimated_tokens": record.estimated_tokens,
                    "matching_headings": heading_matches,
                }
            )
    return sorted(candidates, key=lambda item: item["estimated_tokens"], reverse=True)


def task_contexts(records: list[FileRecord], contents: dict[str, str]) -> list[dict[str, Any]]:
    by_path = {record.path: record for record in records}
    output: list[dict[str, Any]] = []
    for task, definition in TASK_DEFINITIONS.items():
        selected: set[str] = set()
        for path, text in contents.items():
            lowered_path = path.lower()
            if any(fragment.lower() in lowered_path for fragment in definition["path"]):
                selected.add(path)
                continue
            lowered_text = text.lower()
            if any(term.lower() in lowered_text for term in definition["terms"]):
                # Term-only matches are limited to authoritative-looking code/docs to avoid whole-repo noise.
                if path.startswith(("platform-web/", "platform-api/", "execution-runtime/", "docs/technical/", "docs/architecture/", ".github/workflows/")):
                    selected.add(path)
        chosen = sorted(selected)
        output.append(
            {
                "task": task,
                "files": len(chosen),
                "lines": sum(by_path[path].lines for path in chosen),
                "estimated_tokens": sum(by_path[path].estimated_tokens for path in chosen),
                "services": sorted({top_level(path) for path in chosen}),
                "paths": chosen,
            }
        )
    return output


def test_inventory(records: list[FileRecord]) -> dict[str, Any]:
    tests = [record for record in records if record.category == "test"]
    by_service: dict[str, dict[str, int]] = collections.defaultdict(lambda: {"files": 0, "lines": 0})
    for record in tests:
        service = top_level(record.path)
        by_service[service]["files"] += 1
        by_service[service]["lines"] += record.lines
    return {
        "total_files": len(tests),
        "total_lines": sum(item.lines for item in tests),
        "by_service": [{"service": key, **value} for key, value in sorted(by_service.items())],
        "largest": [asdict(item) for item in sorted(tests, key=lambda item: item.lines, reverse=True)[:50]],
    }


def migration_inventory(records: list[FileRecord], contents: dict[str, str]) -> list[dict[str, Any]]:
    results = []
    for record in records:
        path_lower = record.path.lower()
        text_lower = contents[record.path].lower()
        if any(token in path_lower for token in ("migration", "alembic", "schema")) and (
            record.suffix in {".py", ".sql", ".md"}
        ):
            results.append(
                {
                    "path": record.path,
                    "lines": record.lines,
                    "contains_ddl": any(token in text_lower for token in ("create table", "alter table", "drop table")),
                    "contains_version": bool(re.search(r"\bversion\b|revision|migration", text_lower)),
                }
            )
    return sorted(results, key=lambda item: item["lines"], reverse=True)


def docs_with_urls(contents: dict[str, str]) -> list[dict[str, Any]]:
    output = []
    for path, text in contents.items():
        if Path(path).suffix.lower() not in DOC_SUFFIXES:
            continue
        urls = URL_RE.findall(text)
        if urls:
            output.append({"path": path, "url_count": len(urls), "sample": urls[:10]})
    return sorted(output, key=lambda item: item["url_count"], reverse=True)


def markdown_report(data: dict[str, Any]) -> str:
    summary = data["summary"]
    lines = [
        "# Platform 0.9.2 Repository Baseline Audit",
        "",
        f"- Commit: `{data['git']['commit']}`",
        f"- Branch: `{data['git']['branch']}`",
        f"- Collected at: `{data['collected_at']}`",
        f"- Text files: **{summary['text_files']:,}**",
        f"- Code/test/workflow lines: **{summary['engineering_lines']:,}**",
        f"- Documentation lines: **{summary['documentation_lines']:,}**",
        f"- Estimated full text tokens: **{summary['estimated_tokens']:,}**",
        "",
        "## Top-level footprint",
        "",
        "| Directory | Files | Lines | Estimated tokens |",
        "|---|---:|---:|---:|",
    ]
    for item in data["by_top_level"]:
        lines.append(
            f"| `{item['top_level']}` | {item['files']:,} | {item['lines']:,} | {item['estimated_tokens']:,} |"
        )
    lines.extend(["", "## Largest text files", "", "| Path | Category | Lines | Est. tokens |", "|---|---|---:|---:|"])
    for item in data["largest_files"][:50]:
        lines.append(
            f"| `{item['path']}` | {item['category']} | {item['lines']:,} | {item['estimated_tokens']:,} |"
        )
    lines.extend(["", "## Git hotspots", "", "| Path | Changes in last 500 commits |", "|---|---:|"])
    for item in data["git_hotspots"][:50]:
        lines.append(f"| `{item['path']}` | {item['changes']} |")
    lines.extend(["", "## Typical task context baseline", "", "| Task | Files | Lines | Est. tokens | Services |", "|---|---:|---:|---:|---|"])
    for item in data["task_contexts"]:
        lines.append(
            f"| `{item['task']}` | {item['files']} | {item['lines']:,} | {item['estimated_tokens']:,} | {', '.join(item['services'])} |"
        )
    lines.extend(["", "## Naming and template occurrence counts", "", "| Term | Files | Occurrences |", "|---|---:|---:|"])
    grouped: dict[str, tuple[int, int]] = {}
    for item in data["legacy_occurrences"]:
        files, occurrences = grouped.get(item["term"], (0, 0))
        grouped[item["term"]] = (files + 1, occurrences + item["count"])
    for term, (files, occurrences) in grouped.items():
        lines.append(f"| `{term}` | {files} | {occurrences} |")
    lines.extend(["", "## Initial machine findings", ""])
    lines.append(f"- Exact duplicate text groups: **{len(data['duplicate_files'])}**")
    lines.append(f"- Cross-file duplicate code block groups: **{len(data['duplicate_blocks'])}**")
    lines.append(f"- Current-state/context/handoff candidates: **{len(data['current_state_candidates'])}**")
    lines.append(f"- Workflow files: **{len(data['workflows'])}**")
    lines.append(f"- Test files: **{data['tests']['total_files']}** ({data['tests']['total_lines']:,} lines)")
    lines.append(f"- Migration/schema candidates: **{len(data['migrations'])}**")
    lines.append(f"- Dependency declarations: **{len(data['dependencies'])}**")
    lines.extend([
        "",
        "> These are inventory measurements, not automatic refactoring decisions. Human/agent review must distinguish real business concepts, fixtures, history and third-party attribution from template residue.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records, contents = collect_files()
    dependencies = parse_dependencies(contents)
    categories = aggregate(records, "category")
    summary = {
        "text_files": len(records),
        "text_bytes": sum(item.bytes for item in records),
        "text_lines": sum(item.lines for item in records),
        "estimated_tokens": sum(item.estimated_tokens for item in records),
        "engineering_lines": sum(
            item.lines for item in records if item.category in {"code", "test", "workflow"}
        ),
        "documentation_lines": sum(item.lines for item in records if item.category == "documentation"),
    }
    all_legacy_terms = LEGACY_TERMS + GENERIC_TEMPLATE_TERMS
    data: dict[str, Any] = {
        "schema_version": 1,
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git": {
            "commit": run_git(["rev-parse", "HEAD"]),
            "branch": run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "base_hint": os.environ.get("PLATFORM_AUDIT_BASE", ""),
            "status": run_git(["status", "--short"]),
        },
        "summary": summary,
        "by_top_level": aggregate(records, "top_level"),
        "by_category": categories,
        "by_suffix": aggregate(records, "suffix"),
        "largest_files": [asdict(item) for item in sorted(records, key=lambda item: item.lines, reverse=True)[:200]],
        "all_files": [asdict(item) for item in sorted(records, key=lambda item: item.path)],
        "dependencies": [asdict(item) for item in dependencies],
        "legacy_occurrences": count_terms(contents, all_legacy_terms),
        "protected_term_occurrences": count_terms(contents, PROTECTED_TERMS),
        "ignore_directives": {
            name: [
                {"path": path, "count": len(pattern.findall(text))}
                for path, text in contents.items()
                if pattern.search(text)
            ]
            for name, pattern in IGNORE_PATTERNS.items()
        },
        "todo_fixme": count_terms(contents, ["TODO", "FIXME", "HACK", "XXX"]),
        "duplicate_files": duplicate_files(records),
        "duplicate_blocks": duplicate_blocks(contents),
        "python_complexity": python_complexity(contents)[:300],
        "typescript_imports": ts_imports(contents),
        "python_imports": python_imports(contents),
        "git_hotspots": git_hotspots(),
        "workflows": workflow_inventory(contents),
        "current_state_candidates": current_state_candidates(records, contents),
        "task_contexts": task_contexts(records, contents),
        "tests": test_inventory(records),
        "migrations": migration_inventory(records, contents),
        "docs_with_urls": docs_with_urls(contents),
    }

    json_path = OUTPUT / "platform-0.9.2-baseline-audit.json"
    md_path = OUTPUT / "platform-0.9.2-baseline-audit.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(data), encoding="utf-8")

    print(md_path.read_text(encoding="utf-8"))
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
