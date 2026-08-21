#!/usr/bin/env python3
"""Validate governance task records and templates."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


CORE_REQUIRED_LABELS = (
    "Task ID",
    "Status",
    "Last transition at",
    "Business status summary",
    "Risk level",
    "Role",
    "Context Pack",
)

IMPLEMENTATION_REQUIRED_LABELS = (
    "Implementation owner",
    "Base commit",
    "Write set",
    "Shared workflow, public contract, migration chain or file set",
    "Dependencies",
    "Independent test",
    "Rollback boundary",
    "Parallel decision",
)

PARALLEL_REQUIRED_LABELS = (
    "Parallel with",
    "Parallel peer write set",
    "Independence evidence",
)

RECOVERY_REQUIRED_LABELS = ("Recovery from", "Recovered owner status")
ALLOWED_ROLES = {"investigation", "implementation", "acceptance"}
ALLOWED_STATUSES = {"planned", "active", "review", "attention", "blocked", "done"}
ALLOWED_DECISIONS = {"serial", "parallel-approved"}


def field_value(text: str, label: str) -> str | None:
    pattern = rf"(?mi)^\s*(?:-\s*)?{re.escape(label)}:\s*(.+?)\s*$"
    match = re.search(pattern, text)
    return match.group(1).strip(" `") if match else None


def is_none_value(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().strip("`").lower() in {
        "",
        "none",
        "n/a",
        "not-applicable",
        "not-required",
    }


def parse_write_set(value: str | None) -> set[str]:
    if value is None:
        return set()
    normalized = value.strip().strip("`")
    if normalized.lower() in {"", "none", "none (read-only)"}:
        return set()
    return {
        item.strip().strip("`").lower()
        for item in re.split(r"[;\n,]+", normalized)
        if item.strip() and item.strip().strip("`").lower() not in {"-", "none"}
    }


def require_labels(text: str, labels: tuple[str, ...]) -> list[str]:
    return [
        f"missing required field: {label}"
        for label in labels
        if field_value(text, label) is None
    ]


def parse_token_value(
    text: str,
    label: str,
    failures: list[str],
    *,
    allow_unavailable: bool,
) -> int | str | None:
    raw = field_value(text, label)
    if raw is None:
        return None
    normalized = raw.replace(",", "").strip().lower()
    if allow_unavailable and normalized == "unavailable":
        return "unavailable"
    if not re.fullmatch(r"\d+", normalized):
        if allow_unavailable:
            failures.append(f"{label} must be a non-negative integer or unavailable")
        else:
            failures.append(f"{label} must be a non-negative integer")
        return None
    return int(normalized)


def validate_status_summary(status: str, summary: str, failures: list[str]) -> None:
    lowered = summary.lower()
    if status in {"attention", "blocked"} and "needs:" not in lowered:
        failures.append(
            f"{status} Business status summary must state who needs to do what next using Needs:"
        )
    if status == "done":
        required_tokens = ("capability:", "evidence:")
        if any(token not in lowered for token in required_tokens):
            failures.append(
                "done Business status summary must include Capability: and Evidence:"
            )


def validate_counts(counts: str, failures: list[str]) -> None:
    count_pairs = [(int(value), int(limit)) for value, limit in re.findall(r"(\d+)\s*/\s*(\d+)", counts)]
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
            "active-agent counts must be implementation x/2, read-only y/2 and total x+y/4"
        )


def validate_token_controls(text: str, failures: list[str]) -> dict[str, int | str | None]:
    status = (field_value(text, "Status") or "").lower()
    return {}


def validate(path: Path, template: bool) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures = require_labels(text, CORE_REQUIRED_LABELS)
    if template:
        return failures + require_labels(
            text,
            (
                *IMPLEMENTATION_REQUIRED_LABELS,
                *PARALLEL_REQUIRED_LABELS,
                *RECOVERY_REQUIRED_LABELS,
                "Acceptance task",
            ),
        )

    role = (field_value(text, "Role") or "").lower()
    status = (field_value(text, "Status") or "").lower()
    summary = field_value(text, "Business status summary") or ""

    if role not in ALLOWED_ROLES:
        failures.append("Role must be investigation, implementation or acceptance")
    if status not in ALLOWED_STATUSES:
        failures.append("Status must be planned, active, review, attention, blocked or done")
    if not (field_value(text, "Last transition at") or "").strip():
        failures.append("Last transition at must be recorded")
    if not summary.strip():
        failures.append("Business status summary must be recorded")
    else:
        validate_status_summary(status, summary, failures)

    if role == "implementation":
        failures.extend(require_labels(text, IMPLEMENTATION_REQUIRED_LABELS))
        for label in ("Implementation owner", "Base commit"):
            if is_none_value(field_value(text, label)):
                failures.append(f"implementation task requires a concrete {label}")
        branch = field_value(text, "Branch") or ""
        if branch and not branch.startswith("codex/"):
            failures.append("implementation Branch must start with codex/")

        decision = (field_value(text, "Parallel decision") or "").lower()
        if decision not in ALLOWED_DECISIONS:
            failures.append("Parallel decision must be serial or parallel-approved")

        if decision == "parallel-approved":
            failures.extend(require_labels(text, PARALLEL_REQUIRED_LABELS))
            if is_none_value(field_value(text, "Independence evidence")):
                failures.append("parallel-approved requires Independence evidence")
            if is_none_value(field_value(text, "Parallel with")):
                failures.append("parallel-approved requires Parallel with")
            write_set_paths = parse_write_set(field_value(text, "Write set"))
            peer_write_set_paths = parse_write_set(field_value(text, "Parallel peer write set"))
            if not peer_write_set_paths:
                failures.append("parallel-approved requires Parallel peer write set")
            if write_set_paths & peer_write_set_paths:
                failures.append("parallel-approved write sets must be disjoint")
            if not is_none_value(
                field_value(
                    text,
                    "Shared workflow, public contract, migration chain or file set",
                )
            ):
                failures.append(
                    "parallel-approved tasks cannot share workflow, contract, migration or file-set ownership"
                )
            validate_counts(field_value(text, "Active-agent count after dispatch") or "", failures)

        if (field_value(text, "Risk level") or "").lower() == "critical" and is_none_value(
            field_value(text, "Acceptance task")
        ):
            failures.append(
                "critical implementation must name an independent read-only acceptance task"
            )

    if field_value(text, "Recovery from") is not None or field_value(text, "Recovered owner status") is not None:
        failures.extend(require_labels(text, RECOVERY_REQUIRED_LABELS))
        recovery_from = field_value(text, "Recovery from")
        recovered_owner_status = (field_value(text, "Recovered owner status") or "").lower()
        if not is_none_value(recovery_from) and recovered_owner_status != "closed":
            failures.append("recovery takeover requires the previous owner to be recorded as closed")

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
