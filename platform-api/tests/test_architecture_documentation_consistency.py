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
