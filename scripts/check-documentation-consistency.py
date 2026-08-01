#!/usr/bin/env python3
"""Validate canonical architecture ownership and active Markdown links."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
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
    "docs/contracts/README.md",
)
A1_ENTRYPOINTS = REQUIRED_ENTRYPOINTS

REQUIRED_OWNERS = {
    "Platform composition root": "platform-api/app/main.py",
    "Execution API DTOs": "platform-api/app/execution_schemas.py",
    "Platform order submission orchestration": "platform-api/app/trade_command_execution.py",
    "Member holding pure valuation": "platform-api/app/member_holding_valuation.py",
    "EOD Reconciliation public DTOs": "platform-api/app/eod_reconciliation_schemas.py",
    "EOD report and review policy": "platform-api/app/eod_reconciliation_policy.py",
    "EOD Reconciliation persistence": "platform-api/app/eod_reconciliation_repository.py",
    "EOD Reconciliation Service": "platform-api/app/eod_reconciliation_service.py",
    "EOD Reconciliation facade": "platform-api/app/eod_reconciliation.py",
    "EOD operational gate coordination": "platform-api/app/eod_policy.py",
    "Venue Reconciliation public DTOs": "platform-api/app/venue_reconciliation_schemas.py",
    "Venue Reconciliation difference policy": "platform-api/app/venue_reconciliation_policy.py",
    "Venue Reconciliation persistence": "platform-api/app/venue_reconciliation_repository.py",
    "Venue Reconciliation Runtime client": "platform-api/app/venue_reconciliation_runtime_client.py",
    "Venue Reconciliation Service": "platform-api/app/venue_reconciliation_service.py",
    "Venue Reconciliation facade": "platform-api/app/venue_reconciliation.py",
    "Operational fill projection": "platform-api/app/trading.py",
    "Position calculation policy": "platform-api/app/position_math.py",
    "FinancialFact public DTOs": "platform-api/app/financial_fact_schemas.py",
    "FinancialFact normalization": "platform-api/app/financial_fact_normalization.py",
    "FinancialFact persistence": "platform-api/app/financial_fact_repository.py",
    "Formal projection calculations": "platform-api/app/financial_projection_service.py",
    "FinancialFact API orchestration": "platform-api/app/financial_facts.py",
    "SQLite connection": "platform-api/app/database_connection.py",
    "Core database bootstrap": "platform-api/app/database_bootstrap.py",
    "Fixed reference Seeds": "platform-api/app/database_seeds.py",
    "Database compatibility facade": "platform-api/app/database.py",
    "Migration ledger": "platform-api/app/schema_migrations.py",
    "Runtime journal": "execution-runtime/app/journal.py",
    "Platform execution exposure": "platform-api/app/execution_exposure.py",
    "Durable Agent rules": "AGENTS.md",
    "Agent context loading": "docs/codex/context-map.md",
    "Current engineering truth": "docs/codex/current-state.md",
    "Architecture ownership": "docs/architecture/OWNERSHIP.md",
    "Workstream enforcement": "scripts/check-workstream.py",
}

DOCUMENT_CATALOG_REFERENCES = (
    "AGENTS.md",
    "README.md",
    "docs/README.md",
    "docs/codex/context-map.md",
    "docs/codex/current-state.md",
    "docs/contracts/README.md",
)

STALE_CONTEXT_SNIPPETS = (
    "Formal accounting authority: `platform-api/app/financial_facts.py`",
    "Formal accounting authority: platform-api/app/financial_facts.py",
)

EXCLUDED_MARKDOWN_PARTS = frozenset(
    {
        ".git",
        ".venv",
        "archive",
        "audit",
        "dist",
        "node_modules",
        "outputs",
        "vendor",
    }
)
EXTERNAL_LINK_SCHEMES = frozenset(
    {"data", "http", "https", "javascript", "mailto", "tel"}
)
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]\n]*\]\((?P<target>[^)\n]+)\)")
FENCED_CODE_PATTERN = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
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


def validate_owner_catalog(
    root: Path,
    ownership: str,
    required_owners: Mapping[str, str] = REQUIRED_OWNERS,
) -> list[str]:
    """Validate canonical owner rows and the repository paths they name."""

    errors: list[str] = []
    for boundary, owner_path in required_owners.items():
        expected_row = f"| {boundary} | `{owner_path}` |"
        if expected_row not in ownership:
            errors.append(f"ownership catalog missing canonical mapping: {boundary} -> {owner_path}")
        if not (root / owner_path).exists():
            errors.append(f"canonical owner path does not exist: {owner_path}")
    return errors


def validate_context_map(context: str) -> list[str]:
    """Reject obsolete Agent-context ownership shortcuts."""

    return [
        f"stale Agent context ownership statement: {stale}"
        for stale in STALE_CONTEXT_SNIPPETS
        if stale in context
    ]


def active_markdown_paths(root: Path) -> list[Path]:
    """Return active Markdown files while excluding history and generated trees."""

    return [
        path
        for path in sorted(root.rglob("*.md"))
        if not (set(path.relative_to(root).parts) & EXCLUDED_MARKDOWN_PARTS)
    ]


def markdown_without_examples(content: str) -> str:
    """Remove fenced examples and comments before validating maintained prose."""

    return HTML_COMMENT_PATTERN.sub("", FENCED_CODE_PATTERN.sub("", content))


def markdown_link_target(raw_target: str) -> str | None:
    """Return a local link target or ``None`` when the link is intentionally ignored."""

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
    if urlsplit(target).scheme.lower() in EXTERNAL_LINK_SCHEMES:
        return None
    return target


def validate_markdown_links(
    root: Path,
    markdown_paths: Iterable[Path] | None = None,
) -> list[str]:
    """Validate local file/directory targets in active Markdown documents."""

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
    """Reject real workstation home paths from maintained Markdown prose."""

    root = root.resolve()
    paths = active_markdown_paths(root) if markdown_paths is None else sorted(markdown_paths)
    errors: list[str] = []

    for source in paths:
        if not source.is_file():
            continue
        relative_source = source.resolve().relative_to(root).as_posix()
        content = markdown_without_examples(source.read_text(encoding="utf-8"))
        for label, pattern in WORKSTATION_PATH_PATTERNS:
            match = pattern.search(content)
            if match is not None:
                errors.append(
                    f"{relative_source}: workstation-specific {label} path is forbidden: "
                    f"{match.group(0)}"
                )

    return sorted(errors)


def normalized_paragraphs(content: str) -> set[str]:
    """Return substantive prose paragraphs for simple exact-duplication checks."""

    content = markdown_without_examples(content)
    paragraphs: set[str] = set()
    for raw in re.split(r"\n\s*\n", content):
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines or any(line.startswith(("#", "|", "- ", "* ", ">")) for line in lines):
            continue
        paragraph = " ".join(lines)
        if len(paragraph) >= 160:
            paragraphs.add(paragraph)
    return paragraphs


def validate_a1_hierarchy(root: Path) -> list[str]:
    """Validate the controlled A1 set and reject obvious duplicated authority prose."""

    errors: list[str] = []
    if len(A1_ENTRYPOINTS) < 8 or len(A1_ENTRYPOINTS) > 10:
        errors.append(f"A1 entrypoint count must remain between 8 and 10: {len(A1_ENTRYPOINTS)}")

    owners: dict[str, str] = {}
    for relative in A1_ENTRYPOINTS:
        path = root / relative
        if not path.is_file():
            continue
        for paragraph in normalized_paragraphs(path.read_text(encoding="utf-8")):
            previous = owners.get(paragraph)
            if previous is not None:
                errors.append(f"A1 documents duplicate a substantive paragraph: {previous} and {relative}")
            else:
                owners[paragraph] = relative

    docs_index = (root / "docs/README.md").read_text(encoding="utf-8")
    for relative in A1_ENTRYPOINTS:
        display = relative.removeprefix("docs/") if relative.startswith("docs/") else f"../{relative}"
        if relative == "docs/README.md":
            display = "README.md"
        if f"`{display}`" not in docs_index:
            errors.append(f"docs/README.md is missing A1 entry: {relative}")

    web_index = root / "platform-web/docs/README.md"
    if web_index.is_file():
        text = web_index.read_text(encoding="utf-8")
        for forbidden in ("最高权威", "唯一入口", "当前总架构", "统一文档入口"):
            if forbidden in text:
                errors.append(f"platform-web/docs/README.md must remain specialist reference: {forbidden}")

    return errors


def validate_repository(root: Path) -> list[str]:
    """Return deterministic documentation-consistency errors for ``root``."""

    errors: list[str] = []

    for relative_path in REQUIRED_ENTRYPOINTS:
        if not (root / relative_path).is_file():
            errors.append(f"missing canonical documentation entrypoint: {relative_path}")

    ownership_path = root / "docs/architecture/OWNERSHIP.md"
    if ownership_path.is_file():
        errors.extend(validate_owner_catalog(root, ownership_path.read_text(encoding="utf-8")))

    catalog_reference = "docs/architecture/OWNERSHIP.md"
    for relative_path in DOCUMENT_CATALOG_REFERENCES:
        path = root / relative_path
        if path.is_file() and catalog_reference not in path.read_text(encoding="utf-8"):
            errors.append(f"{relative_path} must reference {catalog_reference}")

    context_path = root / "docs/codex/context-map.md"
    if context_path.is_file():
        errors.extend(validate_context_map(context_path.read_text(encoding="utf-8")))

    errors.extend(validate_a1_hierarchy(root))
    errors.extend(validate_markdown_links(root))
    errors.extend(validate_portable_documentation(root))
    return sorted(errors)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(root)
    if errors:
        print("Documentation consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Documentation consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
