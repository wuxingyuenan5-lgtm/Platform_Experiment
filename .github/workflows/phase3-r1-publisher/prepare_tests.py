from __future__ import annotations

from pathlib import Path

from common import ROOT, replace_or_assert

GOVERNANCE = "platform-api/tests/test_architecture_stacked_phase_governance.py"
WORKFLOW_TEST = "platform-api/tests/test_architecture_stacked_phase_workflows.py"


def prepare_tests() -> dict[str, bytes]:
    text = (ROOT / GOVERNANCE).read_text(encoding="utf-8")
    text = replace_or_assert(
        text,
        '            check.validate_stacked_workstream_selection(current["pull_request"]["head"]["ref"], "standard")',
        '            check.validate_stacked_workstream_selection(\n'
        '                current["pull_request"]["head"]["ref"],\n'
        '                "standard",\n'
        '            )',
        "stacked selection formatting",
    )
    text = replace_or_assert(
        text,
        "def test_issue_critical_and_missing_packet_behavior(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:",
        "def test_issue_critical_and_missing_packet_behavior(\n"
        "    monkeypatch: pytest.MonkeyPatch,\n"
        "    tmp_path: Path,\n"
        ") -> None:",
        "issue test formatting",
    )
    text = replace_or_assert(
        text,
        '    section = workflow.split("- name: Validate PR workstream", 1)[1].split("- name: Audit stacked Phase history", 1)[0]',
        '    section = workflow.split("- name: Validate PR workstream", 1)[1].split(\n'
        '        "- name: Audit stacked Phase history",\n'
        '        1,\n'
        '    )[0]',
        "workflow parser formatting",
    )
    payload = Path(__file__).with_name("test_architecture_stacked_phase_workflows.py").read_bytes()
    return {GOVERNANCE: text.encode(), WORKFLOW_TEST: payload}
