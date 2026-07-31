#!/usr/bin/env python3
"""Print a bounded repository reading pack for common Platform tasks."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EXCLUSIONS = (
    "tasks/ except the active Critical packet",
    "closed PR discussions and historical handoffs",
    "lock files unless dependency resolution is the task",
    "node_modules, virtual environments, build, coverage and Playwright output",
    "src/views/demo, Mock data and template examples",
    "projects/risk-control unless legacy deployment or migration is the task",
    "unrelated services and large static catalogs",
)


@dataclass(frozen=True)
class Pack:
    description: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    checks: tuple[str, ...]


PACKS: dict[str, Pack] = {
    "hedge-style": Pack(
        "Modify hedge/research board layout or styling without changing visible behavior.",
        (
            "AGENTS.md",
            "docs/codex/current-state.md",
            "platform-web/AGENTS.md",
            "platform-web/src/views/hedgeBoard/index.vue",
            "platform-web/scripts/verify-hedge-board-layout.cjs",
        ),
        (
            "platform-web/docs/design/platform-ui-guidelines.md",
            "platform-web/e2e/hedge-board/hedge-board.spec.ts",
        ),
        (
            "cd platform-web && pnpm test:hedge-board-layout",
            "cd platform-web && pnpm type:check",
            "cd platform-web && pnpm test:e2e:hedge-board",
        ),
    ),
    "research-field": Pack(
        "Change one A-share, Shenwan or research field without reading unrelated Providers.",
        (
            "AGENTS.md",
            "docs/codex/current-state.md",
            "platform-web/AGENTS.md",
            "platform-web/src/views/hedgeBoard/aShare/index.vue",
            "platform-web/src/views/hedgeBoard/aShare/useAShareResearch.ts",
            "platform-web/src/api/hedgeResearch.ts",
            "platform-api/AGENTS.md",
            "platform-api/app/research_data_schemas.py",
            "platform-api/app/research_service.py",
            "platform-api/tests/test_research_service.py",
        ),
        (
            "platform-api/app/research_providers.py",
            "platform-api/app/research_cache.py",
            "platform-api/tests/test_a_share_research_policy.py",
        ),
        (
            "cd platform-api && python -m pytest tests/test_research_service.py",
            "cd platform-web && pnpm type:check",
        ),
    ),
    "identity-permission": Pack(
        "Change browser role, permission or Session behavior while preserving security boundaries.",
        (
            "AGENTS.md",
            "docs/codex/current-state.md",
            "platform-web/AGENTS.md",
            "platform-web/src/access/userAccess.ts",
            "platform-web/src/router/guard/permissionGuard.ts",
            "platform-api/AGENTS.md",
            "platform-api/app/auth.py",
            "platform-api/app/user_authority.py",
            "platform-api/app/user_permissions.py",
            "platform-api/tests/test_auth_rbac.py",
        ),
        (
            "platform-api/app/user_session_auth.py",
            "platform-api/tests/test_last_ceo_concurrency.py",
            "platform-web/e2e/user-system/user-system.spec.ts",
        ),
        (
            "cd platform-api && python -m pytest tests/test_auth_rbac.py",
            "cd platform-web && pnpm test:user-system",
            "cd platform-web && pnpm test:e2e:user-system",
        ),
    ),
    "member-contract": Pack(
        "Change the member holdings/NAV API contract without loading Runtime or unrelated user administration.",
        (
            "AGENTS.md",
            "docs/codex/current-state.md",
            "platform-web/AGENTS.md",
            "platform-web/src/api/platform/memberHoldings.ts",
            "platform-api/AGENTS.md",
            "platform-api/app/member_holding_routes.py",
            "platform-api/app/member_holding_schemas.py",
            "platform-api/app/member_holding_service.py",
            "platform-api/tests/test_member_holdings.py",
        ),
        (
            "platform-api/app/member_holding_repository.py",
            "docs/technical/MEMBER_HOLDINGS_READ_MODEL.md",
            "platform-api/tests/test_member_holding_decimal.py",
        ),
        (
            "cd platform-api && python -m pytest tests/test_member_holdings.py",
            "cd platform-web && pnpm test:user-system",
        ),
    ),
    "trading-display": Pack(
        "Change cross-spread/funding display while keeping execution and accounting semantics unchanged.",
        (
            "AGENTS.md",
            "docs/codex/current-state.md",
            "platform-web/AGENTS.md",
            "platform-web/src/views/strategy/spread-carry/components/CrossVenueExecutionReplica.vue",
            "platform-web/src/api/platform/crossSpreadObservability.ts",
            "platform-api/AGENTS.md",
            "platform-api/app/cross_spread_observability_schemas.py",
            "platform-api/tests/test_cross_spread_observability.py",
        ),
        (
            "platform-web/scripts/verify-cross-spread-layout.cjs",
            "platform-api/app/cross_spread_observability_service.py",
            "execution-runtime/AGENTS.md",
        ),
        (
            "cd platform-web && pnpm test:cross-spread-layout",
            "cd platform-api && python -m pytest tests/test_cross_spread_observability.py",
            "cd platform-web && pnpm type:check",
        ),
    ),
    "research-provider": Pack(
        "Add or repair one external Research Provider with explicit status and Last Known Good behavior.",
        (
            "AGENTS.md",
            "docs/codex/current-state.md",
            "platform-api/AGENTS.md",
            "platform-api/app/research_providers.py",
            "platform-api/app/research_service.py",
            "platform-api/app/research_cache.py",
            "platform-api/app/research_data_schemas.py",
            "platform-api/scripts/smoke_research_providers.py",
            "platform-api/tests/test_research_service.py",
        ),
        (
            "platform-web/src/api/hedgeResearch.ts",
            "docs/technical/RESEARCH_DATA_PLATFORM.md",
        ),
        (
            "cd platform-api && python -m pytest tests/test_research_service.py",
            "cd platform-api && python scripts/smoke_research_providers.py --timeout 60",
        ),
    ),
    "user-e2e": Pack(
        "Repair user-system browser E2E without loading unrelated product modules.",
        (
            "AGENTS.md",
            "docs/codex/current-state.md",
            "platform-web/AGENTS.md",
            "platform-web/e2e/user-system/user-system.spec.ts",
            "platform-web/playwright.user-system.config.ts",
            "platform-web/scripts/test-user-system-access.cjs",
            "platform-api/AGENTS.md",
            "platform-api/scripts/seed_user_system_e2e.py",
        ),
        (
            "platform-web/e2e/user-system/demo-accounts.spec.ts",
            "platform-api/tests/test_user_browser_flows.py",
        ),
        (
            "cd platform-web && pnpm test:user-system",
            "cd platform-web && pnpm test:e2e:user-system",
        ),
    ),
}


def file_metrics(paths: Iterable[str]) -> tuple[list[dict[str, object]], int, int]:
    rows: list[dict[str, object]] = []
    total_lines = 0
    total_chars = 0
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            rows.append({"path": relative, "exists": False, "lines": 0, "estimated_tokens": 0})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = len(text.splitlines())
        tokens = (len(text) + 3) // 4
        rows.append({"path": relative, "exists": True, "lines": lines, "estimated_tokens": tokens})
        total_lines += lines
        total_chars += len(text)
    return rows, total_lines, (total_chars + 3) // 4


def render_markdown(name: str, pack: Pack, include_optional: bool) -> str:
    selected = pack.required + (pack.optional if include_optional else ())
    rows, total_lines, total_tokens = file_metrics(selected)
    missing = [str(row["path"]) for row in rows if not row["exists"]]
    large = [str(row["path"]) for row in rows if int(row["lines"]) > 1000]
    output = [
        f"# Context pack: {name}",
        "",
        pack.description,
        "",
        f"Required files: {len(pack.required)}",
        f"Selected files: {len(selected)}",
        f"Selected lines: {total_lines}",
        f"Estimated text tokens: {total_tokens}",
        "",
        "## Files",
        "",
        "| Path | Lines | Est. tokens |",
        "|---|---:|---:|",
    ]
    for row in rows:
        suffix = " (missing)" if not row["exists"] else ""
        output.append(f"| `{row['path']}`{suffix} | {row['lines']} | {row['estimated_tokens']} |")
    if pack.optional and not include_optional:
        output += ["", "## Optional only when semantics require it", ""]
        output += [f"- `{path}`" for path in pack.optional]
    output += ["", "## Checks", ""]
    output += [f"- `{command}`" for command in pack.checks]
    output += ["", "## Exclude by default", ""]
    output += [f"- {item}" for item in DEFAULT_EXCLUSIONS]
    if large:
        output += ["", "## Hotspot warning", ""]
        output += [f"- `{path}` exceeds 1,000 lines and remains a structural context hotspot." for path in large]
    if missing:
        output += ["", "## Missing paths", ""]
        output += [f"- `{path}`" for path in missing]
    return "\n".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", nargs="?", choices=sorted(PACKS))
    parser.add_argument("--list", action="store_true", help="list available task packs")
    parser.add_argument("--with-optional", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list or args.task is None:
        for name, pack in sorted(PACKS.items()):
            print(f"{name}: {pack.description}")
        return

    pack = PACKS[args.task]
    selected = pack.required + (pack.optional if args.with_optional else ())
    rows, total_lines, total_tokens = file_metrics(selected)
    if args.json:
        print(
            json.dumps(
                {
                    "task": args.task,
                    "description": pack.description,
                    "include_optional": args.with_optional,
                    "file_count": len(selected),
                    "line_count": total_lines,
                    "estimated_tokens": total_tokens,
                    "files": rows,
                    "checks": pack.checks,
                    "default_exclusions": DEFAULT_EXCLUSIONS,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    print(render_markdown(args.task, pack, args.with_optional), end="")


if __name__ == "__main__":
    main()
