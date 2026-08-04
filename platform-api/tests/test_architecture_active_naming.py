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

FORMAL_APP_TITLE = "全球变量金融平台"
APP_ENV_PATHS = (
    ROOT / "platform-web" / ".env.development",
    ROOT / "platform-web" / ".env.production",
)
EXPECTED_PRODUCTION_CONFIG_VARIABLE = (
    "__PRODUCTION__5168740353D891CF91D1878D5E7353F0__CONF__"
)


def scan_fixture(tmp_path: Path, relative: str, content: str) -> list[str]:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ACTIVE_NAMING.scan_repository(tmp_path, entries=[])


def read_env_value(path: Path, key: str) -> str:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    raise AssertionError(f"{key} is missing from {path.relative_to(ROOT)}")


def production_config_variable(title: str) -> str:
    encoded = "".join(f"{ord(char):04X}"[-4:] for char in title)
    return f"__PRODUCTION__{encoded or '__APP'}__CONF__".upper().replace(" ", "")


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


def test_audit_page_is_scanned(tmp_path: Path) -> None:
    errors = scan_fixture(
        tmp_path,
        "platform-web/src/views/audit/index.vue",
        "<template>admin-risk</template>\n",
    )
    assert errors
    assert "platform-web/src/views/audit/index.vue" in errors[0]


def test_audit_route_is_scanned(tmp_path: Path) -> None:
    errors = scan_fixture(
        tmp_path,
        "platform-web/src/router/routes/modules/audit.ts",
        "export const title = 'RTA Platform';\n",
    )
    assert errors
    assert "platform-web/src/router/routes/modules/audit.ts" in errors[0]


def test_audit_source_module_is_scanned(tmp_path: Path) -> None:
    old_service_name = "Platform" + " Backend"
    errors = scan_fixture(
        tmp_path,
        "platform-api/app/order_audit.py",
        f"SERVICE = '{old_service_name}'\n",
    )
    assert errors
    assert "platform-api/app/order_audit.py" in errors[0]


@pytest.mark.parametrize(
    "relative",
    (
        "docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md",
        "docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md",
    ),
)
def test_legacy_production_audit_evidence_is_exactly_excluded(
    tmp_path: Path,
    relative: str,
) -> None:
    assert scan_fixture(tmp_path, relative, "# RTA Platform historical evidence\n") == []


def test_nonlegacy_audit_markdown_is_scanned(tmp_path: Path) -> None:
    errors = scan_fixture(
        tmp_path,
        "docs/architecture/CURRENT_PLATFORM_AUDIT.md",
        "# RTA Platform current audit\n",
    )
    assert errors
    assert "docs/architecture/CURRENT_PLATFORM_AUDIT.md" in errors[0]


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


def test_formal_app_title_is_exact_in_both_environments() -> None:
    expected_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    for path in APP_ENV_PATHS:
        assert read_env_value(path, "VITE_GLOB_APP_TITLE") == FORMAL_APP_TITLE
        assert read_env_value(path, "VITE_GLOB_APP_VERSION") == expected_version
        source = path.read_text(encoding="utf-8")
        assert source.count("VITE_GLOB_APP_TITLE") == 1


def test_formal_app_title_drives_existing_storage_and_runtime_config_chain() -> None:
    env_source = (ROOT / "platform-web/src/utils/env.ts").read_text(encoding="utf-8")
    setting_source = (ROOT / "platform-web/src/hooks/setting/index.ts").read_text(
        encoding="utf-8"
    )
    plugin_source = (
        ROOT / "platform-web/internal/vite-config/src/plugins/appConfig.ts"
    ).read_text(encoding="utf-8")

    assert "const { VITE_GLOB_APP_TITLE } = getAppEnvConfig();" in env_source
    assert "`${VITE_GLOB_APP_TITLE.replace(/\\s/g, '_')}__${getEnv()}`" in env_source
    assert "`${getCommonStoragePrefix()}${`__${pkg.version}`}__`" in env_source
    assert "getVariableName(import.meta.env.VITE_GLOB_APP_TITLE)" in env_source
    assert "title: VITE_GLOB_APP_TITLE" in setting_source
    assert (
        "shortName: VITE_GLOB_APP_TITLE.replace(/\\s/g, '_').replace(/-/g, '_')"
        in setting_source
    )
    assert "_config?.env?.VITE_GLOB_APP_TITLE" in plugin_source
    assert "getVariableName(appTitle)" in plugin_source

    assert f"{FORMAL_APP_TITLE}__DEVELOPMENT".upper() == "全球变量金融平台__DEVELOPMENT"
    assert FORMAL_APP_TITLE.replace(" ", "_").replace("-", "_") == FORMAL_APP_TITLE
    assert production_config_variable(FORMAL_APP_TITLE) == EXPECTED_PRODUCTION_CONFIG_VARIABLE


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


def test_frontend_build_verifies_generated_formal_brand_config() -> None:
    package = json.loads((ROOT / "platform-web/package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["build"].endswith(
        "&& node scripts/verify-formal-brand-config.cjs"
    )
    verifier = (
        ROOT / "platform-web/scripts/verify-formal-brand-config.cjs"
    ).read_text(encoding="utf-8")
    assert FORMAL_APP_TITLE in verifier
    assert EXPECTED_PRODUCTION_CONFIG_VARIABLE in verifier
    assert "dist/_app.config.js" in verifier
