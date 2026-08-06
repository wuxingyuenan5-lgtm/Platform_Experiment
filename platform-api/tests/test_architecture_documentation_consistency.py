from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts/check-documentation-consistency.py"
SPEC = spec_from_file_location("documentation_consistency", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
DOCUMENTATION_CONSISTENCY = module_from_spec(SPEC)
SPEC.loader.exec_module(DOCUMENTATION_CONSISTENCY)


def test_current_repository_documentation_is_consistent() -> None:
    assert DOCUMENTATION_CONSISTENCY.validate_repository(REPOSITORY_ROOT) == []


def test_markdown_links_accept_existing_local_target(tmp_path: Path) -> None:
    guide = tmp_path / "docs/guide.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Guide\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("[Guide](docs/guide.md)\n", encoding="utf-8")

    assert DOCUMENTATION_CONSISTENCY.validate_markdown_links(tmp_path, [readme]) == []


def test_markdown_links_reject_missing_local_target(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("[Missing](docs/missing.md)\n", encoding="utf-8")

    assert DOCUMENTATION_CONSISTENCY.validate_markdown_links(tmp_path, [readme]) == [
        "README.md: local Markdown target does not exist: docs/missing.md"
    ]


def test_markdown_links_ignore_external_fragment_and_placeholder_targets(
    tmp_path: Path,
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "[External](https://example.com/docs)\n"
        "[Anchor](#section)\n"
        "[Template](tasks/issue-<number>-<slug>.md)\n",
        encoding="utf-8",
    )

    assert DOCUMENTATION_CONSISTENCY.validate_markdown_links(tmp_path, [readme]) == []


def write_candidate_contracts(
    root: Path,
    *,
    current: str,
    auth: str = "状态：`active authentication and authorization contract`\n",
    matrix: str = "状态：`active Platform candidate access contract`\n",
) -> list[Path]:
    current_path = root / "docs/codex/current-state.md"
    auth_path = root / "docs/technical/AUTH_RBAC_LIVE_SESSIONS.md"
    matrix_path = root / "docs/product/PLATFORM_ACCESS_MATRIX.md"
    for path, content in ((current_path, current), (auth_path, auth), (matrix_path, matrix)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return [current_path, auth_path, matrix_path]


def valid_candidate_state() -> str:
    return (
        "Current candidate target: Platform `0.10.1`.\n"
        "The candidate includes browser access and frontend product restoration.\n"
    )


def test_candidate_documentation_rejects_stale_frontend_status(tmp_path: Path) -> None:
    paths = write_candidate_contracts(
        tmp_path,
        current=valid_candidate_state()
        + "Frontend product restoration has not been executed and remains outside the current non-UI scope.\n",
    )

    errors = DOCUMENTATION_CONSISTENCY.validate_candidate_documentation(tmp_path, paths)

    assert any("Frontend product restoration has not been executed" in error for error in errors)
    assert any("remains outside the current non-UI scope" in error for error in errors)


def test_candidate_documentation_rejects_draft_pr_status(tmp_path: Path) -> None:
    paths = write_candidate_contracts(
        tmp_path,
        current=valid_candidate_state(),
        matrix="状态：`frozen for Draft PR #42 acceptance`\n",
    )

    assert DOCUMENTATION_CONSISTENCY.validate_candidate_documentation(tmp_path, paths) == [
        "docs/product/PLATFORM_ACCESS_MATRIX.md:1: active status must not persist a Draft PR number"
    ]


def test_candidate_documentation_rejects_pending_auth_status(tmp_path: Path) -> None:
    paths = write_candidate_contracts(
        tmp_path,
        current=valid_candidate_state(),
        auth="状态：`active authentication contract, verification pending`\n",
    )

    assert DOCUMENTATION_CONSISTENCY.validate_candidate_documentation(tmp_path, paths) == [
        "docs/technical/AUTH_RBAC_LIVE_SESSIONS.md contains stale verification status: verification pending"
    ]


def test_candidate_documentation_requires_browser_and_restoration_scope(tmp_path: Path) -> None:
    paths = write_candidate_contracts(
        tmp_path,
        current="Current candidate target: Platform `0.10.1`.\n",
    )

    errors = DOCUMENTATION_CONSISTENCY.validate_candidate_documentation(tmp_path, paths)

    assert len(errors) == 2
    assert any("browser access" in error for error in errors)
    assert any("frontend product restoration" in error for error in errors)
