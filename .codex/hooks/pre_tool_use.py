from __future__ import annotations

import re

from runtime_guardrails import deny_with_exit, load_payload, resolve_cwd, resolve_runtime_state


ALWAYS_BLOCK_PATTERNS = (
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\b",
    r"\bgit\s+checkout\s+--\b",
    r"\bdel\s+/s\b",
    r"\brd\s+/s\b",
    r"\brmdir\s+/s\b",
    r"\bremove-item\b[^\n\r]*\brecurse\b",
    r"\brm\s+-rf\b",
)

READ_ONLY_GIT_EXACT_ALLOWLIST = {
    "git branch --show-current",
    "git worktree list",
}

READ_ONLY_GIT_PREFIX_ALLOWLIST = (
    "git status",
    "git diff",
    "git show",
    "git log",
    "git rev-parse",
    "git merge-base",
    "git ls-files",
    "git ls-tree",
    "git cat-file",
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


def normalize_command(command: str) -> str:
    return " ".join(command.strip().split())


def matches_any(command: str, patterns: tuple[str, ...]) -> bool:
    lowered = command.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def tool_name_lower(payload: dict[str, object]) -> str:
    return str(payload.get("tool_name") or "").strip().lower()


def extract_shell_command(tool_input: object) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if isinstance(command, str) and command.strip():
        return command
    cmd = tool_input.get("cmd")
    if isinstance(cmd, str) and cmd.strip():
        return cmd
    return None


def is_git_command(command: str) -> bool:
    return normalize_command(command).lower().startswith("git ")


def is_allowed_read_only_git(command: str) -> bool:
    lowered = normalize_command(command).lower()
    if lowered in READ_ONLY_GIT_EXACT_ALLOWLIST:
        return True
    return any(lowered == prefix or lowered.startswith(prefix + " ") for prefix in READ_ONLY_GIT_PREFIX_ALLOWLIST)


def is_obvious_write_command(command: str) -> bool:
    lowered = normalize_command(command).lower()
    if is_git_command(lowered):
        return not is_allowed_read_only_git(lowered)
    return matches_any(lowered, READ_ONLY_WRITE_HINTS)


def main() -> None:
    payload = load_payload()
    cwd = resolve_cwd(payload)
    state = resolve_runtime_state(cwd)
    tool_name = tool_name_lower(payload)
    tool_input = payload.get("tool_input")

    if tool_name in {"apply_patch", "edit", "write"}:
        if state.marker == "READ_ONLY_NO_WRITE":
            deny_with_exit("READ_ONLY_NO_WRITE: patch-style write tool is blocked in this workspace.")
        return

    if tool_name not in {"bash", "exec_command"}:
        return

    command = extract_shell_command(tool_input)
    if command is None:
        deny_with_exit("Fail closed: missing shell command for write-policy evaluation.")

    normalized = normalize_command(command)

    if matches_any(normalized, ALWAYS_BLOCK_PATTERNS):
        deny_with_exit(f"Blocked by repository policy: {normalized}")

    if state.marker == "READ_ONLY_NO_WRITE" and is_git_command(normalized) and not is_allowed_read_only_git(normalized):
        deny_with_exit(f"READ_ONLY_NO_WRITE: blocked non-read-only git command: {normalized}")

    if state.marker == "READ_ONLY_NO_WRITE" and is_obvious_write_command(normalized):
        deny_with_exit(f"READ_ONLY_NO_WRITE: blocked obvious write command: {normalized}")


if __name__ == "__main__":
    main()
