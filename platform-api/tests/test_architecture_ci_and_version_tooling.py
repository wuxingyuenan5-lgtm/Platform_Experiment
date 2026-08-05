from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ci_scope = load_script("ci_scope", "scripts/ci-scope.py")
bump_version = load_script("bump_version", "scripts/bump-version.py")


def test_docs_only_change_skips_application_jobs() -> None:
    assert ci_scope.classify_paths(["README.md"]) == {
        "backend": False,
        "runtime": False,
        "frontend": False,
        "docs_only": True,
    }


def test_single_module_changes_select_only_affected_job() -> None:
    backend = ci_scope.classify_paths(["platform-api/app/example.py"])
    runtime = ci_scope.classify_paths(["execution-runtime/app/example.py"])
    frontend = ci_scope.classify_paths(["platform-web/src/example.ts"])

    assert backend["backend"] and not backend["runtime"] and not backend["frontend"]
    assert runtime["runtime"] and not runtime["backend"] and not runtime["frontend"]
    assert frontend["frontend"] and not frontend["backend"] and not frontend["runtime"]


def test_shared_workflow_change_forces_full_matrix() -> None:
    assert ci_scope.classify_paths([".github/workflows/platform-ci.yml"]) == {
        "backend": True,
        "runtime": True,
        "frontend": True,
        "docs_only": False,
    }


def test_main_push_can_force_full_matrix() -> None:
    result = ci_scope.classify_paths([], force_full=True)
    assert result == {
        "backend": True,
        "runtime": True,
        "frontend": True,
        "docs_only": False,
    }


def test_bump_version_updates_all_maintained_declarations(tmp_path: Path) -> None:
    (tmp_path / "platform-api/app").mkdir(parents=True)
    (tmp_path / "execution-runtime/app").mkdir(parents=True)
    (tmp_path / "platform-web").mkdir()
    (tmp_path / "docs/codex").mkdir(parents=True)
    (tmp_path / "VERSION").write_text("0.8.0\n", encoding="utf-8")
    (tmp_path / "platform-api/pyproject.toml").write_text(
        '[project]\nversion = "0.8.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "execution-runtime/pyproject.toml").write_text(
        '[project]\nversion = "0.8.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "platform-web/package.json").write_text(
        '{\n  "name": "platform-web",\n  "version": "0.8.0",\n  "private": true\n}\n',
        encoding="utf-8",
    )
    for filename in (".env.development", ".env.production"):
        (tmp_path / f"platform-web/{filename}").write_text(
            'VITE_GLOB_APP_VERSION = "0.8.0"\n',
            encoding="utf-8",
        )
    (tmp_path / "platform-api/app/application.py").write_text(
        'PLATFORM_VERSION = "0.8.0"\n', encoding="utf-8"
    )
    (tmp_path / "execution-runtime/app/version.py").write_text(
        'PLATFORM_VERSION = "0.8.0"\n', encoding="utf-8"
    )
    (tmp_path / "docs/codex/current-state.md").write_text(
        '- Current target version: Platform `0.8.0`.\n', encoding="utf-8"
    )

    bump_version.update_versions(tmp_path, "0.9.3")

    assert (tmp_path / "VERSION").read_text(encoding="utf-8") == "0.9.3\n"
    assert 'version = "0.9.3"' in (
        tmp_path / "platform-api/pyproject.toml"
    ).read_text(encoding="utf-8")
    assert 'version = "0.9.3"' in (
        tmp_path / "execution-runtime/pyproject.toml"
    ).read_text(encoding="utf-8")
    assert '"version": "0.9.3"' in (
        tmp_path / "platform-web/package.json"
    ).read_text(encoding="utf-8")
    for filename in (".env.development", ".env.production"):
        assert 'VITE_GLOB_APP_VERSION = "0.9.3"' in (
            tmp_path / f"platform-web/{filename}"
        ).read_text(encoding="utf-8")
    assert 'PLATFORM_VERSION = "0.9.3"' in (
        tmp_path / "platform-api/app/application.py"
    ).read_text(encoding="utf-8")
    assert 'PLATFORM_VERSION = "0.9.3"' in (
        tmp_path / "execution-runtime/app/version.py"
    ).read_text(encoding="utf-8")
    assert 'Platform `0.9.3`' in (
        tmp_path / "docs/codex/current-state.md"
    ).read_text(encoding="utf-8")


def test_permanent_workflows_have_distinct_long_term_responsibilities() -> None:
    platform = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    quality = (ROOT / ".github/workflows/repository-quality.yml").read_text(
        encoding="utf-8"
    )
    secret = (ROOT / ".github/workflows/secret-scan.yml").read_text(encoding="utf-8")

    assert "refactor/platform-0-9-3-" not in platform + quality + secret
    assert "python scripts/scan-secrets.py" not in platform
    assert "python scripts/scan-secrets.py" in secret
    assert "python scripts/check-version-consistency.py" in quality
    assert "python scripts/context-for.py --check-budgets --json" in quality
    assert "name: platform-api" in platform
    assert "name: execution-runtime" in platform
    assert "name: platform-web" in platform
