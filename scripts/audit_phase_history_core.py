#!/usr/bin/env python3
"""Produce a deterministic audit of a linear stacked Platform phase history."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

CATEGORIES = {
    "formal-implementation",
    "bounded-correction",
    "materialization",
    "transport",
    "temporary-add",
    "temporary-remove",
    "evidence",
    "governance",
    "unexpected",
}
FORMAL_MESSAGES = {
    "refactor(platform-0.9.3): remove unused test server workspace",
    "refactor(platform-0.9.3): remove unused demo mock and template assets",
    "refactor(platform-0.9.3): bound route and view discovery",
    "ci(platform-0.9.3): enforce Phase 3 codebase boundaries",
    "chore(platform-0.9.3): simplify frontend build inputs",
    "docs(platform-0.9.3): record Phase 3 bounded cleanup state",
}
TEMPORARY_PREFIXES = (
    "scripts/phase3-materialize/",
    ".github/workflows/phase-3-",
    ".github/workflows/phase3-",
)
GOVERNANCE_PREFIXES = (
    ".github/",
    "docs/",
    "tasks/",
    "scripts/",
    "platform-api/tests/test_architecture_",
)


class AuditError(RuntimeError):
    pass


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
    for raw in lines("diff-tree", "--no-commit-id", "--name-status", "-r", "-M", parent, commit):
        parts = raw.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) == 3:
            result.append({"status": status, "old_path": parts[1], "path": parts[2]})
        elif len(parts) >= 2:
            result.append({"status": status, "path": parts[-1]})
    return result


def diff_stats(parent: str, commit: str) -> tuple[int, int, int]:
    files = additions = deletions = 0
    for raw in lines("diff-tree", "--no-commit-id", "--numstat", "-r", "-M", parent, commit):
        added, deleted, *_paths = raw.split("\t")
        files += 1
        if added.isdigit():
            additions += int(added)
        if deleted.isdigit():
            deletions += int(deleted)
    return files, additions, deletions


def classify(message: str, entries: list[dict[str, str]]) -> str:
    subject = message.splitlines()[0].strip()
    lowered = subject.lower()
    paths = [entry["path"] for entry in entries]
    statuses = [entry["status"] for entry in entries]

    if subject in FORMAL_MESSAGES:
        return "formal-implementation"
    if subject.startswith("fix(platform-0.9.3):"):
        return "bounded-correction"
    if subject.startswith("governance(platform-0.9.3):"):
        return "governance"
    if "phase 3-r1" in lowered or "phase3-r1" in lowered:
        return "governance"
    if subject == "ci(platform-0.9.3): authorize bounded stacked workstream":
        return "governance"

    temporary_only = bool(paths) and all(path.startswith(TEMPORARY_PREFIXES) for path in paths)
    if temporary_only:
        if all(status.startswith("D") for status in statuses):
            return "temporary-remove"
        if any(word in lowered for word in ("transport", "publish", "object", "blob")):
            return "transport"
        if any(word in lowered for word in ("evidence", "snapshot", "artifact", "export")):
            return "evidence"
        if any(status.startswith("A") for status in statuses) and any(
            word in lowered for word in ("add", "bootstrap", "stage", "introduce")
        ):
            return "temporary-add"
        return "materialization"

    if any(word in lowered for word in ("materializ", "reconstruct", "payload")) and all(
        path.startswith(GOVERNANCE_PREFIXES) for path in paths
    ):
        return "materialization"
    if any(word in lowered for word in ("transport", "publish", "object", "blob")) and all(
        path.startswith(GOVERNANCE_PREFIXES) for path in paths
    ):
        return "transport"
    if any(word in lowered for word in ("evidence", "snapshot", "artifact", "export")) and all(
        path.startswith(GOVERNANCE_PREFIXES) for path in paths
    ):
        return "evidence"
    if paths and all(path.startswith(GOVERNANCE_PREFIXES) for path in paths):
        return "governance"
    return "unexpected"


def retention(parent: str, commit: str, head: str, entries: list[dict[str, str]]) -> str:
    outcomes: list[str] = []
    for entry in entries:
        path = entry["path"]
        old_path = entry.get("old_path", path)
        before = object_sha(parent, old_path)
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


def audit(base: str, head: str, required_ancestor: str | None) -> dict[str, Any]:
    git("cat-file", "-e", f"{base}^{{commit}}")
    git("cat-file", "-e", f"{head}^{{commit}}")
    if git("merge-base", base, head).strip() != base:
        raise AuditError("base is not the merge base of the audited head")
    if required_ancestor:
        git("cat-file", "-e", f"{required_ancestor}^{{commit}}")
        if subprocess.run(["git", "merge-base", "--is-ancestor", required_ancestor, head]).returncode:
            raise AuditError("required original head is not an ancestor of the audited head")
        original_count = int(git("rev-list", "--count", f"{base}..{required_ancestor}").strip())
        if original_count != 34:
            raise AuditError(f"original Phase 3 range must contain 34 commits; found {original_count}")
    else:
        original_count = None

    shas = lines("rev-list", "--reverse", "--ancestry-path", f"{base}..{head}")
    previous = base
    commits: list[dict[str, Any]] = []
    merge_count = 0
    unexpected: list[str] = []
    temporary_paths: dict[str, dict[str, Any]] = {}

    for index, sha in enumerate(shas, start=1):
        parents = git("show", "-s", "--format=%P", sha).strip().split()
        if len(parents) != 1:
            merge_count += 1
            raise AuditError(f"non-linear or merge commit found: {sha} parents={parents}")
        if parents[0] != previous:
            raise AuditError(f"parent chain discontinuity at {sha}: expected {previous}, got {parents[0]}")
        parent = parents[0]
        tree = git("show", "-s", "--format=%T", sha).strip()
        message = git("show", "-s", "--format=%B", sha).rstrip("\n")
        entries = changed_entries(parent, sha)
        files, additions, deletions = diff_stats(parent, sha)
        category = classify(message, entries)
        if category not in CATEGORIES:
            raise AuditError(f"invalid category {category!r} for {sha}")
        if category == "unexpected":
            unexpected.append(sha)
        retained = retention(parent, sha, head, entries)
        logical_owner = {
            "formal-implementation": "Phase 3 product-code reduction",
            "bounded-correction": "Phase 3 verification correction",
            "materialization": "deterministic materialization machinery",
            "transport": "Git object or payload transport",
            "temporary-add": "temporary materialization facility",
            "temporary-remove": "temporary facility cleanup",
            "evidence": "verification evidence collection",
            "governance": "Phase governance and auditability",
            "unexpected": "unclassified change",
        }[category]
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
                "final_tree_retains_change": retained,
                "logical_owner": logical_owner,
                "changed_paths": entries,
            }
        )
        for entry in entries:
            path = entry["path"]
            if path.startswith(TEMPORARY_PREFIXES):
                record = temporary_paths.setdefault(path, {"first_seen": index, "last_seen": index})
                record["last_seen"] = index
                record["present_in_final_tree"] = object_sha(head, path) is not None
        previous = sha

    temp_left = sorted(path for path, item in temporary_paths.items() if item.get("present_in_final_tree"))
    if temp_left:
        raise AuditError(f"temporary materialization facilities remain in final tree: {temp_left}")
    if unexpected:
        raise AuditError(f"unexpected commits require manual stop: {unexpected}")

    return {
        "schema_version": 1,
        "base_sha": base,
        "head_sha": head,
        "required_original_head": required_ancestor,
        "original_commit_count": original_count,
        "audited_commit_count": len(commits),
        "merge_commit_count": merge_count,
        "linear_parent_chain": True,
        "temporary_paths_absent_from_final_tree": True,
        "unexpected_commits": [],
        "commits": commits,
        "temporary_paths": temporary_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--required-original-head")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = audit(args.base, args.head, args.required_original_head)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(
        "Phase history audit passed: "
        f"{payload['audited_commit_count']} commits, "
        f"{payload['merge_commit_count']} merges, 0 unexpected."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"Phase history audit failed: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1) from exc
