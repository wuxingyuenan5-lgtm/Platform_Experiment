#!/usr/bin/env python3
"""Print a bounded repository reading pack for common Platform tasks."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

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

PACK_BUDGETS: dict[str, tuple[int, int]] = {
    "hedge-style": (34_000, 6_000),
    "identity-permission": (12_000, 8_000),
    "member-contract": (12_750, 7_000),
    "research-field": (17_000, 4_000),
    "research-provider": (13_000, 3_500),
    "trading-display": (15_000, 4_500),
    "user-e2e": (10_500, 4_000),
}
DEFAULT_STARTUP_BUDGET_TOKENS = 4_000
DEFAULT_STARTUP_BASE = ("AGENTS.md", "docs/codex/current-state.md")
DEFAULT_STARTUP_MODULES = (
    "platform-web/AGENTS.md",
    "platform-api/AGENTS.md",
    "execution-runtime/AGENTS.md",
)


def file_metrics(paths: Iterable[str]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    total_lines = 0
    total_bytes = 0
    total_tokens = 0
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            rows.append(
                {
                    "path": relative,
                    "exists": False,
                    "lines": 0,
                    "bytes": 0,
                    "estimated_tokens": 0,
                }
            )
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        lines = len(text.splitlines())
        tokens = (len(text) + 3) // 4
        rows.append(
            {
                "path": relative,
                "exists": True,
                "lines": lines,
                "bytes": len(raw),
                "estimated_tokens": tokens,
            }
        )
        total_lines += lines
        total_bytes += len(raw)
        total_tokens += tokens
    largest = max(
        (row for row in rows if row["exists"]),
        key=lambda row: (int(row["estimated_tokens"]), str(row["path"])),
        default=None,
    )
    return {
        "file_count": len(rows),
        "line_count": total_lines,
        "byte_count": total_bytes,
        "estimated_tokens": total_tokens,
        "largest_file": largest,
        "missing_paths": [str(row["path"]) for row in rows if not row["exists"]],
        "files": rows,
    }


def pack_report(name: str, pack: Pack) -> dict[str, object]:
    required_budget, optional_budget = PACK_BUDGETS.get(name, (0, 0))
    required = file_metrics(pack.required)
    optional = file_metrics(pack.optional)
    required_tokens = int(required["estimated_tokens"])
    optional_tokens = int(optional["estimated_tokens"])
    total_tokens = required_tokens + optional_tokens
    missing = [*required["missing_paths"], *optional["missing_paths"]]
    return {
        "task": name,
        "description": pack.description,
        "required": {
            **required,
            "budget_tokens": required_budget,
            "over_budget": required_budget <= 0 or required_tokens > required_budget,
        },
        "optional": {
            **optional,
            "budget_tokens": optional_budget,
            "over_budget": optional_budget <= 0 or optional_tokens > optional_budget,
        },
        "total": {
            "file_count": int(required["file_count"]) + int(optional["file_count"]),
            "line_count": int(required["line_count"]) + int(optional["line_count"]),
            "byte_count": int(required["byte_count"]) + int(optional["byte_count"]),
            "estimated_tokens": total_tokens,
            "budget_tokens": required_budget + optional_budget,
            "over_budget": (
                required_budget <= 0
                or optional_budget <= 0
                or required_tokens > required_budget
                or optional_tokens > optional_budget
            ),
        },
        "missing_paths": missing,
        "checks": list(pack.checks),
        "default_exclusions": list(DEFAULT_EXCLUSIONS),
    }


def default_startup_report() -> dict[str, object]:
    variants: list[dict[str, object]] = []
    for module_agent in DEFAULT_STARTUP_MODULES:
        paths = (*DEFAULT_STARTUP_BASE, module_agent)
        metrics = file_metrics(paths)
        variants.append(
            {
                "module_agent": module_agent,
                "paths": list(paths),
                **metrics,
            }
        )
    maximum = max(
        variants,
        key=lambda row: (int(row["estimated_tokens"]), str(row["module_agent"])),
    )
    missing = sorted(
        {
            path
            for variant in variants
            for path in variant["missing_paths"]
        }
    )
    return {
        "budget_tokens": DEFAULT_STARTUP_BUDGET_TOKENS,
        "maximum_estimated_tokens": int(maximum["estimated_tokens"]),
        "over_budget": int(maximum["estimated_tokens"]) > DEFAULT_STARTUP_BUDGET_TOKENS,
        "largest_variant": maximum["module_agent"],
        "missing_paths": missing,
        "variants": variants,
    }


def budget_report() -> dict[str, object]:
    pack_names = sorted(PACKS)
    reports = {name: pack_report(name, PACKS[name]) for name in pack_names}
    unbudgeted = sorted(set(PACKS) - set(PACK_BUDGETS))
    orphan_budgets = sorted(set(PACK_BUDGETS) - set(PACKS))
    startup = default_startup_report()
    failures: list[str] = []
    for name, report in reports.items():
        if report["missing_paths"]:
            failures.append(f"{name}: missing paths: {', '.join(report['missing_paths'])}")
        if report["required"]["over_budget"]:
            failures.append(
                f"{name}: required tokens {report['required']['estimated_tokens']} exceed "
                f"budget {report['required']['budget_tokens']}"
            )
        if report["optional"]["over_budget"]:
            failures.append(
                f"{name}: optional tokens {report['optional']['estimated_tokens']} exceed "
                f"budget {report['optional']['budget_tokens']}"
            )
    if unbudgeted:
        failures.append(f"packs without budgets: {', '.join(unbudgeted)}")
    if orphan_budgets:
        failures.append(f"budgets without packs: {', '.join(orphan_budgets)}")
    if startup["missing_paths"]:
        failures.append(
            "default startup missing paths: " + ", ".join(startup["missing_paths"])
        )
    if startup["over_budget"]:
        failures.append(
            f"default startup tokens {startup['maximum_estimated_tokens']} exceed "
            f"budget {startup['budget_tokens']}"
        )
    return {
        "schema_version": 1,
        "packs": reports,
        "default_startup": startup,
        "unbudgeted_packs": unbudgeted,
        "orphan_budgets": orphan_budgets,
        "failures": failures,
        "ok": not failures,
    }


def selected_report(name: str, pack: Pack, include_optional: bool) -> dict[str, object]:
    report = pack_report(name, pack)
    selected = report["total"] if include_optional else report["required"]
    files: Sequence[dict[str, object]] = (
        [*report["required"]["files"], *report["optional"]["files"]]
        if include_optional
        else report["required"]["files"]
    )
    # Preserve the former top-level fields for existing audit consumers.
    return {
        "schema_version": 1,
        "task": name,
        "description": pack.description,
        "include_optional": include_optional,
        "file_count": selected["file_count"],
        "line_count": selected["line_count"],
        "byte_count": selected["byte_count"],
        "estimated_tokens": selected["estimated_tokens"],
        "budget_tokens": selected["budget_tokens"],
        "over_budget": selected["over_budget"],
        "largest_file": selected["largest_file"],
        "missing_paths": report["missing_paths"],
        "files": list(files),
        "required": report["required"],
        "optional": report["optional"],
        "total": report["total"],
        "checks": report["checks"],
        "default_exclusions": report["default_exclusions"],
    }


def render_markdown(name: str, pack: Pack, include_optional: bool) -> str:
    report = selected_report(name, pack, include_optional)
    output = [
        f"# Context pack: {name}",
        "",
        pack.description,
        "",
        f"Required files: {report['required']['file_count']}",
        f"Optional files: {report['optional']['file_count']}",
        f"Required lines: {report['required']['line_count']}",
        f"Optional lines: {report['optional']['line_count']}",
        f"Required bytes: {report['required']['byte_count']}",
        f"Optional bytes: {report['optional']['byte_count']}",
        f"Required estimated tokens: {report['required']['estimated_tokens']} / {report['required']['budget_tokens']}",
        f"Optional estimated tokens: {report['optional']['estimated_tokens']} / {report['optional']['budget_tokens']}",
        f"Selected estimated tokens: {report['estimated_tokens']}",
        f"Selected over budget: {report['over_budget']}",
        "",
        "## Files",
        "",
        "| Path | Kind | Lines | Bytes | Est. tokens |",
        "|---|---|---:|---:|---:|",
    ]
    required_paths = set(pack.required)
    for row in report["files"]:
        suffix = " (missing)" if not row["exists"] else ""
        kind = "required" if row["path"] in required_paths else "optional"
        output.append(
            f"| `{row['path']}`{suffix} | {kind} | {row['lines']} | "
            f"{row['bytes']} | {row['estimated_tokens']} |"
        )
    if pack.optional and not include_optional:
        output += ["", "## Optional only when semantics require it", ""]
        output += [f"- `{path}`" for path in pack.optional]
    output += ["", "## Checks", ""]
    output += [f"- `{command}`" for command in pack.checks]
    output += ["", "## Exclude by default", ""]
    output += [f"- {item}" for item in DEFAULT_EXCLUSIONS]
    if report["missing_paths"]:
        output += ["", "## Missing paths", ""]
        output += [f"- `{path}`" for path in report["missing_paths"]]
    return "\n".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", nargs="?", choices=sorted(PACKS))
    parser.add_argument("--list", action="store_true", help="list available task packs")
    parser.add_argument("--with-optional", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--check-budgets",
        action="store_true",
        help="validate all pack and default-startup budgets",
    )
    args = parser.parse_args()

    if args.check_budgets:
        report = budget_report()
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for name, data in report["packs"].items():
                print(
                    f"{name}: required={data['required']['estimated_tokens']}/"
                    f"{data['required']['budget_tokens']}, optional="
                    f"{data['optional']['estimated_tokens']}/"
                    f"{data['optional']['budget_tokens']}"
                )
            print(
                "default-startup: "
                f"{report['default_startup']['maximum_estimated_tokens']}/"
                f"{report['default_startup']['budget_tokens']}"
            )
            for failure in report["failures"]:
                print(f"ERROR: {failure}")
        raise SystemExit(0 if report["ok"] else 1)

    if args.list or args.task is None:
        for name, pack in sorted(PACKS.items()):
            required_budget, optional_budget = PACK_BUDGETS.get(name, (0, 0))
            print(
                f"{name}: {pack.description} "
                f"[required budget={required_budget}, optional budget={optional_budget}]"
            )
        return

    pack = PACKS[args.task]
    if args.json:
        print(
            json.dumps(
                selected_report(args.task, pack, args.with_optional),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(render_markdown(args.task, pack, args.with_optional), end="")


if __name__ == "__main__":
    main()
