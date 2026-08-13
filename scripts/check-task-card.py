#!/usr/bin/env python3
"""Validate bounded-concurrency fields in Markdown task cards and templates."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_LABELS = (
    "Task ID",
    "Status",
    "Risk level",
    "Role",
    "Agent ID",
    "Implementation owner",
    "Branch",
    "Worktree",
    "Base commit",
    "Context Pack",
    "Recovery from",
    "Recovered owner status",
    "Parallel with",
    "Parallel peer write set",
    "Write set",
    "Shared workflow, public contract, migration chain or file set",
    "Dependencies",
    "Independent test",
    "Rollback boundary",
    "Parallel decision",
    "Acceptance task",
    "Active-agent count after dispatch",
    "Independence evidence",
)

ALLOWED_DECISIONS = {"serial", "parallel-approved", "read-only"}


def field_value(text: str, label: str) -> str | None:
    pattern = rf"(?mi)^\s*(?:-\s*)?{re.escape(label)}:\s*(.+?)\s*$"
    match = re.search(pattern, text)
    return match.group(1).strip(" `") if match else None


def is_none_value(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().strip("`").lower()
    return normalized in {"", "none", "n/a", "not-applicable", "not-required"}


def parse_write_set(value: str | None) -> set[str]:
    if value is None:
        return set()
    normalized = value.strip().strip("`")
    lowered = normalized.lower()
    if lowered in {"", "none", "none (read-only)", "n/a", "not-applicable-read-only"}:
        return set()
    parts = re.split(r"[;\n,]+", normalized)
    return {
        part.strip().strip("`").lower()
        for part in parts
        if part.strip() and part.strip().strip("`").lower() not in {"-", "none"}
    }


def validate(path: Path, template: bool) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures = [
        f"missing required field: {label}"
        for label in REQUIRED_LABELS
        if field_value(text, label) is None
    ]
    if failures or template:
        return failures

    decision = field_value(text, "Parallel decision")
    if decision not in ALLOWED_DECISIONS:
        failures.append(
            "Parallel decision must be serial, parallel-approved or read-only"
        )

    role = (field_value(text, "Role") or "").lower()
    write_set = (field_value(text, "Write set") or "").lower()
    if role in {"investigation", "acceptance"}:
        if "read-only" not in write_set:
            failures.append("read-only roles must declare Write set: none (read-only)")
        if decision != "read-only":
            failures.append("read-only roles must use Parallel decision: read-only")
    elif role == "implementation":
        for label in ("Implementation owner", "Branch", "Worktree", "Base commit"):
            value = (field_value(text, label) or "").lower()
            if not value or value == "none" or "read-only" in value:
                failures.append(f"implementation task requires a concrete {label}")
        branch = field_value(text, "Branch") or ""
        if not branch.startswith("codex/"):
            failures.append("implementation Branch must start with codex/")
    else:
        failures.append("Role must be investigation, implementation or acceptance")

    if decision == "parallel-approved":
        evidence = field_value(text, "Independence evidence")
        if not evidence or evidence.lower() in {"none", "n/a"}:
            failures.append("parallel-approved requires Independence evidence")
        parallel_with = field_value(text, "Parallel with")
        parallel_peer_write_set = field_value(text, "Parallel peer write set")
        shared_boundary = field_value(
            text,
            "Shared workflow, public contract, migration chain or file set",
        )
        write_set_paths = parse_write_set(field_value(text, "Write set"))
        peer_write_set_paths = parse_write_set(parallel_peer_write_set)
        if is_none_value(parallel_with):
            failures.append("parallel-approved requires Parallel with")
        if not peer_write_set_paths:
            failures.append("parallel-approved requires Parallel peer write set")
        if write_set_paths & peer_write_set_paths:
            failures.append("parallel-approved write sets must be disjoint")
        if not is_none_value(shared_boundary):
            failures.append(
                "parallel-approved tasks cannot share workflow, contract, migration or file-set ownership"
            )

    counts = field_value(text, "Active-agent count after dispatch") or ""
    count_pairs = [
        (int(value), int(limit))
        for value, limit in re.findall(r"(\d+)\s*/\s*(\d+)", counts)
    ]
    limits_ok = [limit for _value, limit in count_pairs] == [2, 2, 4]
    values = [value for value, _limit in count_pairs]
    values_ok = (
        len(values) == 3
        and values[0] <= 2
        and values[1] <= 2
        and values[2] <= 4
        and values[2] == values[0] + values[1]
    )
    if not limits_ok or not values_ok:
        failures.append(
            "active-agent counts must be implementation x/2, read-only y/2 and "
            "total x+y/4"
        )

    risk = (field_value(text, "Risk level") or "").lower()
    if risk == "critical" and role == "implementation":
        acceptance_task = (field_value(text, "Acceptance task") or "").lower()
        if acceptance_task in {"", "none", "not-required", "n/a"}:
            failures.append(
                "critical implementation must name an independent read-only acceptance task"
            )

    recovery_from = field_value(text, "Recovery from")
    recovered_owner_status = field_value(text, "Recovered owner status")
    if not is_none_value(recovery_from) and (recovered_owner_status or "").lower() != "closed":
        failures.append(
            "recovery takeover requires the previous owner to be recorded as closed"
        )

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--check-template", action="store_true")
    args = parser.parse_args()

    if not args.path.is_file():
        raise SystemExit(f"ERROR: task card not found: {args.path}")
    failures = validate(args.path, args.check_template)
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        raise SystemExit(1)
    print(f"OK: {args.path}")


if __name__ == "__main__":
    main()
