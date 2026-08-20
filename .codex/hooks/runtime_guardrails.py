from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


INVALID = "invalid"


@dataclass(frozen=True)
class RuntimeState:
    cwd: Path
    repo_root: Path | None
    branch: str
    head: str
    git_dir: Path | None
    git_common_dir: Path | None
    registered_worktree: bool
    write_allowed: bool
    marker: str


def load_payload() -> dict[str, object]:
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def resolve_cwd(payload: dict[str, object]) -> Path:
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd.strip():
        raise ValueError("missing cwd")
    resolved = Path(cwd).resolve()
    if not resolved.is_dir():
        raise ValueError("cwd is not a directory")
    return resolved


def git_executable() -> str | None:
    return shutil.which("git")


def git_output(cwd: Path, *args: str) -> str:
    executable = git_executable()
    if executable is None:
        raise RuntimeError("git is unavailable")
    completed = subprocess.run(
        [executable, *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git failed")
    return completed.stdout.strip()


def git_output_or_default(cwd: Path, default: str, *args: str) -> str:
    try:
        return git_output(cwd, *args)
    except RuntimeError:
        return default


def resolve_path(raw: str) -> Path | None:
    if raw == INVALID or not raw:
        return None
    return Path(raw).resolve()


def normalize_path_string(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path.resolve())))


def path_is_within(path: Path, root: Path) -> bool:
    try:
        if path.samefile(root):
            return True
    except OSError:
        pass
    normalized_path = normalize_path_string(path)
    normalized_root = normalize_path_string(root)
    return normalized_path == normalized_root or normalized_path.startswith(normalized_root + os.sep)


def is_registered_worktree(cwd: Path, repo_root: Path | None) -> bool:
    if repo_root is None:
        return False
    normalized_repo_root = normalize_path_string(repo_root)
    listing = git_output_or_default(cwd, "", "worktree", "list", "--porcelain")
    if not listing:
        return False
    for line in listing.splitlines():
        if not line.startswith("worktree "):
            continue
        candidate = Path(line.split(" ", 1)[1]).resolve()
        if normalize_path_string(candidate) == normalized_repo_root:
            return True
    return False


def resolve_runtime_state(cwd: Path) -> RuntimeState:
    repo_root = resolve_path(git_output_or_default(cwd, INVALID, "rev-parse", "--show-toplevel"))
    git_dir = resolve_path(
        git_output_or_default(cwd, INVALID, "rev-parse", "--path-format=absolute", "--git-dir")
    )
    git_common_dir = resolve_path(
        git_output_or_default(cwd, INVALID, "rev-parse", "--path-format=absolute", "--git-common-dir")
    )
    branch = git_output_or_default(cwd, INVALID, "branch", "--show-current") or "detached"
    head = git_output_or_default(cwd, INVALID, "rev-parse", "--verify", "HEAD")
    show_prefix = git_output_or_default(cwd, INVALID, "rev-parse", "--show-prefix")
    registered_worktree = is_registered_worktree(cwd, repo_root)
    linked_worktree = git_dir is not None and git_common_dir is not None and git_dir != git_common_dir
    within_repo_root = repo_root is not None and show_prefix != INVALID
    write_allowed = (
        linked_worktree
        and head != INVALID
        and branch.startswith("codex/")
        and within_repo_root
        and registered_worktree
    )
    marker = "WRITE_ALLOWED" if write_allowed else "READ_ONLY_NO_WRITE"
    return RuntimeState(
        cwd=cwd,
        repo_root=repo_root,
        branch=branch,
        head=head,
        git_dir=git_dir,
        git_common_dir=git_common_dir,
        registered_worktree=registered_worktree,
        write_allowed=write_allowed,
        marker=marker,
    )


def build_additional_context(state: RuntimeState) -> str:
    repo_root = state.repo_root or state.cwd
    lines = [
        f"Repo root: {repo_root}",
        f"Branch: {state.branch}",
        f"HEAD: {state.head}",
        f"Mode: {state.marker}",
        f"Authority: {repo_root / 'AGENTS.md'}",
        f"State: {repo_root / 'docs' / 'codex' / 'current-state.md'}",
        f"Governance: {repo_root / 'docs' / 'codex' / 'AI_DEVELOPMENT_GOVERNANCE.md'}",
        "Load the Context Pack and task card named in the current startup envelope.",
        "If no Pack or task card was supplied for a repository write task, stop before writing.",
        "Live Write is disabled by default.",
    ]
    context = "\n".join(lines)
    return context[:1000]


def hook_context_response(event_name: str, state: RuntimeState) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": build_additional_context(state),
        }
    }


def deny_with_exit(reason: str) -> None:
    sys.stderr.write(reason.rstrip() + "\n")
    raise SystemExit(2)
