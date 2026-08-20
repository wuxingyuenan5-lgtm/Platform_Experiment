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
SESSION_START_PATH = CODEX_DIR / "hooks" / "session_start.py"
PRE_TOOL_USE_PATH = CODEX_DIR / "hooks" / "pre_tool_use.py"
WORKTREE_ROOT = REPO_ROOT
SHARED_ROOT = REPO_ROOT.parents[2]

EXPECTED_AGENTS = {
    "critical-reviewer.toml": {
        "name": "critical-reviewer",
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "medium",
        "sandbox_mode": "read-only",
    },
    "platform-worker.toml": {
        "name": "platform-worker",
        "model": "gpt-5.4-mini",
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


def run_hook(script_path: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path)],
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
        self.assertEqual(data["agents"]["default_subagent_model"], "gpt-5.4-mini")
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
            self.assertEqual(
                data["model_reasoning_effort"],
                expected["model_reasoning_effort"],
            )
            self.assertEqual(data["sandbox_mode"], expected["sandbox_mode"])
            self.assertTrue(data["description"].strip())
            self.assertTrue(data["developer_instructions"].strip())

    def test_hooks_json_wires_expected_events(self) -> None:
        self.assertTrue(HOOKS_JSON_PATH.is_file(), ".codex/hooks.json must exist")
        data = json.loads(HOOKS_JSON_PATH.read_text(encoding="utf-8"))
        hooks = data["hooks"]

        self.assertIn("SessionStart", hooks)
        self.assertIn("SubagentStart", hooks)
        self.assertIn("PreToolUse", hooks)

    def test_session_start_outputs_short_writable_context_for_registered_worktree(self) -> None:
        payload = {
            "session_id": "sess-1",
            "cwd": str(WORKTREE_ROOT),
            "hook_event_name": "SessionStart",
            "source": "startup",
            "permission_mode": "default",
            "model": "gpt-5.6-luna",
        }
        result = run_hook(SESSION_START_PATH, payload)
        self.assertEqual(result.returncode, 0, result.stderr)

        body = json.loads(result.stdout)
        context = body["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(context), 1200)
        self.assertIn("WRITE_ALLOWED", context)
        self.assertIn("codex/vg-agent-runtime-guardrails", context)
        self.assertIn("d665eed8f7092af22b1f986827a7064a086d9ce1", context)
        self.assertIn("governance", context)
        self.assertNotIn("Authority hierarchy", context)

    def test_session_start_marks_shared_root_read_only(self) -> None:
        payload = {
            "session_id": "sess-2",
            "cwd": str(SHARED_ROOT),
            "hook_event_name": "SessionStart",
            "source": "startup",
            "permission_mode": "default",
            "model": "gpt-5.6-luna",
        }
        result = run_hook(SESSION_START_PATH, payload)
        self.assertEqual(result.returncode, 0, result.stderr)

        body = json.loads(result.stdout)
        context = body["hookSpecificOutput"]["additionalContext"]
        self.assertIn("READ_ONLY_NO_WRITE", context)
        self.assertLessEqual(len(context), 1200)

    def test_pre_tool_use_allows_read_only_git_command(self) -> None:
        payload = {
            "session_id": "sess-3",
            "cwd": str(WORKTREE_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_use_id": "tool-1",
            "tool_input": {"command": "git diff --check"},
            "permission_mode": "default",
            "model": "gpt-5.4-mini",
        }
        result = run_hook(PRE_TOOL_USE_PATH, payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_pre_tool_use_blocks_destructive_and_protected_root_writes(self) -> None:
        destructive_payload = {
            "session_id": "sess-4",
            "cwd": str(WORKTREE_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_use_id": "tool-2",
            "tool_input": {"command": "git reset --hard"},
            "permission_mode": "default",
            "model": "gpt-5.4-mini",
        }
        destructive = run_hook(PRE_TOOL_USE_PATH, destructive_payload)
        self.assertEqual(destructive.returncode, 2)
        self.assertIn("blocked", destructive.stderr.lower())

        shared_root_payload = {
            "session_id": "sess-5",
            "cwd": str(SHARED_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_use_id": "tool-3",
            "tool_input": {"command": "git add ."},
            "permission_mode": "default",
            "model": "gpt-5.4-mini",
        }
        shared_root = run_hook(PRE_TOOL_USE_PATH, shared_root_payload)
        self.assertEqual(shared_root.returncode, 2)
        self.assertIn("protected shared root", shared_root.stderr.lower())

    def test_pre_tool_use_blocks_recursive_delete_and_apply_patch_in_read_only_state(self) -> None:
        delete_payload = {
            "session_id": "sess-6",
            "cwd": str(WORKTREE_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_use_id": "tool-4",
            "tool_input": {"command": 'Remove-Item -Recurse "C:\\temp\\x"'},
            "permission_mode": "default",
            "model": "gpt-5.4-mini",
        }
        delete_result = run_hook(PRE_TOOL_USE_PATH, delete_payload)
        self.assertEqual(delete_result.returncode, 2)
        self.assertIn("blocked", delete_result.stderr.lower())

        patch_payload = {
            "session_id": "sess-7",
            "cwd": str(SHARED_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "apply_patch",
            "tool_use_id": "tool-5",
            "tool_input": {"command": "*** Begin Patch\n*** End Patch\n"},
            "permission_mode": "default",
            "model": "gpt-5.4-mini",
        }
        patch_result = run_hook(PRE_TOOL_USE_PATH, patch_payload)
        self.assertEqual(patch_result.returncode, 2)
        self.assertIn("read_only_no_write", patch_result.stderr.lower())

    def test_pre_tool_use_fails_closed_for_write_when_payload_is_invalid(self) -> None:
        payload = {
            "session_id": "sess-8",
            "cwd": str(WORKTREE_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_use_id": "tool-6",
            "tool_input": {},
            "permission_mode": "default",
            "model": "gpt-5.4-mini",
        }
        result = run_hook(PRE_TOOL_USE_PATH, payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("fail closed", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
