from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tomllib
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
CODEX_DIR = REPO_ROOT / ".codex"
CONFIG_PATH = CODEX_DIR / "config.toml"
AGENTS_DIR = CODEX_DIR / "agents"
HOOKS_JSON_PATH = CODEX_DIR / "hooks.json"
HOOKS_DIR = CODEX_DIR / "hooks"
SESSION_START_PATH = HOOKS_DIR / "session_start.py"
PRE_TOOL_USE_PATH = HOOKS_DIR / "pre_tool_use.py"
WINDOWS_WRAPPER_PATH = HOOKS_DIR / "run_hook.ps1"

EXPECTED_AGENTS = {
    "critical-reviewer.toml": {
        "name": "critical-reviewer",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "medium",
        "sandbox_mode": "read-only",
    },
    "platform-worker.toml": {
        "name": "platform-worker",
        "model": "gpt-5.6-luna",
        "model_reasoning_effort": "medium",
        "sandbox_mode": "workspace-write",
    },
    "project-lead.toml": {
        "name": "project-lead",
        "model": "gpt-5.6-luna",
        "model_reasoning_effort": "low",
        "sandbox_mode": "read-only",
    },
    "technical-lead.toml": {
        "name": "technical-lead",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "medium",
        "sandbox_mode": "workspace-write",
    },
}

READ_ONLY_GIT_COMMANDS = (
    "git status --short",
    "git diff --check",
    "git show --stat HEAD",
    "git log -1 --oneline",
    "git rev-parse HEAD",
    "git merge-base HEAD HEAD",
    "git worktree list",
    "git branch --show-current",
    "git ls-files",
    "git ls-tree HEAD",
    "git cat-file -t HEAD",
)

BLOCKED_SHARED_ROOT_GIT_COMMANDS = (
    "git restore AGENTS.md",
    "git add AGENTS.md",
    "git stash push -m test",
    "git worktree add C:/temp/x",
)


def run_text(args: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def git_value(*args: str, cwd: Path = REPO_ROOT) -> str:
    return run_text(["git", *args], cwd=cwd)


def shared_root() -> Path:
    return REPO_ROOT.parents[2].resolve()


def current_head() -> str:
    return git_value("rev-parse", "HEAD", cwd=REPO_ROOT)


def current_branch() -> str:
    return git_value("branch", "--show-current", cwd=REPO_ROOT)


def current_repo_root() -> str:
    return git_value("rev-parse", "--show-toplevel", cwd=REPO_ROOT)


def normalize_path_text(value: str) -> str:
    return value.replace("/", "\\")


def run_python_hook(script_path: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
    )


def run_windows_wrapper(script_path: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-File",
            str(WINDOWS_WRAPPER_PATH),
            str(script_path),
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
    )


class CodexRuntimeGuardrailTests(unittest.TestCase):
    def test_config_toml_has_expected_project_scoped_defaults(self) -> None:
        self.assertTrue(CONFIG_PATH.is_file(), ".codex/config.toml must exist")
        data = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["features"]["hooks"], True)
        self.assertEqual(data["agents"]["enabled"], True)
        self.assertEqual(data["agents"]["max_concurrent_threads_per_session"], 2)
        self.assertEqual(data["agents"]["default_subagent_model"], "gpt-5.6-luna")
        self.assertEqual(data["agents"]["default_subagent_reasoning_effort"], "medium")
        self.assertEqual(data["agents"]["interrupt_message"], False)
        self.assertEqual(data["models"]["new_thread"]["model"], "gpt-5.6-luna")
        self.assertEqual(data["models"]["new_thread"]["model_reasoning_effort"], "low")

    def test_only_four_expected_project_agents_exist(self) -> None:
        self.assertTrue(AGENTS_DIR.is_dir(), ".codex/agents must exist")
        agent_files = {path.name for path in AGENTS_DIR.glob("*.toml")}
        self.assertEqual(agent_files, set(EXPECTED_AGENTS))

    def test_agent_files_match_required_models_and_permissions(self) -> None:
        for filename, expected in EXPECTED_AGENTS.items():
            path = AGENTS_DIR / filename
            self.assertTrue(path.is_file(), f"missing agent file: {filename}")
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["name"], expected["name"])
            self.assertEqual(data["model"], expected["model"])
            self.assertEqual(data["model_reasoning_effort"], expected["model_reasoning_effort"])
            self.assertEqual(data["sandbox_mode"], expected["sandbox_mode"])
            self.assertTrue(data["description"].strip())
            self.assertTrue(data["developer_instructions"].strip())

    def test_hooks_json_wires_expected_events_and_windows_wrapper(self) -> None:
        self.assertTrue(HOOKS_JSON_PATH.is_file(), ".codex/hooks.json must exist")
        data = json.loads(HOOKS_JSON_PATH.read_text(encoding="utf-8"))
        hooks = data["hooks"]
        self.assertIn("SessionStart", hooks)
        self.assertIn("SubagentStart", hooks)
        self.assertIn("PreToolUse", hooks)
        self.assertIn("exec_command", hooks["PreToolUse"][0]["matcher"])
        self.assertIn("run_hook.ps1", hooks["SessionStart"][0]["hooks"][0]["commandWindows"])

    def test_session_start_outputs_portable_short_context_for_current_worktree(self) -> None:
        payload = {
            "session_id": "sess-1",
            "cwd": str(REPO_ROOT),
            "hook_event_name": "SessionStart",
            "source": "startup",
            "permission_mode": "default",
            "model": "gpt-5.6-luna",
        }
        result = run_python_hook(SESSION_START_PATH, payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)
        context = body["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(context), 1000)
        self.assertIn("WRITE_ALLOWED", context)
        self.assertIn(current_branch(), context)
        self.assertIn(current_head(), context)
        self.assertIn(normalize_path_text(current_repo_root()), context)
        self.assertIn(
            "Load the Context Pack and task card named in the current startup envelope.",
            context,
        )
        self.assertIn(
            "If no Pack or task card was supplied for a repository write task, stop before writing.",
            context,
        )
        self.assertNotIn("VG-GOV-20260820-agent-runtime-guardrails", context)
        self.assertNotIn("governance", context)

    def test_session_start_marks_shared_root_read_only(self) -> None:
        payload = {
            "session_id": "sess-2",
            "cwd": str(shared_root()),
            "hook_event_name": "SessionStart",
            "source": "startup",
            "permission_mode": "default",
            "model": "gpt-5.6-luna",
        }
        result = run_python_hook(SESSION_START_PATH, payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)
        context = body["hookSpecificOutput"]["additionalContext"]
        self.assertIn("READ_ONLY_NO_WRITE", context)
        self.assertNotIn("WRITE_ALLOWED", context)
        self.assertLessEqual(len(context), 1000)

    def test_windows_wrapper_can_launch_session_start_hook(self) -> None:
        payload = {
            "session_id": "sess-3",
            "cwd": str(REPO_ROOT),
            "hook_event_name": "SessionStart",
            "source": "startup",
            "permission_mode": "default",
            "model": "gpt-5.6-luna",
        }
        result = run_windows_wrapper(SESSION_START_PATH, payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual(body["hookSpecificOutput"]["hookEventName"], "SessionStart")

    def test_windows_wrapper_can_launch_pre_tool_use_hook_with_cmd_input(self) -> None:
        payload = {
            "session_id": "sess-4",
            "cwd": str(REPO_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "exec_command",
            "tool_use_id": "tool-1",
            "tool_input": {"cmd": "git diff --check"},
            "permission_mode": "default",
            "model": "gpt-5.6-luna",
        }
        result = run_windows_wrapper(PRE_TOOL_USE_PATH, payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_pre_tool_use_allows_read_only_git_commands_for_bash_and_exec_command(self) -> None:
        for command in READ_ONLY_GIT_COMMANDS:
            bash_payload = {
                "session_id": "bash-read-only",
                "cwd": str(REPO_ROOT),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_use_id": "tool-bash",
                "tool_input": {"command": command},
                "permission_mode": "default",
                "model": "gpt-5.6-luna",
            }
            bash_result = run_python_hook(PRE_TOOL_USE_PATH, bash_payload)
            self.assertEqual(bash_result.returncode, 0, bash_result.stderr)

            exec_payload = {
                "session_id": "exec-read-only",
                "cwd": str(REPO_ROOT),
                "hook_event_name": "PreToolUse",
                "tool_name": "exec_command",
                "tool_use_id": "tool-exec",
                "tool_input": {"cmd": command},
                "permission_mode": "default",
                "model": "gpt-5.6-luna",
            }
            exec_result = run_python_hook(PRE_TOOL_USE_PATH, exec_payload)
            self.assertEqual(exec_result.returncode, 0, exec_result.stderr)

    def test_pre_tool_use_blocks_apply_patch_edit_and_write_in_shared_root(self) -> None:
        for tool_name in ("apply_patch", "Edit", "Write"):
            payload = {
                "session_id": f"patch-{tool_name}",
                "cwd": str(shared_root()),
                "hook_event_name": "PreToolUse",
                "tool_name": tool_name,
                "tool_use_id": "tool-patch",
                "tool_input": {"command": "*** Begin Patch\n*** End Patch\n"},
                "permission_mode": "default",
                "model": "gpt-5.6-luna",
            }
            result = run_python_hook(PRE_TOOL_USE_PATH, payload)
            self.assertEqual(result.returncode, 2)
            self.assertIn("read_only_no_write", result.stderr.lower())

    def test_pre_tool_use_blocks_shared_root_git_writes(self) -> None:
        for command in BLOCKED_SHARED_ROOT_GIT_COMMANDS:
            payload = {
                "session_id": f"shared-{command}",
                "cwd": str(shared_root()),
                "hook_event_name": "PreToolUse",
                "tool_name": "exec_command",
                "tool_use_id": "tool-write",
                "tool_input": {"cmd": command},
                "permission_mode": "default",
                "model": "gpt-5.6-luna",
            }
            result = run_python_hook(PRE_TOOL_USE_PATH, payload)
            self.assertEqual(result.returncode, 2)
            self.assertIn("read_only_no_write", result.stderr.lower())

    def test_pre_tool_use_blocks_global_destructive_commands_even_when_write_allowed(self) -> None:
        payload = {
            "session_id": "destructive",
            "cwd": str(REPO_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_use_id": "tool-danger",
            "tool_input": {"command": 'Remove-Item -Recurse "C:\\temp\\x"'},
            "permission_mode": "default",
            "model": "gpt-5.6-luna",
        }
        result = run_python_hook(PRE_TOOL_USE_PATH, payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("blocked", result.stderr.lower())

    def test_pre_tool_use_fails_closed_for_missing_write_command_input(self) -> None:
        payload = {
            "session_id": "fail-closed",
            "cwd": str(REPO_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "exec_command",
            "tool_use_id": "tool-missing",
            "tool_input": {},
            "permission_mode": "default",
            "model": "gpt-5.6-luna",
        }
        result = run_python_hook(PRE_TOOL_USE_PATH, payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("fail closed", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
