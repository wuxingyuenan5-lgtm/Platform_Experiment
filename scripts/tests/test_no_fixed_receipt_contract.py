from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class NoFixedReceiptContractTests(unittest.TestCase):
    def test_active_authorities_do_not_force_the_legacy_eight_field_receipt(self) -> None:
        program = (REPO_ROOT / "docs" / "codex" / "0.11.1-program.md").read_text(
            encoding="utf-8"
        )
        issue_template = (
            REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "engineering-task.yml"
        ).read_text(encoding="utf-8")

        self.assertNotIn("Return only `outcome`", program)
        self.assertNotIn("id: output_contract", issue_template)


if __name__ == "__main__":
    unittest.main()
