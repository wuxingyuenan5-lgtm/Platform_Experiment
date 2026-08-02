"""Classification policy for generic stacked-phase history audits."""

from __future__ import annotations

import re

CATEGORIES = {
    "architecture-baseline",
    "formal-implementation",
    "caller-migration",
    "legacy-removal",
    "bounded-correction",
    "contract-test",
    "governance",
    "documentation",
    "evidence",
    "temporary-add",
    "temporary-remove",
    "transport",
    "unexpected",
}
CONVENTIONAL_SUBJECT = re.compile(
    r"^(?P<kind>refactor|fix|test|ci|docs|chore|governance)"
    r"(?:\([^)]+\))?!?:\s+(?P<summary>.+)$",
    re.IGNORECASE,
)
GOVERNANCE_PREFIXES = (
    ".github/",
    "docs/",
    "tasks/",
    "scripts/",
    "platform-api/tests/test_architecture_",
    "execution-runtime/tests/test_runtime_",
)
TEST_MARKERS = ("/tests/", "tests/", ".spec.", ".test.", "__snapshots__/")
MIGRATION_WORDS = ("migrate", "caller", "consumer", "call site", "adopt")
REMOVAL_WORDS = ("remove", "delete", "retire", "drop", "cleanup", "clean up", "exit")
BASELINE_WORDS = ("architecture baseline", "hotspot", "dependency graph", "import graph")
EVIDENCE_WORDS = ("evidence", "snapshot", "artifact", "metrics", "inventory")
TRANSPORT_WORDS = ("transport", "publish", "materializ", "payload", "blob", "trigger")


class AuditError(RuntimeError):
    """A stacked-phase history invariant was violated."""


def is_temporary_path(path: str) -> bool:
    lowered = path.lower()
    if lowered.startswith("scripts/phase") and any(
        marker in lowered
        for marker in ("materializ", "transport", "publish", "payload")
    ):
        return True
    if lowered.startswith(".github/workflows/") and "phase" in lowered and any(
        marker in lowered
        for marker in ("materializ", "transport", "publish", "trigger")
    ):
        return True
    return lowered.startswith("internal/") and any(
        marker in lowered
        for marker in ("transport", "publish", "materializ", "trigger")
    )


def is_governance_path(path: str) -> bool:
    return path.startswith(GOVERNANCE_PREFIXES)


def is_test_path(path: str) -> bool:
    lowered = path.lower()
    return any(marker in lowered for marker in TEST_MARKERS)


def classify(
    message: str,
    entries: list[dict[str, str]],
    additions: int = 0,
    deletions: int = 0,
) -> str:
    subject = message.splitlines()[0].strip()
    lowered = subject.lower()
    paths = [entry["path"] for entry in entries]
    statuses = [entry["status"] for entry in entries]

    if not entries:
        return "transport" if any(word in lowered for word in TRANSPORT_WORDS) else "unexpected"

    if all(is_temporary_path(path) for path in paths):
        if all(status.startswith("D") for status in statuses):
            return "temporary-remove"
        if any(word in lowered for word in TRANSPORT_WORDS):
            return "transport"
        if any(status.startswith("A") for status in statuses):
            return "temporary-add"
        return "unexpected"

    match = CONVENTIONAL_SUBJECT.match(subject)
    if match is None:
        return "unexpected"
    kind = match.group("kind").lower()
    summary = match.group("summary").lower()

    if any(word in summary for word in BASELINE_WORDS):
        return "architecture-baseline"
    if any(word in summary for word in EVIDENCE_WORDS) and all(
        is_governance_path(path) for path in paths
    ):
        return "evidence"
    if kind == "docs":
        return "documentation"
    if kind in {"ci", "governance"}:
        return "governance"
    if kind == "test":
        if all(is_governance_path(path) for path in paths):
            return "governance"
        return "contract-test" if all(is_test_path(path) for path in paths) else "unexpected"
    if kind == "fix":
        return "bounded-correction"
    if any(word in summary for word in MIGRATION_WORDS):
        return "caller-migration"
    if any(word in summary for word in REMOVAL_WORDS):
        return "legacy-removal"
    if kind == "refactor":
        return "formal-implementation"
    if kind == "chore":
        if all(is_governance_path(path) for path in paths):
            return "governance"
        if deletions > additions and any(word in summary for word in ("simplify", "reduce")):
            return "legacy-removal"
        if any(word in summary for word in ("simplify", "normalize", "consolidate")):
            return "formal-implementation"
    return "unexpected"
