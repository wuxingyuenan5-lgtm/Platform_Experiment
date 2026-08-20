from __future__ import annotations

import re

from runtime_guardrails import deny_with_exit, load_payload, resolve_cwd, resolve_runtime_state


ALWAYS_BLOCK_PATTERNS = (
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\b",
    r"\bgit\s+checkout\s+--\b",
    r"\bgit\s+restore\b.*\b(--source|--staged|--worktree)\b",
    r"\bdel\s+/s\b",
    r"\brd\s+/s\b",
    r"\brmdir\s+/s\b",
    r"\bremove-item\b[^\n\r]*\brecurse\b",
    r"\brm\s+-rf\b",
)

SHARED_ROOT_BLOCK_PATTERNS = (
    r"\bgit\s+add(?:\s+-A|\s+\.)\s*$",
    r"\bgit\s+commit\b",
    r"\bgit\s+(checkout|switch)\b",
    r"\bgit\s+(update-ref|symbolic-ref|branch\s+-f|tag\s+-f)\b",
)

READ_ONLY_WRITE_HINTS = (
    r"\bnew-item\b",
    r"\bset-content\b",
    r"\badd-content\b",
    r"\bout-file\b",
    r"\bcopy-item\b",
    r"\bmove-item\b",
    r">",
    r">>",
)

READ_ONLY_GIT_ALLOWLIST = (
    "git status",
    "git diff",
    "git rev-parse",
    "git merge-base",
    "git branch --show-current",
    "git worktree list",
    "git show",
    "git log",
)


def normalize_command(command: str) -> str:
    return " ".join(command.strip().split())


def matches_any(command: str, patterns: tuple[str, ...]) -> bool:
    lowered = command.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def is_read_only_git(command: str) -> bool:
    lowered = normalize_command(command).lower()
    return any(lowered.startswith(prefix) for prefix in READ_ONLY_GIT_ALLOWLIST)


def is_obvious_write_command(command: str) -> bool:
    lowered = normalize_command(command).lower()
    if is_read_only_git(lowered):
        return False
    if matches_any(lowered, SHARED_ROOT_BLOCK_PATTERNS):
        return True
    return matches_any(lowered, READ_ONLY_WRITE_HINTS)


def main() -> None:
    payload = load_payload()
    cwd = resolve_cwd(payload)
    state = resolve_runtime_state(cwd)
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")

    if tool_name == "apply_patch":
        if state.marker == "READ_ONLY_NO_WRITE":
            deny_with_exit("READ_ONLY_NO_WRITE: apply_patch is blocked in this workspace.")
        return

    if tool_name != "Bash":
        return

    if not isinstance(tool_input, dict) or not isinstance(tool_input.get("command"), str):
        deny_with_exit("Fail closed: missing Bash command for write-policy evaluation.")

    command = str(tool_input["command"])
    normalized = normalize_command(command)

    if matches_any(normalized, ALWAYS_BLOCK_PATTERNS):
        deny_with_exit(f"Blocked by repository policy: {normalized}")

    if state.in_protected_shared_root and matches_any(normalized, SHARED_ROOT_BLOCK_PATTERNS):
        deny_with_exit(
            "Blocked in protected shared root: Git ref, index, checkout, switch, and commit writes are disabled."
        )

    if state.marker == "READ_ONLY_NO_WRITE" and is_obvious_write_command(normalized):
        deny_with_exit(f"READ_ONLY_NO_WRITE: blocked obvious write command: {normalized}")


if __name__ == "__main__":
    main()
