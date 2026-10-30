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


def test_missing_cockpit_reports_entrypoint_error_without_traceback(tmp_path: Path) -> None:
    errors = DOCUMENTATION_CONSISTENCY.validate_repository(tmp_path)
    assert "required documentation entrypoint is missing: docs/PROJECT.md" in errors


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


def test_active_authority_requires_an_exact_active_status(tmp_path: Path) -> None:
    path = tmp_path / "docs/authority.md"
    path.parent.mkdir(parents=True)

    path.write_text("状态：`active authentication contract`\n", encoding="utf-8")
    assert not DOCUMENTATION_CONSISTENCY.is_active_authority(
        tmp_path,
        path,
        path.read_text(encoding="utf-8"),
    )

    path.write_text("状态：`active`\n", encoding="utf-8")
    assert DOCUMENTATION_CONSISTENCY.is_active_authority(
        tmp_path,
        path,
        path.read_text(encoding="utf-8"),
    )


@pytest.mark.parametrize("heading", ["## 活跃阶段", "## Continuing work"])
def test_cockpit_links_activate_stages_without_status_metadata(
    tmp_path: Path,
    heading: str,
) -> None:
    project = tmp_path / "docs/PROJECT.md"
    stage = tmp_path / "docs/workstreams/research.md"
    stage.parent.mkdir(parents=True)
    project.write_text(f"{heading}\n[Research](workstreams/research.md)\n", encoding="utf-8")
    stage.write_text("# Research\n当前结果与剩余验收\n", encoding="utf-8")

    assert DOCUMENTATION_CONSISTENCY.is_active_authority(
        tmp_path, stage, stage.read_text(encoding="utf-8")
    )
    assert DOCUMENTATION_CONSISTENCY.validate_workstreams(tmp_path) == []

    stage.write_text("# Research\n[old](docs/planning/retired.md)\n", encoding="utf-8")
    assert DOCUMENTATION_CONSISTENCY.validate_markdown_links(tmp_path, [stage])


def test_workstream_inventory_reports_orphans_and_missing_links(tmp_path: Path) -> None:
    stage = tmp_path / "docs/workstreams/unlisted.md"
    stage.parent.mkdir(parents=True)
    stage.write_text("# Stage\n", encoding="utf-8")
    (tmp_path / "docs/PROJECT.md").write_text(
        "## Current stages\n[Missing](workstreams/missing.md)\n", encoding="utf-8"
    )

    errors = DOCUMENTATION_CONSISTENCY.validate_workstreams(tmp_path)
    assert len(errors) == 2
    assert any("unlisted.md: workstream is not linked" in error for error in errors)
    assert any("declared workstream is missing" in error for error in errors)


def test_current_candidate_rejects_old_version_but_keeps_historical_evidence(
    tmp_path: Path,
) -> None:
    project = tmp_path / "docs/PROJECT.md"
    project.parent.mkdir()
    (tmp_path / "VERSION").write_text("0.11.4\n", encoding="utf-8")
    content = "# 当前项目\n简短进度，不要求固定章节名称。"
    project.write_text(content + "\nPlatform 0.11.3 候选\n", encoding="utf-8")
    assert DOCUMENTATION_CONSISTENCY.validate_project_cockpit(tmp_path) == [
        "PROJECT.md contains stale candidate version: 0.11.3"
    ]
    project.write_text(
        content + "\n历史：Platform 0.11.3 候选\nPlatform 0.11.4 候选\n", encoding="utf-8"
    )
    assert DOCUMENTATION_CONSISTENCY.validate_project_cockpit(tmp_path) == []


@pytest.mark.parametrize(
    "summary",
    ["## New schema migration 44\n", "新增迁移44：建立查询索引。\n", "迁移版本：44\n"],
)
def test_migration_review_accepts_existing_languages_and_formats(
    tmp_path: Path,
    summary: str,
) -> None:
    source = tmp_path / "platform-api/app/schema_migrations.py"
    guide = tmp_path / "docs/database/README.md"
    source.parent.mkdir(parents=True)
    guide.parent.mkdir(parents=True)
    source.write_text(
        "MIGRATIONS = (Migration(version=43, name='old'), Migration(version=44, name='new'))\n",
        encoding="utf-8",
    )
    guide.write_text("## History audit migration 43\n", encoding="utf-8")
    assert DOCUMENTATION_CONSISTENCY.migration_review_notes(tmp_path) == [
        "review whether migration 44 needs a database-guide update"
    ]
    guide.write_text(summary, encoding="utf-8")
    assert DOCUMENTATION_CONSISTENCY.migration_review_notes(tmp_path) == []


def test_documentation_does_not_require_english_boilerplate_or_block_on_review_notes(
    tmp_path: Path,
) -> None:
    for relative in DOCUMENTATION_CONSISTENCY.REQUIRED_ENTRYPOINTS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# 说明\n按实际内容书写，无固定英文句子。\n", encoding="utf-8")
    (tmp_path / "VERSION").write_text("0.11.4\n", encoding="utf-8")
    schema = tmp_path / "platform-api/app/schema_migrations.py"
    schema.parent.mkdir(parents=True)
    schema.write_text("MIGRATIONS = (Migration(version=44),)\n", encoding="utf-8")
    assert DOCUMENTATION_CONSISTENCY.validate_repository(tmp_path) == []
    assert DOCUMENTATION_CONSISTENCY.migration_review_notes(tmp_path)


def test_local_test_fixtures_do_not_pollute_documentation_checks(tmp_path: Path) -> None:
    guide = tmp_path / "docs/guide.md"
    guide.parent.mkdir()
    guide.write_text("# Guide\n", encoding="utf-8")
    for directory in (".pytest-basetemp/case", "tmp"):
        fixture = tmp_path / directory / "README.md"
        fixture.parent.mkdir(parents=True)
        fixture.write_text("[Missing](docs/missing.md)\n", encoding="utf-8")
    paths = DOCUMENTATION_CONSISTENCY.markdown_paths(tmp_path)
    assert paths == [guide]
    assert DOCUMENTATION_CONSISTENCY.validate_markdown_links(tmp_path, paths) == []
