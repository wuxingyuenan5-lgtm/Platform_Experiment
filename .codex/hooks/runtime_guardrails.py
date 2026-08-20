from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys


AUTHORIZED_WORKTREE_ROOT = Path(__file__).resolve().parents[2]
PROTECTED_SHARED_ROOT = AUTHORIZED_WORKTREE_ROOT.parents[2]
AGENTS_PATH = AUTHORIZED_WORKTREE_ROOT / "AGENTS.md"
CURRENT_STATE_PATH = AUTHORIZED_WORKTREE_ROOT / "docs" / "codex" / "current-state.md"
GOVERNANCE_PATH = (
    AUTHORIZED_WORKTREE_ROOT / "docs" / "codex" / "AI_DEVELOPMENT_GOVERNANCE.md"
)
TASK_CARD_PATH = (
    AUTHORIZED_WORKTREE_ROOT
    / "docs"
    / "codex"
    / "tasks"
    / "VG-GOV-20260820-agent-runtime-guardrails.md"
)
CONTEXT_PACK = "governance"


@dataclass(frozen=True)
class RuntimeState:
    cwd: Path
    branch: str
    head: str
    registered_worktree: bool
    in_protected_shared_root: bool
    write_allowed: bool
    marker: str


def load_payload() -> dict[str, object]:
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def resolve_cwd(payload: dict[str, object]) -> Path:
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd.strip():
        raise ValueError("missing cwd")
    return Path(cwd).resolve()


def git_output(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
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


def path_is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def is_registered_worktree(cwd: Path) -> bool:
    try:
        listing = git_output(cwd, "worktree", "list", "--porcelain")
    except RuntimeError:
        return False
    target = str(cwd)
    for line in listing.splitlines():
        if line.startswith("worktree ") and Path(line.split(" ", 1)[1]).resolve() == cwd:
            return True
    return False


def resolve_runtime_state(cwd: Path) -> RuntimeState:
    git_dir = git_output_or_default(cwd, "invalid", "rev-parse", "--git-dir")
    git_common_dir = git_output_or_default(cwd, "invalid", "rev-parse", "--git-common-dir")
    branch = git_output_or_default(cwd, "invalid", "branch", "--show-current") or "detached"
    head = git_output_or_default(cwd, "invalid", "rev-parse", "--verify", "HEAD")
    registered = (
        git_dir != "invalid"
        and git_common_dir != "invalid"
        and Path(git_dir) != Path(git_common_dir)
    ) or is_registered_worktree(cwd)
    in_protected_shared_root = cwd == PROTECTED_SHARED_ROOT

    write_allowed = (
        path_is_within(cwd, AUTHORIZED_WORKTREE_ROOT)
        and cwd != PROTECTED_SHARED_ROOT
        and registered
        and head != "invalid"
    )
    marker = "WRITE_ALLOWED" if write_allowed else "READ_ONLY_NO_WRITE"
    return RuntimeState(
        cwd=cwd,
        branch=branch,
        head=head,
        registered_worktree=registered,
        in_protected_shared_root=in_protected_shared_root,
        write_allowed=write_allowed,
        marker=marker,
    )


def build_additional_context(state: RuntimeState) -> str:
    lines = [
        f"Repo: {AUTHORIZED_WORKTREE_ROOT}",
        f"Branch: {state.branch}",
        f"HEAD: {state.head}",
        f"Mode: {state.marker}",
        f"Authority: {AGENTS_PATH}",
        f"State: {CURRENT_STATE_PATH}",
        f"Governance: {GOVERNANCE_PATH}",
        f"Pack: use {CONTEXT_PACK}",
        f"Task card: {TASK_CARD_PATH}",
        "Live Write: disabled by default",
    ]
    text = "\n".join(lines)
    return text[:1200]


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
