from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check-active-naming-consistency.py"
SPEC = importlib.util.spec_from_file_location("active_naming", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ACTIVE_NAMING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ACTIVE_NAMING)


def scan_fixture(tmp_path: Path, relative: str, content: str) -> list[str]:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ACTIVE_NAMING.scan_repository(tmp_path, entries=[])


def test_current_active_naming_is_consistent() -> None:
    assert ACTIVE_NAMING.scan_repository(ROOT) == []


def test_rta_platform_in_current_readme_fails(tmp_path: Path) -> None:
    assert scan_fixture(tmp_path, "README.md", "# RTA Platform\n")


def test_admin_risk_in_current_ui_fails(tmp_path: Path) -> None:
    assert scan_fixture(
        tmp_path,
        "platform-web/src/view.ts",
        "export const title = 'admin-risk';\n",
    )


def test_private_fund_template_name_in_service_code_fails(tmp_path: Path) -> None:
    assert scan_fixture(
        tmp_path,
        "platform-api/app/service.py",
        "SERVICE = '私募交易风控平台'\n",
    )


def test_nonallowlisted_legacy_name_fails(tmp_path: Path) -> None:
    assert scan_fixture(tmp_path, "scripts/example.py", "DOMAIN = 'risk-web'\n")


def test_unprefixed_runtime_service_name_fails(tmp_path: Path) -> None:
    old_name = "Execution" + " Runtime"
    assert scan_fixture(tmp_path, "docs/technical/service.md", f"# {old_name}\n")


def test_execution_risk_is_a_legal_business_term(tmp_path: Path) -> None:
    assert scan_fixture(tmp_path, "platform-api/app/risk.py", "DOMAIN = 'execution risk'\n") == []


def test_chinese_formal_brand_in_readme_is_allowed(tmp_path: Path) -> None:
    assert scan_fixture(tmp_path, "README.md", "# 全球变量金融平台\n") == []


def test_variable_global_brand_in_frontend_is_allowed(tmp_path: Path) -> None:
    assert scan_fixture(
        tmp_path,
        "platform-web/src/brand.ts",
        "export const brand = 'Variable-Global';\n",
    ) == []


def test_variable_global_distribution_brand_is_allowed(tmp_path: Path) -> None:
    assert scan_fixture(
        tmp_path,
        "platform-api/pyproject.toml",
        '[project]\nname = "variable-global-platform-api"\n',
    ) == []


def test_variable_global_runtime_service_description_is_allowed(tmp_path: Path) -> None:
    assert scan_fixture(
        tmp_path,
        "execution-runtime/README.md",
        "# Variable-Global Execution Runtime\n",
    ) == []


def test_historical_release_note_is_not_scanned(tmp_path: Path) -> None:
    assert scan_fixture(tmp_path, "docs/releases/0.1.0.md", "# RTA Platform release\n") == []


def test_allowlist_rejects_broad_paths(tmp_path: Path) -> None:
    config = tmp_path / "config/legacy-naming-allowlist.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "pattern": "RTA",
                        "path": "docs/**",
                        "category": "historical-release",
                        "reason": "historical",
                        "owner": "Documentation",
                        "removalCondition": "release retired",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="path must be exact"):
        ACTIVE_NAMING.load_allowlist(tmp_path)


def test_legal_brands_are_not_in_legacy_allowlist() -> None:
    entries = ACTIVE_NAMING.load_allowlist(ROOT)
    assert all("variable-global" not in entry.pattern.lower() for entry in entries)
    assert all("全球变量金融平台" not in entry.pattern for entry in entries)


def test_current_formal_brand_counts_are_positive() -> None:
    counts = ACTIVE_NAMING.count_legal_brand_hits(ROOT)
    assert counts["全球变量金融平台"] > 0
    assert counts["Variable-Global"] > 0


def test_distribution_and_frontend_package_names_preserve_brand_contracts() -> None:
    with (ROOT / "platform-api/pyproject.toml").open("rb") as handle:
        assert tomllib.load(handle)["project"]["name"] == "variable-global-platform-api"
    with (ROOT / "execution-runtime/pyproject.toml").open("rb") as handle:
        assert tomllib.load(handle)["project"]["name"] == "variable-global-execution-runtime"
    package = json.loads((ROOT / "platform-web/package.json").read_text(encoding="utf-8"))
    assert package["name"] == "vg-platform-web"


def test_platform_ci_validates_preserved_distribution_metadata() -> None:
    workflow = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    assert "python -m pip show variable-global-platform-api" in workflow
    assert "python -m pip show variable-global-execution-runtime" in workflow
