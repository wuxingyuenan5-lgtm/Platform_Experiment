from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "context-for.py"


def load_module():
    spec = importlib.util.spec_from_file_location("context_for", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ContextForTests(unittest.TestCase):
    def test_budget_report_keeps_estimates_informational(self) -> None:
        module = load_module()
        report = module.budget_report()
        self.assertTrue(report["ok"])
        self.assertEqual(report["failures"], [])
        self.assertNotIn("default_startup", report)
        self.assertTrue(any(
            pack["required"]["over_budget"] or pack["optional"]["over_budget"]
            for pack in report["packs"].values()
        ))

    def test_codex_project_configuration_is_minimal_and_non_blocking(self) -> None:
        config = (REPO_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        agents = REPO_ROOT / ".codex" / "agents"
        hooks = REPO_ROOT / ".codex" / "hooks"
        agents_md = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertNotIn("[hooks]", config)
        self.assertNotIn("[agents]", config.lower())
        self.assertFalse((REPO_ROOT / ".codex" / "hooks.json").exists())
        self.assertEqual(list(agents.glob("*.toml")), [])
        self.assertEqual(list(hooks.glob("*.py")), [])
        self.assertIn("Mode 1: normal direct work by one Agent", agents_md)
        self.assertIn("only when the Owner explicitly requests", agents_md)
        self.assertNotIn("fixed eight-field", agents_md.lower())


if __name__ == "__main__":
    unittest.main()
