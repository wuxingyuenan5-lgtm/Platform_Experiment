#!/usr/bin/env python3
"""Print bounded repository reading packs and report their context estimates."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "scripts/context-packs.json"
FORMAL_CROSS_VENUE_OWNER = (
    "platform-web/src/views/strategy/spread-carry/components/"
    "CrossVenueExecutionWorkspace.vue"
)
DEFAULT_EXCLUSIONS = (
    "closed pull-request discussions and historical handoffs",
    "lock files unless dependency resolution is the task",
    "node_modules, virtual environments, build, coverage and Playwright output",
    "src/views/demo, mock data and template examples",
    "retired project material and external migration evidence",
    "unrelated services and large static catalogs",
)

CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
PACKS: dict[str, dict[str, object]] = CONFIG["packs"]
PACK_BUDGETS: dict[str, list[int]] = CONFIG["budgets"]
PACK_CATEGORIES = frozenset(CONFIG.get("pack_categories", ()))
BOUNDED_CONCURRENCY = CONFIG.get("bounded_concurrency", {})
TASK_CARD_CHECK = CONFIG.get("task_card_check")

EXPECTED_CONCURRENCY = {
    "treat_limits_as": "maximum-safe-upper-bound",
    "max_active_agents": 2,
    "max_implementation_agents": 1,
    "max_read_only_agents": 1,
    "default_implementation_agents": 1,
    "second_implementation_requires": "not-permitted-by-default",
    "default_when_independence_unproven": "serial",
    "critical_acceptance": "independent-read-only",
    "do_not_split_work_to_fill_capacity": True,
}
EXPECTED_PARALLEL_REQUIREMENTS = {
    "disjoint_write_sets",
    "no_unfinished_dependencies",
    "independent_tests",
    "independent_rollback",
}


def largest_file(rows: Iterable[dict[str, object]]) -> dict[str, object] | None:
    existing = [row for row in rows if row["exists"]]
    return max(
        existing,
        key=lambda row: (int(row["estimated_tokens"]), str(row["path"])),
        default=None,
    )


def file_metrics(paths: Iterable[str]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
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
        rows.append(
            {
                "path": relative,
                "exists": True,
                "lines": len(text.splitlines()),
                "bytes": len(raw),
                "estimated_tokens": (len(text) + 3) // 4,
            }
        )

    return {
        "file_count": len(rows),
        "line_count": sum(int(row["lines"]) for row in rows),
        "byte_count": sum(int(row["bytes"]) for row in rows),
        "estimated_tokens": sum(int(row["estimated_tokens"]) for row in rows),
        "largest_file": largest_file(rows),
        "missing_paths": [str(row["path"]) for row in rows if not row["exists"]],
        "files": rows,
    }


def pack_report(name: str) -> dict[str, object]:
    pack = PACKS[name]
    legacy_input_budget, legacy_output_budget = PACK_BUDGETS[name]
    required_budget = int(pack.get("input_budget", legacy_input_budget))
    optional_budget = int(pack.get("output_budget", legacy_output_budget))
    required = file_metrics(pack["required"])
    optional = file_metrics(pack["optional"])
    required_tokens = int(required["estimated_tokens"])
    optional_tokens = int(optional["estimated_tokens"])
    return {
        "task": name,
        "description": pack["description"],
        "category": pack.get("category"),
        "owner_modules": list(pack.get("owner_modules", ())),
        "risk_level": pack.get("risk_level"),
        "write_boundary": pack.get("write_boundary"),
        "legacy_budget_compatible": (
            required_budget == legacy_input_budget
            and optional_budget == legacy_output_budget
        ),
        "required": {
            **required,
            "budget_tokens": required_budget,
            "over_budget": required_tokens > required_budget,
        },
        "optional": {
            **optional,
            "budget_tokens": optional_budget,
            "over_budget": optional_tokens > optional_budget,
        },
        "total": {
            "file_count": int(required["file_count"]) + int(optional["file_count"]),
            "line_count": int(required["line_count"]) + int(optional["line_count"]),
            "byte_count": int(required["byte_count"]) + int(optional["byte_count"]),
            "estimated_tokens": required_tokens + optional_tokens,
            "budget_tokens": required_budget + optional_budget,
            "over_budget": (
                required_tokens > required_budget
                or optional_tokens > optional_budget
            ),
            "largest_file": largest_file(
                [*required["files"], *optional["files"]]
            ),
        },
        "missing_paths": [
            *required["missing_paths"],
            *optional["missing_paths"],
        ],
        "checks": list(pack["checks"]),
        "default_exclusions": list(DEFAULT_EXCLUSIONS),
    }


def budget_report() -> dict[str, object]:
    reports = {name: pack_report(name) for name in sorted(PACKS)}
    unbudgeted = sorted(set(PACKS) - set(PACK_BUDGETS))
    orphan_budgets = sorted(set(PACK_BUDGETS) - set(PACKS))
    failures: list[str] = []

    for key, expected in EXPECTED_CONCURRENCY.items():
        if BOUNDED_CONCURRENCY.get(key) != expected:
            failures.append(f"bounded_concurrency.{key} must be {expected!r}")
    actual_requirements = set(
        BOUNDED_CONCURRENCY.get("parallel_implementation_requires", ())
    )
    if actual_requirements != EXPECTED_PARALLEL_REQUIREMENTS:
        failures.append(
            "bounded_concurrency.parallel_implementation_requires must declare "
            "disjoint writes, no unfinished dependencies, independent tests and "
            "independent rollback"
        )
    if not isinstance(TASK_CARD_CHECK, str) or "scripts/check-task-card.py" not in TASK_CARD_CHECK:
        failures.append("task_card_check must identify the optional task-card validator")

    for name, report in reports.items():
        category = report["category"]
        if category is not None and category not in PACK_CATEGORIES:
            failures.append(f"{name}: unsupported category: {category}")
        if report["missing_paths"]:
            failures.append(
                f"{name}: missing paths: {', '.join(report['missing_paths'])}"
            )
    return {
        "schema_version": 1,
        "packs": reports,
        "unbudgeted_packs": unbudgeted,
        "orphan_budgets": orphan_budgets,
        "bounded_concurrency": BOUNDED_CONCURRENCY,
        "task_card_check": TASK_CARD_CHECK,
        "failures": failures,
        "ok": not failures,
    }


def selected_report(name: str, include_optional: bool) -> dict[str, object]:
    report = pack_report(name)
    selected = report["total"] if include_optional else report["required"]
    files = (
        [*report["required"]["files"], *report["optional"]["files"]]
        if include_optional
        else report["required"]["files"]
    )
    keys = (
        "file_count",
        "line_count",
        "byte_count",
        "estimated_tokens",
        "budget_tokens",
        "over_budget",
        "largest_file",
    )
    return {
        "schema_version": 1,
        "task": name,
        "description": report["description"],
        "category": report["category"],
        "owner_modules": report["owner_modules"],
        "risk_level": report["risk_level"],
        "write_boundary": report["write_boundary"],
        "include_optional": include_optional,
        **{key: selected[key] for key in keys},
        "missing_paths": report["missing_paths"],
        "files": list(files),
        "required": report["required"],
        "optional": report["optional"],
        "total": report["total"],
        "checks": report["checks"],
        "default_exclusions": report["default_exclusions"],
        "bounded_concurrency": BOUNDED_CONCURRENCY,
        "task_card_check": TASK_CARD_CHECK,
    }


def render_markdown(name: str, include_optional: bool) -> str:
    pack = PACKS[name]
    report = selected_report(name, include_optional)
    output = [
        f"# Context pack: {name}",
        "",
        str(pack["description"]),
        "",
        f"Category: {report['category'] or 'legacy-unspecified'}",
        f"Owner modules: {', '.join(report['owner_modules']) or 'legacy-unspecified'}",
        f"Risk level: {report['risk_level'] or 'legacy-unspecified'}",
        f"Write boundary: {report['write_boundary'] or 'legacy-unspecified'}",
        "Bounded concurrency: default 1 implementation agent; max-safe upper bound 4 active, 2 implementation and 2 read-only",
        "Parallel implementation: disjoint writes, no unfinished dependencies, independent tests and rollback; otherwise serial; do not split work merely to use capacity",
        f"Task card check: {TASK_CARD_CHECK}",
        "",
        f"Required files: {report['required']['file_count']}",
        f"Optional files: {report['optional']['file_count']}",
        f"Required estimated tokens: {report['required']['estimated_tokens']} / "
        f"{report['required']['budget_tokens']}",
        f"Optional estimated tokens: {report['optional']['estimated_tokens']} / "
        f"{report['optional']['budget_tokens']}",
        f"Selected estimated tokens: {report['estimated_tokens']}",
        f"Selected over budget: {report['over_budget']}",
        "",
        "## Files",
        "",
        "| Path | Kind | Lines | Bytes | Est. tokens |",
        "|---|---|---:|---:|---:|",
    ]
    required_paths = set(pack["required"])
    for row in report["files"]:
        suffix = " (missing)" if not row["exists"] else ""
        kind = "required" if row["path"] in required_paths else "optional"
        output.append(
            f"| `{row['path']}`{suffix} | {kind} | {row['lines']} | "
            f"{row['bytes']} | {row['estimated_tokens']} |"
        )
    if pack["optional"] and not include_optional:
        output.extend(["", "## Optional only when semantics require it", ""])
        output.extend(f"- `{path}`" for path in pack["optional"])
    output.extend(["", "## Checks", ""])
    output.extend(f"- `{command}`" for command in pack["checks"])
    output.extend(["", "## Exclude by default", ""])
    output.extend(f"- {item}" for item in DEFAULT_EXCLUSIONS)
    if report["missing_paths"]:
        output.extend(["", "## Missing paths", ""])
        output.extend(f"- `{path}`" for path in report["missing_paths"])
    return "\n".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", nargs="?", choices=sorted(PACKS))
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--with-optional", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-budgets", action="store_true")
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
            for failure in report["failures"]:
                print(f"ERROR: {failure}")
        raise SystemExit(0 if report["ok"] else 1)

    if args.list or args.task is None:
        for name, pack in sorted(PACKS.items()):
            required_budget, optional_budget = PACK_BUDGETS[name]
            print(
                f"{name}: {pack['description']} "
                f"[required budget={required_budget}, "
                f"optional budget={optional_budget}]"
            )
        return

    if args.json:
        print(
            json.dumps(
                selected_report(args.task, args.with_optional),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(render_markdown(args.task, args.with_optional), end="")


if __name__ == "__main__":
    main()
