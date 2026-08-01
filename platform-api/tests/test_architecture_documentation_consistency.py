from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts/check-documentation-consistency.py"
SPEC = spec_from_file_location("documentation_consistency", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
DOCUMENTATION_CONSISTENCY = module_from_spec(SPEC)
SPEC.loader.exec_module(DOCUMENTATION_CONSISTENCY)


def test_current_repository_documentation_is_consistent() -> None:
    assert DOCUMENTATION_CONSISTENCY.validate_repository(REPOSITORY_ROOT) == []


def test_owner_catalog_rejects_missing_owner_path(tmp_path: Path) -> None:
    ownership = "| Example boundary | `app/example_owner.py` | responsibility | forbidden |"

    errors = DOCUMENTATION_CONSISTENCY.validate_owner_catalog(
        tmp_path,
        ownership,
        {"Example boundary": "app/example_owner.py"},
    )

    assert errors == ["canonical owner path does not exist: app/example_owner.py"]


def test_owner_catalog_rejects_wrong_mapping(tmp_path: Path) -> None:
    owner = tmp_path / "app/example_owner.py"
    owner.parent.mkdir(parents=True)
    owner.write_text("", encoding="utf-8")

    errors = DOCUMENTATION_CONSISTENCY.validate_owner_catalog(
        tmp_path,
        "| Example boundary | `app/other.py` | responsibility | forbidden |",
        {"Example boundary": "app/example_owner.py"},
    )

    assert errors == [
        "ownership catalog missing canonical mapping: Example boundary -> app/example_owner.py"
    ]


def test_context_map_rejects_obsolete_financial_facts_shortcut() -> None:
    errors = DOCUMENTATION_CONSISTENCY.validate_context_map(
        "- Formal accounting authority: `platform-api/app/financial_facts.py`."
    )

    assert errors == [
        "stale Agent context ownership statement: "
        "Formal accounting authority: `platform-api/app/financial_facts.py`"
    ]


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


def test_markdown_links_ignore_excluded_historical_directories(tmp_path: Path) -> None:
    archived = tmp_path / "docs/archive/old.md"
    archived.parent.mkdir(parents=True)
    archived.write_text("[Missing](gone.md)\n", encoding="utf-8")

    assert DOCUMENTATION_CONSISTENCY.validate_markdown_links(tmp_path) == []


def test_markdown_links_ignore_examples_inside_fenced_code(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("```markdown\n[Example](not-real.md)\n```\n", encoding="utf-8")

    assert DOCUMENTATION_CONSISTENCY.validate_markdown_links(tmp_path, [readme]) == []


def test_portable_documentation_rejects_real_user_home_paths(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "Windows: C:\\Users\\alice\\workspace\\repo\n"
        "macOS: /Users/bob/workspace/repo\n"
        "Linux: /home/carol/workspace/repo\n",
        encoding="utf-8",
    )

    assert DOCUMENTATION_CONSISTENCY.validate_portable_documentation(
        tmp_path,
        [readme],
    ) == [
        "README.md: workstation-specific Linux user home path is forbidden: /home/carol/",
        "README.md: workstation-specific Windows user profile path is forbidden: "
        "C:\\Users\\alice\\",
        "README.md: workstation-specific macOS user home path is forbidden: /Users/bob/",
    ]


def test_portable_documentation_allows_placeholders_and_fenced_examples(
    tmp_path: Path,
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "Use `%APPDATA%\\MetaQuotes` or `${HOME}/workspace`.\n"
        "Use `C:\\Users\\<user>\\workspace`, `/Users/<user>/workspace`, "
        "or `/home/<user>/workspace`.\n"
        "```text\nC:\\Users\\example\\historical-output\n```\n",
        encoding="utf-8",
    )

    assert DOCUMENTATION_CONSISTENCY.validate_portable_documentation(
        tmp_path,
        [readme],
    ) == []


def test_a1_hierarchy_rejects_duplicate_substantive_paragraphs(tmp_path: Path) -> None:
    paragraph = (
        "This deliberately long authority paragraph repeats the same current rule "
        "across two top-level documents and therefore exceeds the minimum duplication "
        "threshold used by the documentation hierarchy gate."
    )
    for relative in DOCUMENTATION_CONSISTENCY.A1_ENTRYPOINTS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Title\n\nUnique content for {relative}.\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(f"# Root\n\n{paragraph}\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(f"# Rules\n\n{paragraph}\n", encoding="utf-8")
    docs_index = tmp_path / "docs/README.md"
    docs_index.write_text(
        docs_index.read_text(encoding="utf-8")
        + "\n"
        + " ".join(
            f"`{p.removeprefix('docs/') if p.startswith('docs/') else '../' + p}`"
            for p in DOCUMENTATION_CONSISTENCY.A1_ENTRYPOINTS
        ),
        encoding="utf-8",
    )

    errors = DOCUMENTATION_CONSISTENCY.validate_a1_hierarchy(tmp_path)
    assert any("duplicate a substantive paragraph" in error for error in errors)


def test_platform_web_index_cannot_claim_repository_authority(tmp_path: Path) -> None:
    for relative in DOCUMENTATION_CONSISTENCY.A1_ENTRYPOINTS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Entry\n", encoding="utf-8")
    docs_index = tmp_path / "docs/README.md"
    docs_index.write_text(
        " ".join(
            f"`{p.removeprefix('docs/') if p.startswith('docs/') else '../' + p}`"
            for p in DOCUMENTATION_CONSISTENCY.A1_ENTRYPOINTS
        ),
        encoding="utf-8",
    )
    web = tmp_path / "platform-web/docs/README.md"
    web.parent.mkdir(parents=True, exist_ok=True)
    web.write_text("# 唯一入口\n", encoding="utf-8")

    assert any(
        "must remain specialist reference" in error
        for error in DOCUMENTATION_CONSISTENCY.validate_a1_hierarchy(tmp_path)
    )
