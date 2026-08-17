from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_AUTHORITIES = (
    "docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md",
    "docs/operations/RUNBOOK.md",
    "docs/codex/current-state.md",
    "docs/codex/0.11.1-program.md",
    "docs/technical/LIVE_ACCOUNT_OBSERVABILITY.md",
    "docs/technical/AUTH_RBAC_LIVE_SESSIONS.md",
    "docs/technical/LIVE_VENUE_ADAPTERS.md",
    "docs/technical/VENUE_RECONCILIATION.md",
    "docs/technical/DEPLOYMENT.md",
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
            "Each CEO instruction fixes both leg quantities and creates at most one execution batch",
            "cumulative external fills may not exceed those instruction quantities",
            "global one-active-execution serialization",
            "`result_unknown` forbids blind retry",
            "Kill Switch",
            "forced read-only reset",
            "15-second total chase TTL",
            "one-second evaluation cadence",
            "at most five amend or cancel-repost mutations",
            "at least one tick of price change before mutation",
        )

        for statement in required_contract:
            self.assertIn(statement, runbook, f"runbook lost mandatory contract text: {statement}")

    def test_legacy_fixed_cap_code_and_public_session_type_remain_explicit_blockers(self) -> None:
        current_state = read("docs/codex/current-state.md")
        program = read("docs/codex/0.11.1-program.md")
        runbook = read("docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md")
        auth_contract = read("docs/technical/AUTH_RBAC_LIVE_SESSIONS.md")
        adapter_contract = read("docs/technical/LIVE_VENUE_ADAPTERS.md")
        platform_sessions = read("platform-api/app/live_trading_sessions.py")

        for authority in (current_state, program, runbook):
            self.assertIn("fixed-notional-cap code", authority)
            self.assertIn("controlled-live readiness blocker", authority)

        self.assertIn("`minimum_size_acceptance`", auth_contract)
        self.assertIn("legacy compatibility", auth_contract)
        self.assertIn(
            'Literal["minimum_size_acceptance", "existing_limits", "scale_change"]',
            platform_sessions,
        )
        self.assertIn("VG_RUNTIME_LIVE_MAX_ORDER_NOTIONAL", adapter_contract)
        self.assertIn("VG_RUNTIME_LIVE_MAX_DAILY_NOTIONAL", adapter_contract)
        self.assertIn("legacy compatibility", adapter_contract)
        self.assertIn("controlled-live readiness blocker", adapter_contract)


if __name__ == "__main__":
    unittest.main()
