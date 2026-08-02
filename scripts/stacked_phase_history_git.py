"""Git graph and final-tree checks for generic stacked-phase history audits."""

from __future__ import annotations

import subprocess
from typing import Any

from stacked_phase_history_model import (
    CATEGORIES,
    AuditError,
    classify,
    is_temporary_path,
)


def git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode:
        raise AuditError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def lines(*args: str) -> list[str]:
    return [line for line in git(*args).splitlines() if line]


def object_sha(revision: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", f"{revision}:{path}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def changed_entries(parent: str, commit: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for raw in lines(
        "diff-tree", "--no-commit-id", "--name-status", "-r", "-M", parent, commit
    ):
        parts = raw.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) == 3:
            result.append(
                {"status": status, "old_path": parts[1], "path": parts[2]}
            )
        elif len(parts) >= 2:
            result.append({"status": status, "path": parts[-1]})
    return result


def diff_stats(parent: str, commit: str) -> tuple[int, int, int]:
    files = additions = deletions = 0
    for raw in lines(
        "diff-tree", "--no-commit-id", "--numstat", "-r", "-M", parent, commit
    ):
        added, deleted, *_paths = raw.split("\t")
        files += 1
        if added.isdigit():
            additions += int(added)
        if deleted.isdigit():
            deletions += int(deleted)
    return files, additions, deletions


def retention(
    parent: str,
    commit: str,
    head: str,
    entries: list[dict[str, str]],
) -> str:
    outcomes: list[str] = []
    for entry in entries:
        path = entry["path"]
        before = object_sha(parent, entry.get("old_path", path))
        after = object_sha(commit, path)
        final = object_sha(head, path)
        if final == after and after != before:
            outcomes.append("retained")
        elif final == before and after != before:
            outcomes.append("removed")
        elif final is None and after is None:
            outcomes.append("retained")
        else:
            outcomes.append("absorbed")
    if not outcomes or all(item == "retained" for item in outcomes):
        return "yes"
    if all(item == "removed" for item in outcomes):
        return "no"
    return "partial"


LOGICAL_OWNERS = {
    "architecture-baseline": "stacked-phase architecture baseline",
    "formal-implementation": "stacked-phase formal implementation",
    "caller-migration": "internal caller migration",
    "legacy-removal": "legacy implementation removal",
    "bounded-correction": "bounded verification correction",
    "contract-test": "contract and architecture verification",
    "governance": "repository and CI governance",
    "documentation": "current authoritative documentation",
    "evidence": "verification evidence",
    "temporary-add": "temporary facility introduction",
    "temporary-remove": "temporary facility cleanup",
    "transport": "transport or trigger facility",
    "unexpected": "unclassified change",
}


def audit(
    accepted_base: str,
    head: str,
    *,
    pr_base: str | None = None,
    phase_number: int | None = None,
) -> dict[str, Any]:
    pr_base = pr_base or accepted_base
    if accepted_base != pr_base:
        raise AuditError(
            "Accepted base SHA does not match PR base SHA: "
            f"accepted={accepted_base}, pr_base={pr_base}"
        )
    if phase_number is not None and phase_number <= 0:
        raise AuditError("stacked phase number must be positive")

    git("cat-file", "-e", f"{accepted_base}^{{commit}}")
    git("cat-file", "-e", f"{head}^{{commit}}")
    behind_text, ahead_text = git(
        "rev-list", "--left-right", "--count", f"{accepted_base}...{head}"
    ).split()
    behind = int(behind_text)
    ahead = int(ahead_text)
    if behind != 0:
        raise AuditError(f"audited head is behind accepted base by {behind} commits")
    if ahead <= 0:
        raise AuditError("audited head must be ahead of accepted base")

    if git("merge-base", accepted_base, head).strip() != accepted_base:
        raise AuditError("accepted base is not the merge base of the audited head")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", accepted_base, head],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode:
        raise AuditError("accepted base is not an ancestor of the audited head")

    merge_commits = lines("rev-list", "--merges", f"{accepted_base}..{head}")
    if merge_commits:
        raise AuditError(f"non-linear or merge commit found: {merge_commits}")

    shas = lines(
        "rev-list", "--reverse", "--ancestry-path", f"{accepted_base}..{head}"
    )
    if len(shas) != ahead:
        raise AuditError(
            "ancestry-path commit count differs from ahead count: "
            f"ancestry={len(shas)}, ahead={ahead}"
        )

    previous = accepted_base
    commits: list[dict[str, Any]] = []
    unexpected: list[str] = []
    temporary_paths: dict[str, dict[str, Any]] = {}

    for index, sha in enumerate(shas, start=1):
        parents = git("show", "-s", "--format=%P", sha).strip().split()
        if len(parents) != 1:
            raise AuditError(f"non-linear or merge commit found: {sha} parents={parents}")
        if parents[0] != previous:
            raise AuditError(
                f"parent chain discontinuity at {sha}: "
                f"expected {previous}, got {parents[0]}"
            )
        parent = parents[0]
        tree = git("show", "-s", "--format=%T", sha).strip()
        message = git("show", "-s", "--format=%B", sha).rstrip("\n")
        entries = changed_entries(parent, sha)
        files, additions, deletions = diff_stats(parent, sha)
        category = classify(message, entries, additions, deletions)
        if category not in CATEGORIES:
            raise AuditError(f"invalid category {category!r} for {sha}")
        if category == "unexpected":
            unexpected.append(sha)
        commits.append(
            {
                "sequence": index,
                "sha": sha,
                "parent_sha": parent,
                "tree_sha": tree,
                "message": message,
                "changed_files": files,
                "additions": additions,
                "deletions": deletions,
                "is_merge_commit": False,
                "category": category,
                "final_tree_retains_change": retention(parent, sha, head, entries),
                "logical_owner": LOGICAL_OWNERS[category],
                "changed_paths": entries,
            }
        )
        for entry in entries:
            path = entry["path"]
            if is_temporary_path(path):
                record = temporary_paths.setdefault(
                    path,
                    {"first_seen": index, "last_seen": index},
                )
                record["last_seen"] = index
                record["present_in_final_tree"] = object_sha(head, path) is not None
        previous = sha

    remaining = sorted(
        path
        for path, item in temporary_paths.items()
        if item.get("present_in_final_tree")
    )
    if remaining:
        raise AuditError(
            f"temporary transport or materialization facilities remain: {remaining}"
        )
    if unexpected:
        raise AuditError(f"unexpected commits require manual stop: {unexpected}")

    return {
        "schema_version": 2,
        "accepted_base_sha": accepted_base,
        "pr_base_sha": pr_base,
        "head_sha": head,
        "stacked_phase": phase_number,
        "ahead": ahead,
        "behind": behind,
        "audited_commit_count": len(commits),
        "merge_commit_count": 0,
        "linear_parent_chain": True,
        "base_is_head_ancestor": True,
        "temporary_paths_absent_from_final_tree": True,
        "unexpected_commits": [],
        "commits": commits,
        "temporary_paths": temporary_paths,
    }
