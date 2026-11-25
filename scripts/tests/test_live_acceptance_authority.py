from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_AUTHORITIES = (
    "docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md",
    "docs/operations/RUNBOOK.md",
    "docs/BASELINE.md",
    "docs/contracts/LIVE_ACCOUNT_OBSERVABILITY.md",
    "docs/contracts/AUTHORIZATION.md",
    "docs/contracts/VENUE_ADAPTERS.md",
    "docs/contracts/VENUE_RECONCILIATION.md",
    "docs/operations/DEPLOYMENT.md",
)


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class LiveAcceptanceAuthorityTests(unittest.TestCase):
    def test_active_authorities_do_not_claim_fixed_size_or_cap_requirements(self) -> None:
        prohibited_claims = (
            "controlled, minimum-size live acceptance",
            "controlled minimum-size validation",
            "minimum-size live validation",
            "before any 1 oz real-money write",
            "defaults to `1 oz`",
            "maximum order quantity: 1 oz",
            "repeated 1 oz open/close cycles",
            "first 1 oz write window",
            "1 oz、单活动生命周期",
            "真实账户最小允许仓位验收",
            "platform absolute notional limits；",
        )

        for relative_path in ACTIVE_AUTHORITIES:
            content = read(relative_path).lower()
            for claim in prohibited_claims:
                self.assertNotIn(claim, content, f"{relative_path} retains prohibited claim")

    def test_runbook_retains_instruction_bounds_and_owner_approved_chase_parameters(self) -> None:
        runbook = read("docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md")
        required_contract = (
            "One instruction creates at most one batch",
            "cumulative external fills may not exceed its quantities",
            "Resource serialization",
            "Unknown outcomes prohibit blind retry, duplicate intent and blind rollback",
            "Kill Switch",
            "proof of forced reset",
            "15-second total chase TTL",
            "one-second evaluation cadence",
            "at most five amend or cancel-repost mutations",
            "at least one tick of price change before mutation",
        )

        for statement in required_contract:
            self.assertIn(statement, runbook, f"runbook lost mandatory contract text: {statement}")

    def test_mandatory_safeguards_are_not_relax_or_remove_candidates(self) -> None:
        observability = read("docs/contracts/LIVE_ACCOUNT_OBSERVABILITY.md")
        safeguards = observability.split("## 10. Controlled-acceptance safeguards", 1)[1].split(
            "## 11. Windows-host acceptance sequence", 1
        )[0]

        self.assertIn(
            "The mandatory safeguards above are not candidates for relaxation or removal",
            safeguards,
        )
        self.assertNotIn("`retain`, `relax` or `remove`", safeguards)

    def test_normal_authorization_retires_acceptance_caps_but_preserves_live_gates(self) -> None:
        baseline = read("docs/BASELINE.md")
        runbook = read("docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md")
        auth = read("docs/contracts/AUTHORIZATION.md")
        self.assertIn("Legacy acceptance sessions and temporary windows are not normal trading prerequisites", baseline)
        self.assertIn("Normal CEO execution no longer applies temporary acceptance quantity/notional", baseline)
        self.assertIn("Legacy `LiveTradingSession` records do not participate in normal trading admission", runbook)
        self.assertIn("Platform and Runtime Live Write remain independent, default-off", runbook)
        self.assertIn("does not authorize a real order", runbook)
        for safeguard in ("Kill Switch", "idempotency", "result_unknown"):
            self.assertIn(safeguard, baseline)
        self.assertIn("CEO", auth)
        # Retained legacy records cannot become a permission gate for normal trading.
        self.assertIn(
            'Literal["minimum_size_acceptance", "existing_limits", "scale_change"]',
            read("platform-api/app/live_trading_sessions.py"),
        )


if __name__ == "__main__":
    unittest.main()
