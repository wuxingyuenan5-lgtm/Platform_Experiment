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
        "- Formal accounting authority: `platform-backend/app/financial_facts.py`."
    )

    assert errors == [
        "stale Agent context ownership statement: "
        "Formal accounting authority: `platform-backend/app/financial_facts.py`"
    ]
